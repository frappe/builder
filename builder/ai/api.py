"""Whitelisted endpoints for Builder AI.

A single conversational entry point — `run` — drives the unified agent loop for
everything (generation, editing, scripts, clarification). The remaining
endpoints are flow-agnostic session/model helpers.
"""

import json
import logging

import frappe
import litellm
from frappe import _

from builder.ai.agent.loop import run_agent_job
from builder.ai.block_codec import BlockCodec
from builder.ai.models import ModelRegistry
from builder.ai.session import AISession
from builder.ai.snapshots import capture_page_state
from builder.utils import has_page_write

logger = frappe.logger("builder.ai.api")
logger.setLevel(logging.INFO)


def resolve_api_key() -> str:
	api_key = frappe.get_single("Builder Settings").get_password("ai_api_key", raise_exception=False)
	if not api_key:
		frappe.throw(_("Please configure an OpenRouter API key in Settings → AI"))
	return api_key


@frappe.whitelist()
@has_page_write()
def run(
	prompt: str,
	page_context: str,
	page_id: str | None = None,
	model: str | None = None,
	session_id: str | None = None,
	selected_block_ids: list | None = None,
	image_data: str | None = None,
	selected_block_context: list | None = None,
):
	"""Single entry point: run the agent for one user turn."""
	logger.info(f"run: page_id={page_id}, model={model}, session_id={session_id}")

	try:
		json.loads(page_context)
	except (json.JSONDecodeError, TypeError):
		frappe.throw(_("Invalid page context JSON"))

	if page_id and session_id:
		if AISession.is_session_running(session_id):
			frappe.local.response.http_status_code = 429
			return {"status": "busy", "message": _("Another AI request is still processing. Please wait.")}

		session = AISession.get(session_id, page_id=page_id)
		msg_meta: dict = {"selectedBlockContext": selected_block_context or []}
		if image_data:
			msg_meta["attachedImageUrl"] = image_data
		session.append_message("user", prompt, message_type="chat", task_type="agent", metadata=msg_meta)

	resolved_model = ModelRegistry.get_default(model or "openrouter")
	if not ModelRegistry.is_known_model(resolved_model):
		frappe.throw(_("Unknown AI model: {0}").format(resolved_model))
	api_key = resolve_api_key()
	image_url = BlockCodec.validate_image_data(image_data) if image_data else None

	# Capture the pre-turn page state now (synchronously, before the worker or any
	# streaming touches the canvas — so it's reliably pre-turn). The snapshot DOC is
	# created later, by the loop, only if the turn actually changes the page.
	pre_turn_state = capture_page_state(page_id)

	# Background queue (not now=True): a streaming generation can run 30-60s, and
	# now=True would hold this web worker open for the entire stream — exhausting the
	# worker pool under concurrency. Realtime events flow over Redis pub/sub regardless
	# of which process runs the job.
	frappe.enqueue(
		run_agent_job,
		queue="default",
		timeout=600,
		prompt=prompt,
		page_context_json=page_context,
		model=resolved_model,
		api_key=api_key,
		user=frappe.session.user,
		page_id=page_id,
		session_id=session_id,
		selected_block_ids=selected_block_ids,
		image_url=image_url,
		pre_turn_state=pre_turn_state,
	)
	frappe.local.response.http_status_code = 202
	return {"status": "accepted", "session_id": session_id}


@frappe.whitelist()
@has_page_write()
def cancel(session_id: str):
	"""Request that the currently-running turn for this session abort at its
	next stream chunk. The loop closes the LLM stream — Anthropic / OpenRouter
	stop billing for further tokens once the connection drops."""
	if session_id:
		frappe.cache.set_value(f"builder_ai_cancel:{session_id}", "1", expires_in_sec=300)
	return {"status": "ok"}


@frappe.whitelist()
@has_page_write()
def revert_to_message(session_id: str, message_id: str):
	"""Rewind the conversation to before the given turn: delete that turn's user
	prompt, its assistant reply, and every message after it. The page itself is
	restored separately by the client via the turn's snapshot."""
	session = AISession.get(session_id)
	session.truncate_from_turn(message_id)
	return {"messages": session.get_messages()}


@frappe.whitelist()
@has_page_write()
def get_ai_models():
	return ModelRegistry.AVAILABLE


@frappe.whitelist()
@has_page_write()
def get_ai_session(page_id: str, model: str | None = None):
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
	if not page_id or page_id == "new" or not frappe.db.exists("Builder Page", page_id):
		return {"session_id": "", "messages": []}

	session = AISession.get_or_create(page_id)
	session.clear()
	return {"session_id": session.name, "messages": []}


@frappe.whitelist()
@has_page_write()
def update_session_message_metadata(session_id: str, metadata: dict):
	"""Persist client-side metadata (affectedBlocks, affectedScripts, undoScripts)
	onto the last assistant message so it survives page reloads."""
	if not session_id or not frappe.db.exists(AISession.DOCTYPE, session_id):
		return
	session = AISession(frappe.get_doc(AISession.DOCTYPE, session_id))
	safe_meta = {
		k: metadata[k] for k in ("affectedBlocks", "affectedScripts", "undoScripts") if k in metadata
	}
	session.update_last_assistant_metadata(safe_meta)


@frappe.whitelist()
@has_page_write()
def test_api_key():
	settings = frappe.get_single("Builder Settings")
	model = settings.get("ai_model") or "openrouter"
	api_key = settings.get_password("ai_api_key", raise_exception=False)
	if not api_key:
		return {"success": False, "message": _("Please set an OpenRouter API key")}

	actual_model = ModelRegistry.get_default(model)

	try:
		litellm.completion(
			model=actual_model,
			messages=[{"role": "user", "content": "Say 'OK' if you can read this"}],
			max_tokens=10,
			api_key=api_key,
		)
		return {"success": True, "message": _("API key is valid")}
	except Exception as e:
		logger.error(f"test_api_key failed: {e!s}", exc_info=True)
		return {"success": False, "message": str(e)}
