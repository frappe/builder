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


def build_mention_hint(mentioned_pages: list | str | None) -> str:
	"""Turn inline @page references into a compact resolution hint appended to the turn,
	so the agent maps each "@Title" to the exact page id + route."""
	if isinstance(mentioned_pages, str):
		try:
			mentioned_pages = json.loads(mentioned_pages)
		except (json.JSONDecodeError, TypeError):
			return ""
	if not isinstance(mentioned_pages, list) or not mentioned_pages:
		return ""
	lines = []
	for p in mentioned_pages:
		if not isinstance(p, dict) or not p.get("name"):
			continue
		route = (p.get("route") or "").lstrip("/")
		lines.append(f"- @{p.get('title') or p['name']}: page id={p['name']}, route=/{route}")
	if not lines:
		return ""
	return "\n\n[Referenced pages — resolve the @mentions above to these exact ids/routes]\n" + "\n".join(
		lines
	)


@frappe.whitelist()
@has_page_write()
def run(
	prompt: str,
	page_context: str = "[]",
	page_id: str | None = None,
	model: str | None = None,
	session_id: str | None = None,
	selected_block_ids: list | None = None,
	image_data: str | None = None,
	selected_block_context: list | None = None,
	mentioned_pages: list | str | None = None,
):
	"""Single entry point: run the agent for one user turn.

	Two modes, one loop: WITH a page_id it's the in-editor chat (client block ops apply
	to the canvas); WITHOUT one it's the page-less dashboard chat, which orchestrates via
	server tools + parallel sub-agents (see run_agent_job / build_orchestrator_registry).

	`mentioned_pages` carries inline @page references from the dashboard chat so the agent
	can resolve "@My Page" to the exact page id/route.
	"""
	logger.info(f"run: page_id={page_id}, model={model}, session_id={session_id}")

	if page_context:
		try:
			json.loads(page_context)
		except (json.JSONDecodeError, TypeError):
			frappe.throw(_("Invalid page context JSON"))

	# Append the user turn + guard concurrency for any established session (page or
	# page-less). AISession.get tolerates page_id=None.
	if session_id:
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

	# Resolve inline @page references into a hint the agent can act on (stored session
	# message keeps the user's original "@Title" text; only the enqueued turn is augmented).
	agent_prompt = prompt + build_mention_hint(mentioned_pages)

	# Capture the pre-turn page state now (synchronously, before the worker or any
	# streaming touches the canvas — so it's reliably pre-turn). The snapshot DOC is
	# created later, by the loop, only if the turn actually changes the page. Page-less
	# dashboard turns have nothing to snapshot.
	pre_turn_state = capture_page_state(page_id) if page_id else None

	# Background queue (not now=True): a streaming generation can run 30-60s, and
	# now=True would hold this web worker open for the entire stream — exhausting the
	# worker pool under concurrency. Realtime events flow over Redis pub/sub regardless
	# of which process runs the job. Page-less turns may fan out sub-agents and block on
	# the join, so they get a longer timeout (children run on a SEPARATE queue).
	frappe.enqueue(
		run_agent_job,
		queue="default",
		timeout=1200 if not page_id else 600,
		prompt=agent_prompt,
		page_context_json=page_context or "[]",
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


def ensure_site_permission():
	if not frappe.has_permission("Builder Page", "create"):
		frappe.throw(_("You do not have permission to build sites"), frappe.PermissionError)


@frappe.whitelist()
@has_page_write()
def get_general_session(model: str | None = None):
	"""The page-less dashboard chat session — one active session per user, reused so the
	conversation continues across turns (a new message must NOT start a new session)."""
	session = AISession.get_or_create_general(model=model)
	return {
		"session_id": session.name,
		"page_id": None,
		"selected_model": session.selected_model,
		"last_task_type": session.last_task_type,
		"messages": session.get_messages(),
	}


@frappe.whitelist()
@has_page_write()
def new_general_session(model: str | None = None):
	"""Start a fresh dashboard chat: retire the current active general session so the next
	get_general_session mints a new one. (History stays queryable; it's just deactivated.)"""
	name = frappe.db.get_value(
		AISession.DOCTYPE,
		{"session_user": frappe.session.user, "session_kind": "general", "status": "Active"},
		"name",
	)
	if name:
		frappe.db.set_value(AISession.DOCTYPE, name, "status", "Inactive", update_modified=False)
	session = AISession.get_or_create_general(model=model)
	return {"session_id": session.name, "messages": []}


@frappe.whitelist()
@has_page_write()
def get_ai_session_messages(session_id: str):
	"""Load a specific dashboard chat session's messages (opening a past session)."""
	if not session_id or not frappe.db.exists(AISession.DOCTYPE, session_id):
		return {"session_id": "", "messages": []}
	session = AISession.get(session_id)  # asserts ownership
	return {
		"session_id": session.name,
		"selected_model": session.selected_model,
		"messages": session.get_messages(),
	}


@frappe.whitelist()
@has_page_write()
def list_ai_sessions(limit: int = 30):
	"""Recent dashboard chat sessions for the current user — powers the sidebar."""
	rows = frappe.get_all(
		AISession.DOCTYPE,
		filters={"session_user": frappe.session.user, "session_kind": "general"},
		fields=["name", "last_task_type", "last_interaction_on", "modified"],
		order_by="last_interaction_on desc",
		limit=min(int(limit), 50),
	)
	# Use the first user message as the human-readable title (cheap sub-query per row).
	for r in rows:
		r["title"] = frappe.db.get_value(
			AISession.MESSAGE_DOCTYPE,
			{"session": r["name"], "role": "user"},
			"content",
			order_by="creation asc",
		)
	return rows


@frappe.whitelist()
@has_page_write()
def get_ai_batch_status(batch_id: str):
	"""Live progress of a parallel sub-agent fan-out: batch status + per-task rows. The
	chat's task-group card polls this alongside the realtime nudges."""
	if not batch_id or not frappe.db.exists("Builder AI Batch", batch_id):
		frappe.throw(_("Batch not found"))
	batch = frappe.get_doc("Builder AI Batch", batch_id)
	return {
		"batch_id": batch.batch_id,
		"status": batch.status,
		"project_folder": batch.project_folder,
		"total_tasks": batch.total_tasks,
		"completed_tasks": batch.completed_tasks,
		"failed_tasks": batch.failed_tasks,
		"tasks": [
			{"row": t.name, "title": t.title, "page": t.page, "status": t.status, "error": t.error}
			for t in batch.tasks
		],
	}


@frappe.whitelist()
def publish_site_batch(batch_id: str):
	"""Publish every page in a generated site (a batch's project folder)."""
	from builder.ai.agent.pending import apply_publish_site

	ensure_site_permission()
	if not batch_id or not frappe.db.exists("Builder AI Batch", batch_id):
		frappe.throw(_("Batch not found"))
	folder = frappe.db.get_value("Builder AI Batch", batch_id, "project_folder")
	if not folder:
		frappe.throw(_("This batch has no site to publish"))
	return {"status": "published", "message": apply_publish_site({"folder": folder})}


@frappe.whitelist()
def confirm_pending_settings(message_id: str, decision: str = "apply", session_id: str | None = None):
	"""Apply (or skip) a sensitive action the agent proposed. The privileged write runs
	HERE, on this user-triggered call — never inside the model's turn. Reads the stored
	payload off the pending-action message and dispatches to apply_pending_action."""
	from builder.ai.agent.pending import apply_pending_action

	if not frappe.has_permission("Builder Settings", "write"):
		frappe.throw(_("You are not permitted to apply this change"), frappe.PermissionError)
	if not message_id or not frappe.db.exists(AISession.MESSAGE_DOCTYPE, message_id):
		frappe.throw(_("Pending action not found"))

	msg = frappe.get_doc(AISession.MESSAGE_DOCTYPE, message_id)
	owner = frappe.db.get_value(AISession.DOCTYPE, msg.session, "session_user")
	if owner != frappe.session.user:
		frappe.throw(_("This action does not belong to you"), frappe.PermissionError)
	if msg.status != "pending_action":
		frappe.throw(_("No pending action on this message"))

	if decision != "apply":
		frappe.db.set_value(AISession.MESSAGE_DOCTYPE, message_id, "status", "action_skipped")
		return {"status": "skipped"}

	meta = AISession.load_metadata(msg.metadata_json)
	result = apply_pending_action(meta.get("kind"), meta.get("payload") or {})
	frappe.db.set_value(AISession.MESSAGE_DOCTYPE, message_id, "status", "action_applied")
	frappe.db.commit()
	return {"status": "applied", "message": result}


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
