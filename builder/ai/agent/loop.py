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

import frappe

from builder.ai import llm
from builder.ai.agent.registry import ToolRegistry, build_default_registry
from builder.ai.block_codec import BlockCodec
from builder.ai.models import ModelRegistry
from builder.ai.prompts import Prompts
from builder.ai.session import AISession
from builder.utils import to_compact_yaml

logger = frappe.logger("builder.ai.agent.loop")
logger.setLevel(logging.INFO)

MAX_ROUNDS = 100
EVENT_PREFIX = "ai_chat"


class CancelledError(Exception):
	"""Raised inside the stream loops when the user cancels the turn."""


def _looks_like_page_yaml(text: str) -> bool:
	"""Heuristic: did the model emit page YAML as plain content?"""
	if not text:
		return False
	stripped = re.sub(r"^```(?:yaml)?\s*", "", text.strip())
	return stripped.startswith(("el:", "- el:", "id: root", "- id:"))


class AgentRunner:
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
		# Tiered model selection: resolved in run() once we know the scenario.
		self.loop_model = self.model

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

	# --- message construction --------------------------------------------

	def build_page_context(self) -> str:
		root = self._page_root()
		if root is None:
			return ""
		compressed = BlockCodec.compress(root, depth=0, task_tier="complex")
		return f"Current page structure (YAML — pass a block's 'ref' value as block_id to edit it):\n{to_compact_yaml(compressed)}"

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

		parts: list[str] = []
		if n := counts.get("add_block"):
			parts.append(f"added {n} {blk(n)}")
		if n := counts.get("update_block"):
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
		# The conversational loop always runs on the fast model (clarify, plan,
		# targeted edits). Full-page generation runs on the user's selected heavy
		# model, but inside the artifact generator — not here.
		self.loop_model = ModelRegistry.get_simple(self.model)
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
				client_operations.extend(client_ops)

				# A terminal tool ends the turn and hands control back to the user.
				# If the model emits more than one, the first wins (the turn is over).
				if terminal_ops:
					self.handle_terminal(terminal_ops[0])
					return

				# An artifact tool (full-page generation) is the turn's work:
				# its generator streams the artifact live on the heavy model and
				# returns the canonical client op(s). Generation ends the loop.
				if artifact_ops:
					for op in artifact_ops:
						tool = self.registry.get(op["tool_name"])
						if tool and tool.generator:
							client_operations.extend(tool.generator(self, op["args"]))
					break

				if not server_ops:
					break

				# Resolve server tools, feed results back, and loop.
				messages.append(
					{"role": "assistant", "content": summary_text or None, "tool_calls": raw_tool_calls}
				)
				for tc_dict, op in zip(raw_tool_calls, tool_operations, strict=True):
					tool = self.registry.get(op["tool_name"])
					if tool and tool.side == "server" and tool.handler:
						content = tool.handler(self, op["args"])
					else:
						content = "Will be applied by the frontend."
					messages.append({"role": "tool", "tool_call_id": tc_dict["id"], "content": content})

		except CancelledError:
			self._emit_cancelled()
			return
		except Exception as e:
			logger.error(f"Agent LLM call failed: {e!s}", exc_info=True)
			frappe.log_error(f"Agent LLM call failed: {e}", "AgentRunner.run")
			AISession.try_append_message(
				self.session_id, "assistant", str(e), message_type="status", metadata={"status": "error"}
			)
			frappe.db.commit()  # commit before emit so the client's reload sees it
			self.emit("error", message=str(e))
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
			client_operations.append({"tool_name": "generate_page", "args": {"yaml": yaml_text}})
			self.emit("stream", chunk=yaml_text, kind="page_yaml")
			summary_text = ""

		if not client_operations and not summary_text:
			logger.warning("Agent returned empty response (no tools, no text)")
			self.emit("error", message="The AI returned an empty response. Please try rephrasing.")
			return

		if client_operations:
			logger.info(f"Emitting {len(client_operations)} tool operations to frontend")
			self.emit("tool_batch", operations=client_operations)

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

		AISession.try_append_message(
			self.session_id,
			"assistant",
			summary_text or f"Applying {len(client_operations)} change(s).",
			message_type="chat",
			task_type="agent",
			metadata={"status": "complete", "model": self.model, "operations": len(client_operations)},
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
