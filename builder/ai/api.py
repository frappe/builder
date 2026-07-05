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
from frappe.utils.caching import redis_cache

from builder.ai.agent.loop import run_agent_job
from builder.ai.block_codec import BlockCodec
from builder.ai.models import ModelRegistry
from builder.ai.session import AISession
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
		# Key on the exact token in the text — titles can collide across pages, so the
		# token (disambiguated with the route when needed) is what maps to a single id.
		label = p.get("token") or f"@{p.get('title') or p['name']}"
		lines.append(f"- {label} → page id={p['name']}, route=/{route}")
	if not lines:
		return ""
	return "\n\n[Referenced pages — resolve the @mentions above to these exact ids/routes]\n" + "\n".join(
		lines
	)


@frappe.whitelist()
@has_page_write()
def run(
	prompt: str,
	page_id: str | None = None,
	model: str | None = None,
	session_id: str | None = None,
	selected_block_ids: list | None = None,
	image_data: str | None = None,
	selected_block_context: list | None = None,
	mentioned_pages: list | str | None = None,
	display_text: str | None = None,
):
	"""Single entry point: run the agent for one user turn.

	Two modes, one loop: WITH a page_id it's the in-editor chat (the server edits the
	page authoritatively from draft_blocks and mirrors accepted ops to the canvas);
	WITHOUT one it's the page-less dashboard chat, which orchestrates via server tools
	+ parallel sub-agents (see run_agent_job / build_orchestrator_registry).

	`mentioned_pages` carries inline @page references from the dashboard chat so the agent
	can resolve "@My Page" to the exact page id/route.
	"""
	logger.info(f"run: page_id={page_id}, model={model}, session_id={session_id}")

	# Append the user turn + guard concurrency for any established session (page or
	# page-less). AISession.get tolerates page_id=None. The worker takes the atomic
	# run lock; this check just gives a fast 429 instead of a queued rejection.
	if session_id:
		if AISession.is_session_running(session_id):
			frappe.local.response.http_status_code = 429
			return {"status": "busy", "message": _("Another AI request is still processing. Please wait.")}

		session = AISession.get(session_id, page_id=page_id)
		msg_meta: dict = {"selectedBlockContext": selected_block_context or []}
		if image_data:
			msg_meta["attachedImageUrl"] = image_data
		# A card-composed reply (option tap, form submit) shows as this compact line
		# in the chat; the full labelled text stays the message content for the model.
		if display_text:
			msg_meta["displayText"] = display_text.strip()[:300]
		session.append_message("user", prompt, message_type="chat", task_type="agent", metadata=msg_meta)

	resolved_model = ModelRegistry.get_default(model or "openrouter")
	if not ModelRegistry.is_known_model(resolved_model):
		frappe.throw(_("Unknown AI model: {0}").format(resolved_model))
	if image_data and not ModelRegistry.supports_vision(resolved_model):
		frappe.throw(
			_("{0} can't view images — pick a vision-capable model or remove the image").format(
				resolved_model
			)
		)
	api_key = resolve_api_key()
	image_url = BlockCodec.validate_image_data(image_data) if image_data else None

	# Resolve inline @page references into a hint the agent can act on (stored session
	# message keeps the user's original "@Title" text; only the enqueued turn is augmented).
	agent_prompt = prompt + build_mention_hint(mentioned_pages)

	# Background queue (not now=True): a streaming generation can run 30-60s, and
	# now=True would hold this web worker open for the entire stream — exhausting the
	# worker pool under concurrency. Realtime events flow over Redis pub/sub regardless
	# of which process runs the job. A fan-out ends the turn (spawn is terminal), so no
	# turn needs a long-join timeout anymore.
	frappe.enqueue(
		run_agent_job,
		queue="default",
		timeout=600,
		prompt=agent_prompt,
		model=resolved_model,
		api_key=api_key,
		user=frappe.session.user,
		page_id=page_id,
		session_id=session_id,
		selected_block_ids=selected_block_ids,
		image_url=image_url,
	)
	frappe.local.response.http_status_code = 202
	return {"status": "accepted", "session_id": session_id}


def ensure_site_permission():
	if not frappe.has_permission("Builder Page", "create"):
		frappe.throw(_("You do not have permission to build sites"), frappe.PermissionError)


def ensure_session_owner(session_id: str) -> None:
	owner = frappe.db.get_value(AISession.DOCTYPE, session_id, "session_user")
	if not owner:
		frappe.throw(_("Session not found"))
	if owner != frappe.session.user and "System Manager" not in frappe.get_roles():
		frappe.throw(_("This chat belongs to another user"), frappe.PermissionError)


@frappe.whitelist()
@has_page_write()
def revert_ai_turn(session_id: str, message_id: str):
	"""Server-side revert (no canvas to restore through): put every
	page the turn touched back to its pre-edit snapshot, then rewind the conversation
	— this turn and everything after it."""
	ensure_session_owner(session_id)
	meta = AISession.load_metadata(
		frappe.db.get_value(
			AISession.MESSAGE_DOCTYPE, {"name": message_id, "session": session_id}, "metadata_json"
		)
	)
	# A multi-page turn carries one snapshot per page in revertSnapshots; a
	# single-page turn just revertSnapshot.
	snapshots = list((meta.get("revertSnapshots") or {}).values()) or [meta.get("revertSnapshot")]
	snapshots = [s for s in snapshots if s and frappe.db.exists("Builder Snapshot", s)]
	if not snapshots:
		frappe.throw(_("This turn has no revert snapshot"))
	for snapshot in snapshots:
		page = frappe.db.get_value("Builder Snapshot", snapshot, "reference_name")
		frappe.get_doc("Builder Page", page).restore_snapshot(snapshot)
	session = AISession.get(session_id)
	session.truncate_from_turn(message_id)
	return {"messages": session.get_messages()}


def get_owned_batch(batch_id: str):
	"""Load a Builder AI Batch, asserting the caller owns it (or is a System Manager)."""
	if not batch_id or not frappe.db.exists("Builder AI Batch", batch_id):
		frappe.throw(_("Batch not found"))
	batch = frappe.get_doc("Builder AI Batch", batch_id)
	if batch.created_by_user != frappe.session.user and "System Manager" not in frappe.get_roles():
		frappe.throw(_("This batch belongs to another user"), frappe.PermissionError)
	return batch


@frappe.whitelist()
@has_page_write()
def get_ai_batch_status(batch_id: str):
	"""Live progress of a parallel sub-agent fan-out: batch status + per-task rows. The
	chat's task-group card polls this alongside the realtime nudges."""
	batch = get_owned_batch(batch_id)
	return {
		"batch_id": batch.batch_id,
		"status": batch.status,
		"project_folder": batch.project_folder,
		"total_tasks": batch.total_tasks,
		"completed_tasks": batch.completed_tasks,
		"failed_tasks": batch.failed_tasks,
		"tasks": [
			{
				"row": t.name,
				"title": t.title,
				"page": t.page,
				"status": t.status,
				"error": t.error,
				# Sub-agents screenshot their page via preview_page — thumbnail for the card.
				"preview": frappe.db.get_value("Builder Page", t.page, "preview") if t.page else None,
			}
			for t in batch.tasks
		],
	}


@frappe.whitelist()
@has_page_write()
def cancel_ai_batch(batch_id: str):
	"""Stop a running fan-out: queued tasks abort at entry, running sub-agents abort at
	their next stream chunk. The last one to settle finalizes the batch as cancelled
	(without waking the agent to discuss it)."""
	from builder.ai.orchestration import cancel_batch

	batch = get_owned_batch(batch_id)
	cancel_batch(batch.name)
	return {"status": "cancelling"}


@frappe.whitelist()
def publish_site_batch(batch_id: str):
	"""Publish every page in a generated site (a batch's project folder)."""
	from builder.ai.agent.pending import apply_publish_site

	ensure_site_permission()
	batch = get_owned_batch(batch_id)
	if not batch.project_folder:
		frappe.throw(_("This batch has no site to publish"))
	return {"status": "published", "message": apply_publish_site({"folder": batch.project_folder})}


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
		AISession.try_append_message(
			msg.session, "assistant", "Skipped — nothing was changed.", message_type="status"
		)
		frappe.db.commit()
		resumed = resume_agent_after_decision(msg.session, "skip", "")
		return {"status": "skipped", "resumed": resumed}

	meta = AISession.load_metadata(msg.metadata_json)
	result = apply_pending_action(meta.get("kind"), meta.get("payload") or {})
	frappe.db.set_value(AISession.MESSAGE_DOCTYPE, message_id, "status", "action_applied")
	# The OUTCOME becomes part of the conversation — visible in the chat after a
	# reload, and context for the agent's next turn (it knows what was applied).
	AISession.try_append_message(msg.session, "assistant", result, message_type="status")
	frappe.db.commit()
	resumed = resume_agent_after_decision(msg.session, "apply", result)
	return {"status": "applied", "message": result, "resumed": resumed}


def resume_agent_after_decision(session_id: str, decision: str, result: str) -> bool:
	"""A confirm-gated step ENDS the agent's turn — so once the user decides, the
	bigger task must continue without another prod ("create a merch store" should
	not stall after each approved doctype/seed step). Dashboard (general) sessions
	only: editor turns are canvas-bound. The continuation instruction rides only
	this enqueued turn — it is never persisted, so no fake user bubble appears; the
	durable outcome message above is what future context sees."""
	row = frappe.db.get_value(AISession.DOCTYPE, session_id, ["session_kind", "selected_model"], as_dict=True)
	if not row or row.session_kind != "general" or AISession.is_session_running(session_id):
		return False
	if decision == "apply":
		prompt = (
			f"[The user APPROVED the pending action and it was applied: {result}] "
			"Continue the task from where you left off — do NOT redo or re-propose that step. "
			"If nothing remains, wrap up with a 1-2 sentence summary."
		)
	else:
		prompt = (
			"[The user SKIPPED the pending action — it was NOT applied.] "
			"Continue the task without that step, adapting where needed; if it can't proceed "
			"without it, say so briefly."
		)
	frappe.enqueue(
		run_agent_job,
		queue="default",
		timeout=600,
		prompt=prompt,
		model=ModelRegistry.get_default(row.selected_model or "openrouter"),
		api_key=resolve_api_key(),
		user=frappe.session.user,
		page_id=None,
		session_id=session_id,
	)
	return True


@frappe.whitelist()
@has_page_write()
def cancel(session_id: str):
	"""Request that the currently-running turn for this session abort at its
	next stream chunk. The loop closes the LLM stream — Anthropic / OpenRouter
	stop billing for further tokens once the connection drops."""
	from builder.ai import locks
	from builder.ai.agent.loop import EVENT_PREFIX

	if not session_id:
		return {"status": "ok"}
	ensure_session_owner(session_id)
	frappe.cache.set_value(f"builder_ai_cancel:{session_id}", "1", expires_in_sec=300)
	# Only a live loop acknowledges the flag. If no turn holds the session lock
	# (the run crashed, timed out, or never started), tell the panel directly —
	# otherwise "Cancelling…" spins forever.
	if not locks.held(locks.session_key(session_id)):
		channel = frappe.db.get_value("Builder AI Session", session_id, "page") or session_id
		frappe.publish_realtime(
			f"{EVENT_PREFIX}_error_{channel}",
			{"session_id": session_id, "message": "That run is no longer active."},
			user=frappe.session.user,
		)
		return {"status": "not_running"}
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
	return ModelRegistry.available()


@frappe.whitelist()
@has_page_write()
def get_ai_session(page_id: str, model: str | None = None, session_id: str | None = None):
	"""One page can hold several parallel chat sessions. With `session_id` this loads
	that specific session; without it, the page's most recently used one (creating
	the first if none exist)."""
	if not page_id or page_id == "new" or not frappe.db.exists("Builder Page", page_id):
		return {
			"session_id": "",
			"page_id": page_id,
			"selected_model": model or "",
			"last_task_type": None,
			"messages": [],
		}

	if session_id and frappe.db.exists(AISession.DOCTYPE, session_id):
		session = AISession.get(session_id, page_id=page_id)
	else:
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
def get_ai_cost_currency():
	"""The currency AI costs display in — the site's currency (System Settings, or
	its country's) — with the cached daily USD rate. Falls back to USD whenever the
	currency or rate is unknowable, so cost display never breaks on FX problems."""
	currency = site_display_currency()
	if currency == "USD":
		return {"currency": "USD", "rate": 1}
	rate = usd_rate(currency)
	return {"currency": currency, "rate": rate} if rate else {"currency": "USD", "rate": 1}


def site_display_currency() -> str:
	settings = frappe.get_cached_doc("System Settings")
	if settings.get("currency"):
		return settings.get("currency")
	if settings.get("country"):
		from frappe.geo.country_info import get_country_info

		return (get_country_info(settings.get("country")) or {}).get("currency") or "USD"
	return "USD"


@redis_cache(ttl=24 * 3600)
def usd_rate(currency: str) -> float | None:
	"""USD → currency, from the ECB daily fixing (frankfurter.app, keyless)."""
	import requests

	try:
		r = requests.get(
			"https://api.frankfurter.app/latest", params={"from": "USD", "to": currency}, timeout=8
		)
		r.raise_for_status()
		return float(r.json()["rates"][currency])
	except Exception:
		return None


@frappe.whitelist()
@has_page_write()
def new_ai_session(page_id: str, model: str | None = None):
	"""Start a fresh chat session on this page — existing sessions stay untouched
	and switchable (VS Code-style parallel chats)."""
	if not page_id or page_id == "new" or not frappe.db.exists("Builder Page", page_id):
		frappe.throw(_("Save the page before starting a chat session"))
	session = AISession.create({"page": page_id}, model)
	return {"session_id": session.name, "messages": []}


@frappe.whitelist()
@has_page_write()
def list_page_ai_sessions(page_id: str, limit: int = 20):
	"""This page's chat sessions for the current user — powers the session switcher."""
	if not page_id or page_id == "new":
		return []
	rows = frappe.get_all(
		AISession.DOCTYPE,
		filters={"page": page_id, "session_user": frappe.session.user, "status": "Active"},
		fields=["name", "title", "last_interaction_on"],
		order_by="last_interaction_on desc",
		limit=min(int(limit), 50),
	)
	# A user-set title wins; otherwise the first user message names the session.
	for r in rows:
		r["title"] = r["title"] or frappe.db.get_value(
			AISession.MESSAGE_DOCTYPE,
			{"session": r["name"], "role": "user"},
			"content",
			order_by="creation asc",
		)
	return rows


@frappe.whitelist()
@has_page_write()
def delete_ai_session(session_id: str):
	ensure_session_owner(session_id)
	AISession.get(session_id).clear()  # messages first (separate doctype)
	frappe.delete_doc(AISession.DOCTYPE, session_id, ignore_permissions=True)
	return {"status": "ok"}


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
	session = AISession.get(session_id)  # asserts ownership
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


@frappe.whitelist()
@has_page_write()
def get_active_build(page_id: str):
	"""The in-flight generation stream for a page, if one is running — lets an editor
	that loads mid-build replay the live preview instead of showing the stale draft."""
	from builder.ai.agent.artifact import stream_buffer_key

	raw = frappe.cache().get_value(stream_buffer_key(page_id))
	return frappe.parse_json(raw) if raw else None


CASSETTE_MODES = ("record", "replay")


@frappe.whitelist()
@has_page_write()
def cassette_status():
	"""Cassette state for the dev UI. Only exposed on developer-mode benches —
	record/replay is a testing tool, not a product feature."""
	from builder.ai import cassette

	if not (frappe.conf.developer_mode or frappe.conf.ai_cassette_enabled):
		return {"enabled": False}
	import os

	directory = os.path.dirname(cassette.episode_path("probe"))
	episodes = sorted(f[: -len(".jsonl")] for f in os.listdir(directory) if f.endswith(".jsonl"))
	return {"enabled": True, "active": cassette.config(), "episodes": episodes}


@frappe.whitelist()
@has_page_write()
def cassette_arm(mode: str, episode: str):
	from builder.ai import cassette

	if not (frappe.conf.developer_mode or frappe.conf.ai_cassette_enabled):
		frappe.throw(_("Cassettes are only available in developer mode"))
	if mode not in CASSETTE_MODES or not (episode or "").strip():
		frappe.throw(_("Pick record/replay and an episode name"))
	cassette.arm(mode, episode.strip())
	return cassette_status()


@frappe.whitelist()
@has_page_write()
def cassette_disarm():
	from builder.ai import cassette

	cassette.disarm()
	return cassette_status()
