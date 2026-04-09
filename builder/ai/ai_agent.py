import json
import logging

import frappe
import litellm

from builder.ai.ai_block_codec import BlockCodec
from builder.ai.ai_llm import TASK_PARAMS, call_llm
from builder.ai.ai_models import ModelRegistry
from builder.ai.ai_prompts import Prompts
from builder.ai.ai_session import AISession
from builder.utils import to_compact_yaml

logger = frappe.logger("builder.ai_agent")
logger.setLevel(logging.INFO)

AGENT_TOOLS = [
	{
		"type": "function",
		"function": {
			"name": "update_block",
			"description": (
				"Merge style, attribute, or content changes into an existing block. "
				"Use this to change colours, fonts, spacing, text, HTML attributes, "
				"element type, or class names on ANY block at any nesting depth. "
				"Make sure to set units on style values (e.g. padding: '10px' not just 10)."
			),
			"parameters": {
				"type": "object",
				"properties": {
					"block_id": {
						"type": "string",
						"description": "The blockId of the target block (from the page YAML).",
					},
					"base_styles": {
						"type": "object",
						"description": "CSS-in-JS camelCase style properties to merge into baseStyles (desktop). E.g. {backgroundColor: '#ff0000'}.",
					},
					"mobile_styles": {
						"type": "object",
						"description": "CSS-in-JS style properties to merge into mobileStyles.",
					},
					"tablet_styles": {
						"type": "object",
						"description": "CSS-in-JS style properties to merge into tabletStyles.",
					},
					"attributes": {
						"type": "object",
						"description": "HTML attributes to merge (e.g. {href: '/about', target: '_blank'} for links, {src: '...', alt: '...'} for images, {id: 'hero-section'} for HTML id). Do not use this for block identity; block_id is separate.",
					},
					"inner_text": {
						"type": "string",
						"description": "Replace the text content of the block (plain text).",
					},
					"inner_html": {
						"type": "string",
						"description": "Replace the inner HTML of the block (use for rich content).",
					},
					"element": {
						"type": "string",
						"description": "Change the HTML element tag (e.g. 'h1', 'button', 'a').",
					},
					"classes": {
						"type": "array",
						"items": {"type": "string"},
						"description": "Replace the classes array on the block.",
					},
				},
				"required": ["block_id"],
			},
		},
	},
	{
		"type": "function",
		"function": {
			"name": "add_block",
			"description": (
				"Insert a new block as a child of an existing block. "
				"Use this to add sections, components, or elements anywhere in the page tree."
			),
			"parameters": {
				"type": "object",
				"properties": {
					"parent_block_id": {
						"type": "string",
						"description": "The blockId of the parent block that will contain the new block.",
					},
					"block": {
						"type": "object",
						"description": (
							"The new block definition using compact YAML schema: "
							"el (element tag), name (optional label), style (CSS-in-JS dict), "
							"m_style (mobile styles), t_style (tablet styles), "
							"attrs (HTML attributes, including attrs.id for HTML id), text (text content), "
							"classes (list of CSS classes), c (children array). "
							"Do NOT include an 'id' field — one will be auto-assigned."
						),
					},
					"after_block_id": {
						"type": "string",
						"description": "Insert the new block immediately after this sibling blockId. Takes precedence over 'index'.",
					},
					"index": {
						"type": "integer",
						"description": "Zero-based position in the parent's children list. Defaults to appending at the end.",
					},
				},
				"required": ["parent_block_id", "block"],
			},
		},
	},
	{
		"type": "function",
		"function": {
			"name": "remove_block",
			"description": "Delete an existing block (and all its descendants) from the page.",
			"parameters": {
				"type": "object",
				"properties": {
					"block_id": {
						"type": "string",
						"description": "The blockId of the block to delete.",
					},
				},
				"required": ["block_id"],
			},
		},
	},
	{
		"type": "function",
		"function": {
			"name": "move_block",
			"description": (
				"Move an existing block to a different parent, or reorder it within the same parent."
			),
			"parameters": {
				"type": "object",
				"properties": {
					"block_id": {
						"type": "string",
						"description": "The blockId of the block to move.",
					},
					"new_parent_block_id": {
						"type": "string",
						"description": "The blockId of the new parent block.",
					},
					"after_block_id": {
						"type": "string",
						"description": "Place the block immediately after this sibling blockId in the new parent. Takes precedence over 'index'.",
					},
					"index": {
						"type": "integer",
						"description": "Zero-based position in the new parent's children list. Defaults to appending at the end.",
					},
				},
				"required": ["block_id", "new_parent_block_id"],
			},
		},
	},
	{
		"type": "function",
		"function": {
			"name": "set_page_script",
			"description": (
				"Create a new JavaScript or CSS client script and attach it to the page. "
				"Use this to add event listeners, animations, dynamic behaviour, fetch calls, "
				"or any page-level code that cannot be expressed via block styles alone."
			),
			"parameters": {
				"type": "object",
				"properties": {
					"script": {
						"type": "string",
						"description": "The full JavaScript or CSS source code to add to the page.",
					},
					"script_type": {
						"type": "string",
						"enum": ["JavaScript", "CSS"],
						"description": "Whether this is a JavaScript or CSS script. Defaults to 'JavaScript'.",
					},
				},
				"required": ["script"],
			},
		},
	},
	{
		"type": "function",
		"function": {
			"name": "get_page_scripts",
			"description": (
				"Fetch the JavaScript and/or CSS scripts attached to this page. "
				"Call this before using update_script so you can read the existing code. "
				"Pass script_type to fetch only one kind."
			),
			"parameters": {
				"type": "object",
				"properties": {
					"script_type": {
						"type": "string",
						"enum": ["JavaScript", "CSS"],
						"description": "Return only scripts of this type. Omit to return all scripts.",
					},
				},
				"required": [],
			},
		},
	},
	{
		"type": "function",
		"function": {
			"name": "update_script",
			"description": (
				"Replace the source code of an existing page script. "
				"You MUST call get_page_scripts first and copy the exact 'script_name' value "
				"from that response — do not guess or invent a name."
			),
			"parameters": {
				"type": "object",
				"properties": {
					"script_name": {
						"type": "string",
						"description": "The exact 'script_name' value returned by get_page_scripts (e.g. 'BSC-00001'). Never invent this value.",
					},
					"script": {
						"type": "string",
						"description": "The new full source code that replaces the existing script content.",
					},
					"script_type": {
						"type": "string",
						"enum": ["JavaScript", "CSS"],
						"description": "Change the script type. Omit to keep the existing type.",
					},
				},
				"required": ["script_name", "script"],
			},
		},
	},
]


class AgentJob:
	TOOLS = AGENT_TOOLS
	SYSTEM_PROMPT = Prompts.AGENT

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
	):
		self.prompt = prompt
		self.page_context_json = page_context_json
		self.model = model
		self.api_key = api_key
		self.user = user or frappe.session.user
		self.page_id = page_id
		self.session_id = session_id

	def emit(self, suffix: str, **kwargs):
		event = f"ai_agent_{suffix}"
		if self.page_id:
			event = f"{event}_{self.page_id}"
		frappe.publish_realtime(event, {"page_id": self.page_id, **kwargs}, user=self.user)

	def build_page_context(self) -> str:
		try:
			data = json.loads(self.page_context_json)
			root = data[0] if isinstance(data, list) else data
			if not isinstance(root, dict):
				return ""
			compressed = BlockCodec.compress(root, depth=0, task_tier="complex")
			return f"Current page structure (YAML — use the 'id' values as blockIds):\n{to_compact_yaml(compressed)}"
		except (json.JSONDecodeError, TypeError):
			return ""

	def build_messages(self) -> list[dict]:
		messages: list[dict] = [
			{
				"role": "system",
				"content": self.SYSTEM_PROMPT,
				"cache_control": {"type": "ephemeral"},
			},
		]
		session_context = AISession.build_context_from_id(self.session_id)
		if session_context:
			messages.append({"role": "system", "content": session_context})

		page_context_message = self.build_page_context()
		if page_context_message:
			messages.append({"role": "user", "content": page_context_message})
			messages.append(
				{
					"role": "assistant",
					"content": "Understood. I have the current page structure. What would you like me to change?",
				}
			)
		messages.append({"role": "user", "content": self.prompt})
		return messages

	def fetch_page_scripts(self, script_type: str | None = None) -> str:
		"""Query DB for scripts attached to this page and return as JSON string."""
		if not self.page_id:
			return json.dumps([])
		try:
			script_names = frappe.db.get_all(
				"Builder Page Client Script",
				filters={"parent": self.page_id, "parenttype": "Builder Page"},
				pluck="builder_script",
			)
			if not script_names:
				return json.dumps([])
			filters: dict = {"name": ["in", script_names]}
			if script_type:
				filters["script_type"] = script_type
			scripts = frappe.db.get_all(
				"Builder Client Script",
				filters=filters,
				fields=["name", "script_type", "script"],
			)
			return json.dumps(
				[{"script_name": s.name, "script_type": s.script_type, "script": s.script} for s in scripts]
			)
		except Exception as e:
			logger.warning(f"fetch_page_scripts failed: {e}")
			return json.dumps([])

	def call_tool_llm(self, messages: list[dict]) -> tuple[list[dict], str, list[dict]]:
		"""Returns (tool_operations, text_content, raw_tool_calls) where raw_tool_calls
		are serialisable dicts needed to reconstruct the assistant turn for a follow-up round."""
		llm_model = ModelRegistry.get_simple(self.model)
		resolved_model = f"gemini/{llm_model}" if llm_model.startswith("gemini-") else llm_model

		if "claude-" in llm_model:
			for m in messages:
				if m["role"] == "system" and isinstance(m.get("content"), str):
					m["content"] = [{"type": "text", "text": m["content"]}]

		logger.debug(f"Calling agent LLM with tools: {[t['function']['name'] for t in self.TOOLS]}")
		resp = litellm.completion(
			model=resolved_model,
			messages=messages,
			stream=False,
			api_key=self.api_key,
			tools=self.TOOLS,
			**TASK_PARAMS["simple"],
		)
		choice = resp.choices[0]
		assistant_message = choice.message
		logger.info(
			"Agent LLM responded: has_tool_calls=%s, has_text=%s",
			bool(assistant_message.tool_calls),
			bool(assistant_message.content),
		)

		tool_operations = []
		raw_tool_calls: list[dict] = []
		if assistant_message.tool_calls:
			for tc in assistant_message.tool_calls:
				raw_arguments = tc.function.arguments or ""
				try:
					args = json.loads(raw_arguments)
				except json.JSONDecodeError:
					args = {}
				logger.info(
					"AI tool response: tool=%s, raw_arguments=%s",
					tc.function.name,
					BlockCodec.truncate_for_log(raw_arguments, 2000),
				)
				tool_operations.append({"tool_name": tc.function.name, "args": args})
				raw_tool_calls.append(
					{
						"id": tc.id,
						"type": "function",
						"function": {"name": tc.function.name, "arguments": raw_arguments},
					}
				)

		return tool_operations, assistant_message.content or "", raw_tool_calls

	def stream_summary(self, messages: list[dict], tool_operations: list[dict]) -> str:
		summary_messages = [
			*messages,
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
			{"role": "user", "content": "Briefly describe what was changed (1–2 sentences, plain text)."},
		]

		summary_text = ""
		try:
			for chunk in call_llm(
				ModelRegistry.get_simple(self.model),
				summary_messages,
				TASK_PARAMS["simple"],
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

	def run(self):
		logger.info(
			f"AgentJob.run: page_id={self.page_id}, model={self.model}, session_id={self.session_id}, user={self.user}"
		)
		self.emit("progress", message=f"Thinking with {ModelRegistry.get_label(self.model)}…")

		messages = self.build_messages()
		client_tool_operations: list[dict] = []
		summary_text = ""

		try:
			# Agentic loop: resolve server-side tools first, then hand client tools to the frontend.
			for _round in range(4):
				tool_operations, summary_text, raw_tool_calls = self.call_tool_llm(messages)

				server_ops = [op for op in tool_operations if op["tool_name"] == "get_page_scripts"]
				client_ops = [op for op in tool_operations if op["tool_name"] != "get_page_scripts"]
				client_tool_operations.extend(client_ops)

				if not server_ops:
					break

				# Append assistant turn and tool results, then loop.
				messages.append(
					{"role": "assistant", "content": summary_text or None, "tool_calls": raw_tool_calls}
				)
				for tc_dict, op in zip(raw_tool_calls, tool_operations, strict=True):
					if op["tool_name"] == "get_page_scripts":
						content = self.fetch_page_scripts(op["args"].get("script_type"))
						logger.info("Served get_page_scripts: %s bytes", len(content))
					else:
						content = "Will be applied by the frontend."
					messages.append({"role": "tool", "tool_call_id": tc_dict["id"], "content": content})

		except Exception as e:
			logger.error(f"Agent LLM call failed: {e!s}", exc_info=True)
			frappe.log_error(f"Agent LLM call failed: {e}", "AgentJob.run")
			AISession.try_append_message(
				self.session_id,
				"assistant",
				str(e),
				message_type="status",
				metadata={"status": "error"},
			)
			self.emit("error", message=str(e))
			return

		if not client_tool_operations and not summary_text:
			logger.warning("Agent returned empty response (no tools, no text)")
			self.emit("error", message="The AI returned an empty response. Please try rephrasing.")
			return

		if client_tool_operations:
			logger.info(f"Emitting {len(client_tool_operations)} tool operations to frontend")
			self.emit("tool_batch", operations=client_tool_operations)

		if not summary_text:
			summary_text = self.stream_summary(messages, client_tool_operations)
		else:
			self.emit("stream", chunk=summary_text)

		AISession.try_append_message(
			self.session_id,
			"assistant",
			summary_text or f"Applying {len(client_tool_operations)} change(s).",
			message_type="chat",
			task_type="agent",
			metadata={"status": "complete", "model": self.model, "operations": len(client_tool_operations)},
		)

		self.emit("complete", message=summary_text or "Done")


def run_agent_job(
	prompt: str,
	page_context_json: str,
	model: str,
	api_key: str,
	user: str | None = None,
	page_id: str | None = None,
	session_id: str | None = None,
):
	AgentJob(
		prompt,
		page_context_json,
		model,
		api_key,
		user=user,
		page_id=page_id,
		session_id=session_id,
	).run()
