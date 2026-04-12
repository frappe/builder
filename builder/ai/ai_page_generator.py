import json
import logging

import frappe
import litellm
from frappe import _

from builder.ai.ai_agent import run_agent_job
from builder.ai.ai_block_codec import BlockCodec
from builder.ai.ai_llm import TASK_PARAMS, call_llm
from builder.ai.ai_models import ModelRegistry
from builder.ai.ai_prompts import Prompts, parse_clarification
from builder.ai.ai_session import AISession
from builder.utils import has_page_write

litellm.drop_params = True
logger = frappe.logger("builder.ai_page_generator")
logger.setLevel(logging.INFO)


class LLMJob:
	def __init__(
		self,
		prompt: str,
		model: str,
		api_key: str,
		event_prefix: str,
		is_modify: bool,
		*,
		user: str | None = None,
		page_id: str | None = None,
		block_context: str | None = None,
		task_type: str | None = None,
		image_url: str | None = None,
		session_id: str | None = None,
	):
		self.prompt = prompt
		self.model = model
		self.api_key = api_key
		self.event_prefix = event_prefix
		self.is_modify = is_modify
		self.user = user or frappe.session.user
		self.page_id = page_id
		self.block_context = block_context
		self.task_type = task_type
		self.image_url = image_url
		self.session_id = session_id

	def emit(self, suffix: str, **kwargs):
		event = f"{self.event_prefix}_{suffix}"
		if self.page_id:
			event = f"{event}_{self.page_id}"
		frappe.publish_realtime(
			event,
			{"page_id": self.page_id, "task_type": self.task_type, **kwargs},
			user=self.user,
		)

	def build_user_content(self, stripped_context: str | None) -> str | list:
		if self.is_modify and stripped_context:
			if self.task_type == "rewrite_text":
				text = f'Text content to rewrite: "{stripped_context}"\n\nInstruction: {self.prompt}'
			elif self.task_type == "replace_image":
				text = f"Current image attributes:\n{stripped_context}\n\nInstruction: {self.prompt}"
			else:
				text = f"Block:\n{stripped_context}\n\nChange: {self.prompt}"
		else:
			text = f"Create a page for: {self.prompt}"

		effective_image = self.image_url if self.task_type not in {"rewrite_text", "replace_image"} else None
		if effective_image:
			return [
				{"type": "text", "text": text},
				{"type": "image_url", "image_url": {"url": effective_image}},
			]
		return text

	def completion_summary(self, block_id: str | None = None) -> str | None:
		if self.task_type == "rewrite_text":
			return "Rewrote the selected text content."
		if self.task_type == "replace_image":
			return "Replaced the selected image."
		if self.is_modify:
			return f"Applied an inline update{(' to block ' + block_id) if block_id else ''}."
		return "Page generated successfully."

	def run(self):
		logger.info(
			f"LLMJob.run: event={self.event_prefix}, page_id={self.page_id}, "
			f"is_modify={self.is_modify}, task_type={self.task_type}, session_id={self.session_id}"
		)

		task_tier = Prompts.classify_task(is_modify=self.is_modify, task_type=self.task_type)
		params = TASK_PARAMS[task_tier]
		model = ModelRegistry.get_simple(self.model) if task_tier == "simple" else self.model

		action = "Modifying" if self.is_modify else "Generating"
		self.emit(
			"progress",
			status="generating",
			message=f"{action} with {ModelRegistry.get_label(model)}",
			task_tier=task_tier,
			model_used=model,
			total_length=0,
		)

		original_id = None
		stripped_context = None
		if self.is_modify and self.block_context:
			original_id = BlockCodec.extract_block_id(self.block_context)
			stripped_context = BlockCodec.strip_context(
				self.block_context, task_tier, task_type=self.task_type
			)

		session_context = AISession.build_context_from_id(self.session_id)

		messages = [
			{
				"role": "system",
				"content": Prompts.get_system(self.is_modify, self.task_type),
				"cache_control": {"type": "ephemeral"},
			},
		]
		if session_context:
			messages.append({"role": "system", "content": session_context})
		messages.append({"role": "user", "content": self.build_user_content(stripped_context)})

		content = ""
		try:
			last_stage = None
			for chunk in call_llm(model, messages, params, stream=True, api_key=self.api_key):
				if delta := chunk.choices[0].delta.content:
					if not content:
						self.emit("progress", message="Building...")
						last_stage = "Building..."
					content += delta
					self.emit("stream", chunk=delta, block_id=original_id, total_length=len(content))

					stage = ModelRegistry.get_progress_stage(content)
					if stage and stage != last_stage:
						last_stage = stage
						self.emit("progress", message=stage, total_length=len(content))

			logger.info(f"LLM stream response | model={model} length={len(content)}\n{content}")

		except ValueError as e:
			frappe.log_error(f"Parse error: {e}\nContent: {content}", f"{self.event_prefix} parse")
			AISession.try_append_message(
				self.session_id,
				"assistant",
				"The AI response could not be parsed into valid Builder blocks.",
				message_type="status",
				task_type=self.task_type,
				block_id=original_id,
				metadata={"status": "error"},
			)
			self.emit("error", message="Failed to parse AI response. The model returned invalid YAML.")
			return

		except Exception as e:
			logger.error(f"LLMJob failed in {self.event_prefix}: {e!s}", exc_info=True)
			frappe.log_error(f"LLM job error: {e}", self.event_prefix)
			AISession.try_append_message(
				self.session_id,
				"assistant",
				str(e),
				message_type="status",
				task_type=self.task_type,
				block_id=original_id,
				metadata={"status": "error"},
			)
			self.emit("error", message=str(e))
			return

		if clarification := parse_clarification(content):
			logger.info(f"LLMJob: clarification requested: {clarification}")
			AISession.try_append_message(
				self.session_id,
				"assistant",
				clarification["question"],
				message_type="clarification",
				task_type=self.task_type or ("modify" if self.is_modify else "generate"),
				block_id=original_id,
				metadata={"options": clarification["options"], "status": "clarification"},
			)
			self.emit(
				"clarify",
				question=clarification["question"],
				options=clarification["options"],
				block_id=original_id,
			)
			return

		summary = self.completion_summary(original_id)
		if summary:
			AISession.try_append_message(
				self.session_id,
				"assistant",
				summary,
				message_type="status",
				task_type=self.task_type or ("modify" if self.is_modify else "generate"),
				block_id=original_id,
				metadata={"status": "complete", "model": model},
			)

		success_message = "Modified block successfully" if self.is_modify else "Page generated successfully"
		self.emit(
			"complete",
			block_id=original_id,
			model_used=model,
			task_tier=task_tier,
			message=success_message,
		)


def generate_page_blocks(
	prompt: str,
	model: str,
	api_key: str,
	user: str | None = None,
	page_id: str | None = None,
	image_url: str | None = None,
	session_id: str | None = None,
):
	LLMJob(
		prompt,
		model,
		api_key,
		"ai_generation",
		is_modify=False,
		user=user,
		page_id=page_id,
		image_url=image_url,
		session_id=session_id,
	).run()


def modify_section_blocks(
	prompt: str,
	block_context: str,
	model: str,
	api_key: str,
	user: str | None = None,
	page_id: str | None = None,
	task_type: str | None = None,
	image_url: str | None = None,
	session_id: str | None = None,
):
	LLMJob(
		prompt,
		model,
		api_key,
		"ai_modify",
		is_modify=True,
		user=user,
		page_id=page_id,
		block_context=block_context,
		task_type=task_type,
		image_url=image_url,
		session_id=session_id,
	).run()


def enqueue_ai_job(fn, model=None, **kwargs):
	if not frappe.has_permission("Builder Page", ptype="write"):
		frappe.throw(_("You do not have permission to modify pages"))

	settings = frappe.get_single("Builder Settings")

	if not model:
		model = "openrouter"
	model = ModelRegistry.get_default(model)

	api_key = settings.get_password("ai_api_key", raise_exception=False)
	if not api_key:
		frappe.throw(_("Please configure an OpenRouter API key in Settings \u2192 AI"))

	frappe.enqueue(fn, model=model, api_key=api_key, user=frappe.session.user, now=True, **kwargs)
	frappe.local.response.http_status_code = 202
	return {"status": "accepted", "session_id": kwargs.get("session_id")}


@frappe.whitelist()
@has_page_write()
def get_ai_models():
	return ModelRegistry.AVAILABLE


@frappe.whitelist()
@has_page_write()
def get_ai_session(page_id: str, model: str | None = None):
	logger.info(f"get_ai_session: page_id={page_id}, model={model}")

	if not page_id or page_id == "new" or not frappe.db.exists("Builder Page", page_id):
		return {
			"session_id": "",
			"page_id": page_id,
			"selected_model": model or "",
			"last_task_type": None,
			"messages": [],
		}

	session = AISession.get_or_create(page_id, model=model)
	return {
		"session_id": session.name,
		"page_id": session.page,
		"selected_model": session.selected_model,
		"last_task_type": session.last_task_type,
		"messages": session.get_messages(),
	}


@frappe.whitelist()
@has_page_write()
def clear_ai_session(page_id: str):
	logger.info(f"clear_ai_session: page_id={page_id}")

	if not page_id or page_id == "new" or not frappe.db.exists("Builder Page", page_id):
		return {"session_id": "", "messages": []}

	session = AISession.get_or_create(page_id)
	session.clear()
	return {"session_id": session.name, "messages": []}


@frappe.whitelist()
@has_page_write()
def generate_page_from_prompt(
	prompt: str,
	page_id: str | None = None,
	model: str | None = None,
	image_data: str | None = None,
	session_id: str | None = None,
):
	logger.info(
		f"generate_page_from_prompt: page_id={page_id}, model={model}, session_id={session_id}, has_image={bool(image_data)}"
	)

	image_url = BlockCodec.validate_image_data(image_data) if image_data else None
	if page_id and session_id:
		session = AISession.get(session_id, page_id=page_id)
		generate_meta: dict = {"scope": "page"}
		if image_data:
			generate_meta["attachedImageUrl"] = image_data
		session.append_message(
			"user", prompt, message_type="chat", task_type="generate", metadata=generate_meta
		)

	return enqueue_ai_job(
		generate_page_blocks,
		prompt=prompt,
		page_id=page_id,
		model=model,
		image_url=image_url,
		session_id=session_id,
	)


@frappe.whitelist()
@has_page_write()
def modify_section_from_prompt(
	prompt: str,
	block_context: str,
	page_id: str | None = None,
	task_type: str | None = None,
	model: str | None = None,
	image_data: str | None = None,
	session_id: str | None = None,
):
	logger.info(
		f"modify_section_from_prompt: page_id={page_id}, task_type={task_type}, model={model}, session_id={session_id}"
	)

	try:
		json.loads(block_context)
	except json.JSONDecodeError:
		frappe.throw(_("Invalid block context JSON"))

	image_url = BlockCodec.validate_image_data(image_data) if image_data else None
	block_id = BlockCodec.extract_block_id(block_context)

	if page_id and session_id:
		session = AISession.get(session_id, page_id=page_id)
		session.append_message(
			"user",
			prompt,
			message_type="chat",
			task_type=task_type or "modify",
			block_id=block_id,
			metadata={"scope": "block" if block_id and block_id != "root" else "page"},
		)

	return enqueue_ai_job(
		modify_section_blocks,
		prompt=prompt,
		block_context=block_context,
		page_id=page_id,
		task_type=task_type,
		model=model,
		image_url=image_url,
		session_id=session_id,
	)


@frappe.whitelist()
@has_page_write()
def test_api_key():
	logger.info("test_api_key: Testing OpenRouter API key")
	settings = frappe.get_single("Builder Settings")
	model = settings.get("ai_model") or "openrouter"
	api_key = settings.get_password("ai_api_key", raise_exception=False)
	if not api_key:
		return {"success": False, "message": _("Please set an OpenRouter API key")}

	actual_model = ModelRegistry.get_default(model)
	if actual_model.startswith("gemini-"):
		actual_model = f"gemini/{actual_model}"

	try:
		litellm.completion(
			model=actual_model,
			messages=[{"role": "user", "content": "Say 'OK' if you can read this"}],
			max_tokens=10,
			api_key=api_key,
		)
		return {"success": True, "message": _("API key is valid")}
	except Exception as e:
		logger.error(f"test_api_key: API key validation failed: {e!s}", exc_info=True)
		return {"success": False, "message": str(e)}


@frappe.whitelist()
@has_page_write()
def run_agent_from_prompt(
	prompt: str,
	page_context: str,
	page_id: str | None = None,
	model: str | None = None,
	session_id: str | None = None,
	selected_block_ids: list | None = None,
	image_data: str | None = None,
	selected_block_context: list | None = None,
):
	logger.info(f"run_agent_from_prompt: page_id={page_id}, model={model}, session_id={session_id}")

	if not frappe.has_permission("Builder Page", ptype="write"):
		frappe.throw(_("You do not have permission to modify pages"))

	try:
		json.loads(page_context)
	except (json.JSONDecodeError, TypeError):
		frappe.throw(_("Invalid page context JSON"))

	if page_id and session_id:
		session = AISession.get(session_id, page_id=page_id)
		msg_meta: dict = {"scope": "page", "selectedBlockContext": selected_block_context or []}
		if image_data:
			msg_meta["attachedImageUrl"] = image_data
		session.append_message(
			"user",
			prompt,
			message_type="chat",
			task_type="agent",
			metadata=msg_meta,
		)

	return enqueue_ai_job(
		run_agent_job,
		prompt=prompt,
		page_context_json=page_context,
		page_id=page_id,
		session_id=session_id,
		model=model,
		selected_block_ids=selected_block_ids,
		image_url=image_data,
	)
