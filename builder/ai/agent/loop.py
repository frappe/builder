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


_JSON_UNESCAPE = {"n": "\n", "t": "\t", "r": "\r", '"': '"', "\\": "\\", "/": "/", "b": "\b", "f": "\f"}


def extract_streaming_string(partial_args: str, key: str) -> str | None:
	"""Best-effort decode of a string value from a partial JSON object.

	Given an incomplete tool-call arguments string (e.g. `{"yaml": "el: di`),
	return the decoded value of `key` so far (e.g. `el: di`), JSON-unescaping as
	we go. Returns None until the key's opening quote has been seen. The frontend
	never sees JSON escaping — only clean text.
	"""
	match = re.search(r'"' + re.escape(key) + r'"\s*:\s*"', partial_args)
	if not match:
		return None  # key's opening quote not seen yet
	out: list[str] = []
	i = match.end()
	n = len(partial_args)
	while i < n:
		ch = partial_args[i]
		if ch == "\\":
			if i + 1 >= n:
				break  # dangling escape — wait for more
			nxt = partial_args[i + 1]
			if nxt == "u" and i + 6 <= n:
				try:
					out.append(chr(int(partial_args[i + 2 : i + 6], 16)))
				except ValueError:
					pass
				i += 6
				continue
			out.append(_JSON_UNESCAPE.get(nxt, nxt))
			i += 2
			continue
		if ch == '"':
			break  # closing quote — value complete
		out.append(ch)
		i += 1
	return "".join(out)


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
		return (
			f"Current page structure (YAML — use the 'id' values as blockIds):\n{to_compact_yaml(compressed)}"
		)

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

		Tool-call arguments are accumulated by index across chunks. For a tool
		that declares `stream_arg` (e.g. generate_page → "yaml"), the value is
		decoded incrementally and emitted to the client as it arrives, so the
		page renders live. `raw_tool_calls` reconstruct the assistant turn for a
		follow-up round.
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
		emitted: dict[int, int] = {}  # index -> chars of stream_arg already emitted

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
					tool = self.registry.get(entry["name"]) if entry["name"] else None
					if tool and tool.stream_arg:
						decoded = extract_streaming_string(entry["args"], tool.stream_arg)
						if decoded is not None and len(decoded) > emitted.get(idx, 0):
							self.emit("stream", chunk=decoded[emitted.get(idx, 0) :], kind="page_yaml")
							emitted[idx] = len(decoded)

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

	def should_use_full_model(self) -> bool:
		"""Use the user's selected (full) model only when full-page generation is
		imminent: the page is empty AND the user just approved a proposed plan.
		Clarification, planning, and targeted edits all run on the fast model so
		the refine loop stays snappy."""
		root = self._page_root()
		page_empty = root is None or not (root.get("children") or root.get("c"))
		if not page_empty:
			return False
		return AISession.last_assistant_was_plan(self.session_id)

	def stream_summary(self, messages: list[dict], tool_operations: list[dict]) -> str:
		"""Generate a short markdown summary of the applied changes, streamed to
		the client. Kept context-light so the flash model stays fast."""
		last_user = next(
			(m for m in reversed(messages) if m.get("role") == "user" and isinstance(m.get("content"), str)),
			None,
		)
		summary_messages = [
			*(([last_user]) if last_user else []),
			{
				"role": "assistant",
				"content": None,
				"tool_calls": [
					{
						"id": f"call_{i}",
						"type": "function",
						"function": {"name": op["tool_name"], "arguments": json.dumps(op["args"])},
					}
					for i, op in enumerate(tool_operations)
				],
			},
			*[
				{"role": "tool", "tool_call_id": f"call_{i}", "content": "Applied successfully."}
				for i, op in enumerate(tool_operations)
			],
			{"role": "user", "content": "Briefly describe what was changed (1–2 sentences, as markdown)."},
		]

		summary_text = ""
		try:
			for chunk in llm.complete(
				ModelRegistry.get_simple(self.model),
				summary_messages,
				llm.TASK_PARAMS["simple"],
				stream=True,
				api_key=self.api_key,
			):
				if delta := chunk.choices[0].delta.content:
					summary_text += delta
					self.emit("stream", chunk=delta)
		except Exception as e:
			logger.warning(f"Failed to generate summary text: {e!s}")
			n = len(tool_operations)
			summary_text = f"Applying {n} change{'s' if n != 1 else ''} to the page."
			self.emit("stream", chunk=summary_text)

		return summary_text

	# --- generation fast-path --------------------------------------------

	def _run_generation_fastpath(self):
		"""Stream the page YAML as plain content (no tool envelope) so the
		canvas renders live during the LLM completion. Used only when the user
		just approved a plan; at the end we synthesize a generate_page tool op
		so the final state is the canonical, fully-parsed YAML."""
		plan = AISession.latest_plan(self.session_id) or {}
		plan_recap = ""
		if plan:
			sections = "\n".join(f"- {s}" for s in (plan.get("sections") or []))
			plan_recap = (
				"User-approved plan to build now:\n"
				f"Headline: {plan.get('headline', '')}\n"
				f"Sections:\n{sections}\n"
				f"Palette: {plan.get('palette', '')}"
			)

		messages: list[dict] = [
			{"role": "system", "content": Prompts.GENERATION_YAML, "cache_control": {"type": "ephemeral"}},
		]
		if plan_recap:
			messages.append({"role": "system", "content": plan_recap})

		# Prior conversation as proper role-tagged turns.
		messages.extend(AISession.build_context_messages_from_id(self.session_id))

		user_text = self.prompt
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

		self.emit("progress", message="Building the page…")

		yaml_content = ""
		try:
			stream = llm.complete(
				self.loop_model,
				messages,
				llm.TASK_PARAMS["complex"],
				stream=True,
				api_key=self.api_key,
			)
			for chunk in stream:
				if self.is_cancelled():
					try:
						stream.close()
					except Exception:
						pass
					self._emit_cancelled()
					return
				delta = chunk.choices[0].delta.content
				if delta:
					yaml_content += delta
					self.emit("stream", chunk=delta, kind="page_yaml")
		except Exception as e:
			logger.error(f"Generation fast-path failed: {e!s}", exc_info=True)
			frappe.log_error(f"Generation fast-path failed: {e}", "AgentRunner.fastpath")
			AISession.try_append_message(
				self.session_id, "assistant", str(e), message_type="status", metadata={"status": "error"}
			)
			frappe.db.commit()
			self.emit("error", message=str(e))
			return

		yaml_text = BlockCodec.strip_fences(yaml_content).strip()
		if not yaml_text:
			self.emit("error", message="The AI returned an empty response. Please try rephrasing.")
			return

		# Canonical final apply — re-applies the full YAML so the canvas matches
		# what the frontend can parse cleanly, not the last partial stream state.
		self.emit("tool_batch", operations=[{"tool_name": "generate_page", "args": {"yaml": yaml_text}}])

		summary_text = (
			"Created the page. Ask me to refine it — adjust styles, add sections, or change the layout."
		)
		self.emit("stream", chunk=summary_text)

		AISession.try_append_message(
			self.session_id,
			"assistant",
			summary_text,
			message_type="chat",
			task_type="agent",
			metadata={"status": "complete", "model": self.model, "operations": 1},
		)
		frappe.db.commit()
		self.emit("complete", message=summary_text)

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
		# Tiered model: full model only when generation is imminent, else fast model.
		self.loop_model = self.model if self.should_use_full_model() else ModelRegistry.get_simple(self.model)
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

		# Fast-path: when generation is imminent (user just approved a plan),
		# stream raw YAML directly to the canvas instead of going through
		# tool-calling — provider tool-call argument streaming is unreliable,
		# leaving the user staring at a blank canvas for the whole completion.
		if self.should_use_full_model():
			try:
				self._run_generation_fastpath()
			finally:
				self.clear_cancel_flag()
				if self.session_id:
					try:
						AISession(frappe.get_doc(AISession.DOCTYPE, self.session_id)).clear_running()
					except Exception:
						pass
			return

		messages = self.build_messages()
		client_operations: list[dict] = []
		summary_text = ""

		try:
			for _round in range(MAX_ROUNDS):
				tool_operations, summary_text, raw_tool_calls = self.call_tool_llm(messages)

				terminal_ops = [
					op for op in tool_operations if self.registry.side(op["tool_name"]) == "terminal"
				]
				server_ops = [op for op in tool_operations if self.registry.side(op["tool_name"]) == "server"]
				client_ops = [op for op in tool_operations if self.registry.side(op["tool_name"]) == "client"]
				client_operations.extend(client_ops)

				# A terminal tool ends the turn and hands control back to the user.
				# If the model emits more than one, the first wins (the turn is over).
				if terminal_ops:
					self.handle_terminal(terminal_ops[0])
					return

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
			self.emit("stream", chunk=summary_text)
		elif generated:
			# Skip the extra summary call after generation (the YAML arg would
			# bloat its context); send a fixed nudge instead.
			summary_text = (
				"Created the page. Ask me to refine it — adjust styles, add sections, or change the layout."
			)
			self.emit("stream", chunk=summary_text)
		else:
			summary_text = self.stream_summary(messages, client_operations)

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
