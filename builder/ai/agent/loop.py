"""The single agentic loop for Builder AI.

`AgentRunner` holds the per-request state, builds the message list, and drives
one tool-calling loop until the model stops requesting server/terminal tools.
Tool *behaviour* lives in the registry; this file only orchestrates.

Realtime event contract (consumed by the frontend). Every event name is
suffixed with the page id, e.g. `ai_chat_stream_<page_id>`:

    ai_chat_progress    {message}
    ai_chat_stream      {chunk, kind?}   kind="page_yaml" → apply to canvas;
                                         absent/"summary" → append to chat text
    ai_chat_tool_batch  {operations: [{tool_name, args}]}
    ai_chat_clarify     {question, options, previews?,
                         plan_summary?, headline?, sections?, palette?}
    ai_chat_complete    {message}
    ai_chat_error       {message}

All events also carry {page_id}. Clarify messages are persisted+committed
before the event fires, so a session reload on receipt is race-free.
"""

import json
import logging
import re
import time

import frappe

from builder.ai import llm
from builder.ai.agent.registry import ToolRegistry, build_default_registry
from builder.ai.block_codec import BlockCodec
from builder.ai.models import ModelRegistry
from builder.ai.prompts import Prompts
from builder.ai.session import AISession
from builder.ai.snapshots import save_revert_snapshot
from builder.utils import to_compact_yaml

logger = frappe.logger("builder.ai.agent.loop")
logger.setLevel(logging.INFO)

# One turn may span several rounds: server-tool reads, plus a model that applies a
# page-wide change in batches across rounds. High enough to finish a big bulk edit
# (e.g. translate every block of a large page), bounded so a runaway loop can't spin.
MAX_ROUNDS = 25
EVENT_PREFIX = "ai_chat"

# Tools that change the block tree — the only changes a page snapshot can revert. A
# turn touching only scripts is reverted via the per-message "Undo script" action, so
# it gets no snapshot (and no misleading "Revert this edit" button).
BLOCK_TOOLS = frozenset(
	{"add_block", "update_block", "update_blocks", "remove_block", "move_block", "generate_page"}
)


class CancelledError(Exception):
	"""Raised inside the stream loops when the user cancels the turn."""


def _looks_like_page_yaml(text: str) -> bool:
	"""Heuristic: did the model emit page YAML as plain content?"""
	if not text:
		return False
	stripped = re.sub(r"^```(?:yaml)?\s*", "", text.strip())
	return stripped.startswith(("el:", "- el:", "id: root", "- id:"))


class AgentRunner:
	# Above this many chars of compact-YAML page structure, switch the page context
	# from the full tree to a compact outline (read_block pulls detail on demand).
	# Tuned so a typical multi-section page still ships in full; only big pages skeletonise.
	FULL_CONTEXT_LIMIT = 9000

	def __init__(
		self,
		prompt: str,
		page_context_json: str,
		model: str,
		api_key: str,
		*,
		user: str | None = None,
		page_id: str | None = None,
		session_id: str | None = None,
		selected_block_ids: list[str] | None = None,
		image_url: str | None = None,
		registry: ToolRegistry | None = None,
		system_prompt: str | None = None,
		pre_turn_state: dict | None = None,
	):
		self.prompt = prompt
		self.page_context_json = page_context_json
		self.model = model
		self.api_key = api_key
		self.user = user or frappe.session.user
		self.page_id = page_id
		self.session_id = session_id
		self.selected_block_ids = selected_block_ids or []
		self.image_url = image_url
		self.registry = registry or build_default_registry()
		self.system_prompt = system_prompt or Prompts.AGENT_SYSTEM
		# Page state captured before this turn (in api.run). A snapshot doc is created
		# from it ONLY if the turn mutates the page; its name lands on the final
		# assistant message as the revert handle. None when the page was empty.
		self.pre_turn_state = pre_turn_state
		self.revert_snapshot: str | None = None
		# Per-turn debug trace (one entry per round) + why the turn ended. Persisted on
		# the assistant message so the agent debugger can explain what the model did and
		# why it stopped (e.g. "model_finished after 1 round, 2 tool calls").
		self.trace: list[dict] = []
		self.stop_reason = ""
		# Tiered model selection: resolved in run() once we know the scenario.
		self.loop_model = self.model
		# Per-turn token tally, summed across every LLM call this turn (the loop's
		# tool-calling rounds + the generation stream). Surfaced in debug metadata and
		# logged so the selector/tiered-context changes can be measured against baseline.
		self.usage = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0, "calls": 0}

	# --- cancellation -----------------------------------------------------

	def _cancel_key(self) -> str | None:
		return f"builder_ai_cancel:{self.session_id}" if self.session_id else None

	def is_cancelled(self) -> bool:
		key = self._cancel_key()
		# use_local_cache=False is critical: the cancel is set by a DIFFERENT
		# web worker, and Frappe's per-request local cache would otherwise
		# pin the first (miss) result and never re-read Redis.
		return bool(frappe.cache.get_value(key, use_local_cache=False)) if key else False

	def clear_cancel_flag(self) -> None:
		if key := self._cancel_key():
			frappe.cache.delete_value(key)

	# --- realtime ---------------------------------------------------------

	def emit(self, suffix: str, **kwargs):
		event = f"{EVENT_PREFIX}_{suffix}"
		if self.page_id:
			event = f"{event}_{self.page_id}"
		frappe.publish_realtime(event, {"page_id": self.page_id, **kwargs}, user=self.user)

	def ensure_revert_snapshot(self) -> None:
		"""Create the pre-turn snapshot the first time the turn changes the block tree.
		Consumes pre_turn_state so it runs at most once — and runs as soon as the first
		block batch is applied, so even a cancelled multi-round edit stays revertable."""
		if self.pre_turn_state is None:
			return
		state, self.pre_turn_state = self.pre_turn_state, None
		self.revert_snapshot = save_revert_snapshot(self.page_id, state)

	def record_usage(self, chunk) -> None:
		"""Add a streamed chunk's usage to the per-turn tally. Only the final chunk of
		a stream (stream_options.include_usage) carries usage; the rest are None."""
		usage = getattr(chunk, "usage", None)
		if not usage:
			return
		self.usage["prompt_tokens"] += getattr(usage, "prompt_tokens", 0) or 0
		self.usage["completion_tokens"] += getattr(usage, "completion_tokens", 0) or 0
		self.usage["total_tokens"] += getattr(usage, "total_tokens", 0) or 0
		self.usage["calls"] += 1

	def record_round(self, round_index: int, tool_operations: list[dict], text: str) -> None:
		"""Append one round to the debug trace: which tools the model called (with
		truncated args) and any text it wrote. This is what the agent debugger reads to
		explain a turn — e.g. why it applied only N blocks."""
		self.trace.append(
			{
				"round": round_index,
				"tools": [
					{
						"name": op["tool_name"],
						"args": BlockCodec.truncate_for_log(
							json.dumps(op.get("args", {}), ensure_ascii=False), 300
						),
					}
					for op in tool_operations
				],
				"text": BlockCodec.truncate_for_log(text or "", 300),
			}
		)

	# --- message construction --------------------------------------------

	def build_page_context(self) -> str:
		root = self._page_root()
		if root is None:
			return ""
		full = to_compact_yaml(BlockCodec.compress(root, depth=0, task_tier="complex"))
		# Small pages: ship the full structure — cheapest path is no extra read_block
		# round-trips, and the model can match existing styles directly. Big pages: ship
		# a compact outline instead (styles/attrs omitted) and let the model pull detail
		# on demand with read_block. The threshold is on the full serialisation length,
		# which tracks token cost closely.
		if len(full) <= self.FULL_CONTEXT_LIMIT:
			return (
				f"Current page structure (YAML — pass a block's 'ref' value as block_id to edit it):\n{full}"
			)
		return self.build_skeleton_context(root)

	def build_skeleton_context(self, root: dict) -> str:
		"""Outline + full detail for any blocks the user has selected (so the common
		targeted-edit case needs no read_block round-trip)."""
		from builder.ai.agent.selectors import find_block, render_skeleton

		outline = render_skeleton(root)
		parts = [
			"This page is large, so you're given a compact OUTLINE (one line per block: "
			"indentation = nesting, then ref, element, optional name, and a short text "
			"preview). Styles and attributes are omitted. Pass a block's ref as block_id to "
			"edit it. To see a block's full styles/attributes/text before editing, call "
			"read_block(ref); to act on many blocks at once, call query_blocks then "
			"update_blocks. The outline reflects the page at the start of this turn.",
			outline,
		]
		for ref in self.selected_block_ids:
			block = find_block(root, ref)
			if block is None:
				continue
			detail = to_compact_yaml(BlockCodec.compress(block, depth=0, task_tier="complex"))
			parts.append(f"Full detail for selected block {ref}:\n{detail}")
		return "\n\n".join(parts)

	def build_messages(self) -> list[dict]:
		messages: list[dict] = [
			{
				"role": "system",
				"content": self.system_prompt,
				"cache_control": {"type": "ephemeral"},
			},
		]

		if page_context_message := self.build_page_context():
			messages.append({"role": "user", "content": page_context_message})
			messages.append(
				{
					"role": "assistant",
					"content": "Understood. I have the current page structure. What would you like me to change?",
				}
			)

		# Prior conversation as proper role-tagged turns (not a flattened system
		# blob) — the model handles dialogue better and we save the "User:"/
		# "Assistant:" prefix tokens on every call.
		messages.extend(AISession.build_context_messages_from_id(self.session_id))

		user_text = self.prompt
		if self.selected_block_ids:
			user_text += f"\n\n(User has selected: {', '.join(self.selected_block_ids)})"
		if self.image_url:
			messages.append(
				{
					"role": "user",
					"content": [
						{"type": "text", "text": user_text},
						{"type": "image_url", "image_url": {"url": self.image_url}},
					],
				}
			)
		else:
			messages.append({"role": "user", "content": user_text})
		return messages

	# --- LLM call ---------------------------------------------------------

	def call_tool_llm(self, messages: list[dict]) -> tuple[list[dict], str, list[dict]]:
		"""Stream one tool-calling completion. Returns (tool_operations,
		text_content, raw_tool_calls).

		Tool-call arguments are accumulated by index across chunks.
		`raw_tool_calls` reconstruct the assistant turn for a follow-up round.
		Large artifacts (e.g. a full page) are NOT streamed here — the model
		calls an artifact tool with a short brief, and the loop hands generation
		to that tool's generator, which streams the artifact as content.
		"""
		stream = llm.complete_with_tools(
			self.loop_model,
			messages,
			self.registry.schemas(),
			llm.TASK_PARAMS["agent"],
			api_key=self.api_key,
			stream=True,
		)

		content_parts: list[str] = []
		# index -> {"id", "name", "args"}; preserves call order across chunks.
		acc: dict[int, dict] = {}

		for chunk in stream:
			if self.is_cancelled():
				try:
					stream.close()
				except Exception:
					pass
				raise CancelledError
			self.record_usage(chunk)
			# The final include_usage chunk carries usage but no choices.
			if not chunk.choices:
				continue
			delta = chunk.choices[0].delta
			if getattr(delta, "content", None):
				content_parts.append(delta.content)
			for tc in getattr(delta, "tool_calls", None) or []:
				idx = tc.index if tc.index is not None else 0
				entry = acc.setdefault(idx, {"id": None, "name": None, "args": ""})
				if tc.id:
					entry["id"] = tc.id
				fn = getattr(tc, "function", None)
				if fn and fn.name:
					entry["name"] = fn.name
				if fn and fn.arguments:
					entry["args"] += fn.arguments

		tool_operations: list[dict] = []
		raw_tool_calls: list[dict] = []
		for idx in sorted(acc):
			entry = acc[idx]
			if not entry["name"]:
				continue
			raw_arguments = entry["args"] or ""
			try:
				args = json.loads(raw_arguments)
			except json.JSONDecodeError:
				args = {}
			logger.info(
				"AI tool response: tool=%s, raw_arguments=%s",
				entry["name"],
				BlockCodec.truncate_for_log(raw_arguments, 2000),
			)
			tool_operations.append({"tool_name": entry["name"], "args": args})
			raw_tool_calls.append(
				{
					"id": entry["id"],
					"type": "function",
					"function": {"name": entry["name"], "arguments": raw_arguments},
				}
			)

		content = "".join(content_parts)
		logger.info("Agent LLM responded: tool_calls=%d, has_text=%s", len(tool_operations), bool(content))
		return tool_operations, content, raw_tool_calls

	def _page_root(self) -> dict | None:
		"""Parse page_context_json into the root block dict, or None if empty/invalid."""
		try:
			data = json.loads(self.page_context_json)
		except (json.JSONDecodeError, TypeError):
			return None
		if isinstance(data, list):
			data = data[0] if data else None
		return data if isinstance(data, dict) else None

	@staticmethod
	def describe_operations(operations: list[dict]) -> str:
		"""A deterministic one-line summary of applied ops — used when the model
		didn't return its own summary text, so we avoid a second LLM round trip."""
		from collections import Counter

		counts = Counter(op.get("tool_name") for op in operations)

		def blk(n: int) -> str:
			return "block" if n == 1 else "blocks"

		# update_blocks edits many blocks in one op — count the blocks it touched,
		# not the single call, so the summary reads "updated 12 blocks" not "1".
		batched = 0
		for op in operations:
			if op.get("tool_name") != "update_blocks":
				continue
			args = op.get("args") or {}
			patches = args.get("patches")
			batched += len(patches) if isinstance(patches, list) else len(args.get("block_ids") or [])

		parts: list[str] = []
		if n := counts.get("add_block"):
			parts.append(f"added {n} {blk(n)}")
		if n := (counts.get("update_block", 0) + batched):
			parts.append(f"updated {n} {blk(n)}")
		if n := counts.get("remove_block"):
			parts.append(f"removed {n} {blk(n)}")
		if n := counts.get("move_block"):
			parts.append(f"moved {n} {blk(n)}")
		if counts.get("set_page_script"):
			parts.append("added a script")
		if counts.get("update_script"):
			parts.append("updated a script")

		if not parts:
			n = len(operations)
			return f"Applied {n} change{'s' if n != 1 else ''} to the page."
		sentence = parts[0] if len(parts) == 1 else f"{', '.join(parts[:-1])} and {parts[-1]}"
		return sentence[0].upper() + sentence[1:] + "."

	# --- orchestration ----------------------------------------------------

	def _emit_cancelled(self) -> None:
		msg = "Cancelled."
		AISession.try_append_message(
			self.session_id, "assistant", msg, message_type="status", metadata={"status": "cancelled"}
		)
		frappe.db.commit()
		self.emit("complete", message=msg)

	def run(self):
		# Clear any stale cancel flag from a previous turn before starting.
		self.clear_cancel_flag()
		started = time.monotonic()
		# Editing an existing page runs the loop on the user's CHOSEN model — edit
		# taste matters as much as generation taste, and silently downgrading a
		# deliberately-picked heavy model is the surest way to degrade output. Only
		# the lightweight new-page conversation (clarify/plan on an empty page) drops
		# to the cheap model; full-page generation always uses the heavy model inside
		# the artifact generator regardless.
		has_content = self._page_root() is not None
		self.loop_model = self.model if has_content else ModelRegistry.get_simple(self.model)
		logger.info(
			f"AgentRunner.run: page_id={self.page_id}, model={self.model}, loop_model={self.loop_model}, "
			f"session_id={self.session_id}, user={self.user}"
		)
		label = ModelRegistry.get_label(self.loop_model)
		self.emit("progress", message=f"Thinking with {label}" if label else "Thinking…")

		if self.session_id and AISession.is_session_running(self.session_id):
			logger.warning(f"AgentRunner.run: session {self.session_id} already running, rejecting")
			self.emit(
				"error", message="Another AI request is still processing. Please wait for it to finish."
			)
			return

		if self.session_id:
			try:
				AISession(frappe.get_doc(AISession.DOCTYPE, self.session_id)).set_running()
			except Exception:
				pass

		messages = self.build_messages()
		client_operations: list[dict] = []
		summary_text = ""

		try:
			for _round in range(MAX_ROUNDS):
				tool_operations, summary_text, raw_tool_calls = self.call_tool_llm(messages)
				self.record_round(_round, tool_operations, summary_text)

				# Classify each call. Artifact tools (e.g. generate_page) take
				# precedence over their nominal side — they're handled by their
				# generator, not emitted as a plain client op.
				terminal_ops, artifact_ops, server_ops, client_ops = [], [], [], []
				for op in tool_operations:
					tool = self.registry.get(op["tool_name"])
					if tool and tool.artifact:
						artifact_ops.append(op)
					elif self.registry.side(op["tool_name"]) == "terminal":
						terminal_ops.append(op)
					elif self.registry.side(op["tool_name"]) == "server":
						server_ops.append(op)
					else:
						client_ops.append(op)
				# A terminal tool ends the turn and hands control back to the user.
				# If the model emits more than one, the first wins (the turn is over).
				if terminal_ops:
					self.handle_terminal(terminal_ops[0])
					return

				# An artifact tool (full-page generation) is the turn's work:
				# its generator streams the artifact live on the heavy model and
				# returns the canonical client op(s). Generation ends the loop.
				if artifact_ops:
					self.stop_reason = "generated"
					self.ensure_revert_snapshot()  # generate_page replaces the block tree
					for op in artifact_ops:
						tool = self.registry.get(op["tool_name"])
						if tool and tool.generator:
							ops = tool.generator(self, op["args"])
							client_operations.extend(ops)
							if ops:
								self.emit("tool_batch", operations=ops)
					break

				# Apply this round's edits immediately so the canvas updates live and the
				# user sees progress during a long multi-block change.
				if client_ops:
					if any(op["tool_name"] in BLOCK_TOOLS for op in client_ops):
						self.ensure_revert_snapshot()
					client_operations.extend(client_ops)
					self.emit("tool_batch", operations=client_ops)

				# Keep looping as long as the model is still calling tools. A page-wide
				# change (translate every block, restyle all buttons) spans several rounds,
				# emitting a batch each round; the model ENDS the turn by replying with a
				# final summary and NO tool calls. (Previously the loop broke after the
				# first client-only round, so bulk edits silently did just the first few.)
				if not tool_operations:
					self.stop_reason = "model_finished"
					break

				messages.append(
					{"role": "assistant", "content": summary_text or None, "tool_calls": raw_tool_calls}
				)
				for tc_dict, op in zip(raw_tool_calls, tool_operations, strict=True):
					tool = self.registry.get(op["tool_name"])
					if tool and tool.side == "server" and tool.handler:
						content = tool.handler(self, op["args"])
					else:
						content = "Applied."
					messages.append({"role": "tool", "tool_call_id": tc_dict["id"], "content": content})
			else:
				# Loop ran the full MAX_ROUNDS without the model finishing — a very large
				# bulk edit or a stuck loop. The work done so far still applies.
				self.stop_reason = "max_rounds"

		except CancelledError:
			self._emit_cancelled()
			return
		except Exception as e:
			logger.error(f"Agent LLM call failed: {e!s}", exc_info=True)
			frappe.log_error(f"Agent LLM call failed: {e}", "AgentRunner.run")
			# Show a generic message to the user — raw provider/exception strings can
			# leak internals (keys, model ids, stack detail). Full error is logged above.
			user_msg = "Something went wrong while building your changes. Please try again."
			AISession.try_append_message(
				self.session_id, "assistant", user_msg, message_type="status", metadata={"status": "error"}
			)
			frappe.db.commit()  # commit before emit so the client's reload sees it
			self.emit("error", message=user_msg)
			return
		finally:
			self.clear_cancel_flag()
			if self.session_id:
				try:
					AISession(frappe.get_doc(AISession.DOCTYPE, self.session_id)).clear_running()
				except Exception:
					pass

		# Defensive: a weaker model may emit page YAML as content instead of
		# calling generate_page. Treat that as a synthetic generate_page op.
		if not client_operations and _looks_like_page_yaml(summary_text):
			logger.info("Recovering YAML-as-content into a synthetic generate_page op")
			yaml_text = BlockCodec.strip_fences(summary_text)
			op = {"tool_name": "generate_page", "args": {"yaml": yaml_text}}
			client_operations.append(op)
			self.ensure_revert_snapshot()
			self.emit("stream", chunk=yaml_text, kind="page_yaml")
			self.emit("tool_batch", operations=[op])
			summary_text = ""

		if not client_operations and not summary_text:
			logger.warning("Agent returned empty response (no tools, no text)")
			self.emit("error", message="The AI returned an empty response. Please try rephrasing.")
			return

		# Block/script edits and generation ops were already emitted incrementally inside
		# the loop (live canvas progress); nothing more to emit here.
		generated = any(op["tool_name"] == "generate_page" for op in client_operations)
		if summary_text:
			# The model wrote a summary alongside its tool calls — richest, and
			# free (no extra round trip). Prefer it whenever present.
			self.emit("stream", chunk=summary_text)
		elif generated:
			# Skip a summary call after generation (the YAML arg would bloat its
			# context); send a fixed nudge instead.
			summary_text = (
				"Created the page. Ask me to refine it — adjust styles, add sections, or change the layout."
			)
			self.emit("stream", chunk=summary_text)
		else:
			# Block/script edits with no model text: synthesise the summary from
			# the ops rather than making a second LLM call. The canvas already
			# updated from the tool_batch above; this just ends the turn sooner.
			summary_text = self.describe_operations(client_operations)
			self.emit("stream", chunk=summary_text)

		# The revert snapshot was created lazily during the loop, the first time a block
		# change was applied (see ensure_revert_snapshot). Script-only / no-op / clarify
		# turns never trigger it, so they carry no revert handle.
		elapsed_ms = round((time.monotonic() - started) * 1000)
		logger.info(
			"AI turn done | page=%s rounds=%d llm_calls=%d prompt_tokens=%d "
			"completion_tokens=%d total_tokens=%d elapsed_ms=%d stop=%s",
			self.page_id,
			len(self.trace),
			self.usage["calls"],
			self.usage["prompt_tokens"],
			self.usage["completion_tokens"],
			self.usage["total_tokens"],
			elapsed_ms,
			self.stop_reason or "model_finished",
		)
		final_metadata = {
			"status": "complete",
			"model": self.model,
			"operations": len(client_operations),
			# Trace for the agent debugger: why the turn ended + what the model did each
			# round. Explains cases like "only 2 blocks updated" at a glance.
			"debug": {
				"stopReason": self.stop_reason or "model_finished",
				"loopModel": self.loop_model,
				"rounds": len(self.trace),
				# Per-turn cost signal for the selector/tiered-context experiment.
				"tokens": self.usage,
				"elapsedMs": elapsed_ms,
				"trace": self.trace,
			},
		}
		if self.revert_snapshot:
			final_metadata["revertSnapshot"] = self.revert_snapshot
		AISession.try_append_message(
			self.session_id,
			"assistant",
			summary_text or f"Applying {len(client_operations)} change(s).",
			message_type="chat",
			task_type="agent",
			metadata=final_metadata,
		)
		frappe.db.commit()  # commit before emit so the client's reload sees the final turn
		self.emit("complete", message=summary_text or "Done")

	def handle_terminal(self, op: dict):
		"""Run a terminal tool's handler (which emits the appropriate event and
		persists the message). Terminal tools register a handler."""
		tool = self.registry.get(op["tool_name"])
		if tool and tool.handler:
			tool.handler(self, op["args"])


def run_agent_job(prompt: str, page_context_json: str, model: str, api_key: str, **kwargs):
	AgentRunner(prompt, page_context_json, model, api_key, **kwargs).run()
