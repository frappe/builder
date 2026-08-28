"""Whitelisted endpoints for Builder AI.

A single conversational entry point — `run` — drives the unified agent loop for
everything (generation, editing, scripts, clarification). The remaining
endpoints are flow-agnostic session/model helpers.
"""

import logging
import re

import frappe
import litellm
from frappe import _

from builder.ai.agent.loop import run_agent_job
from builder.ai.block_codec import BlockCodec
from builder.ai.models import ModelRegistry
from builder.ai.session import AISession
from builder.utils import has_page_write

logger = frappe.logger("builder.ai.api")
logger.setLevel(logging.INFO)


def resolve_api_key(model: str | None = None) -> str:
	"""The key to call `model` with: its provider's own key when it has one (a
	local or self-hosted gateway needs no OpenRouter account at all), otherwise
	the OpenRouter key from Builder Settings."""
	if model:
		from builder.ai.llm import provider_api_key

		info = ModelRegistry.find(model)
		if info and (key := provider_api_key(info)):
			return key
	api_key = frappe.get_single("Builder Settings").get_password("ai_api_key", raise_exception=False)
	if not api_key:
		frappe.throw(
			_(
				"Please configure an OpenRouter API key in Settings → AI, or an API key on the model's provider"
			)
		)
	return api_key


def save_attached_image(data_url: str) -> str | None:
	"""Persist a pasted image as a site file. The data URI only lives for the turn
	it was sent on; the file URL is what later turns replay and briefs reference.
	Private: it belongs to the chat (a mock may be confidential), and every reader —
	replay, brief attachment, the chat thumbnail — goes through permissioned paths."""
	try:
		header, content = data_url.split(";base64,", 1)
		ext = header.removeprefix("data:image/").split("+")[0] or "png"
		file = frappe.get_doc(
			{
				"doctype": "File",
				"file_name": f"ai-attachment-{frappe.generate_hash(length=10)}.{ext}",
				"is_private": 1,
				"folder": "Home/Builder Uploads",
				"content": content,
				"decode": True,
			}
		).insert(ignore_permissions=True)
		return file.file_url
	except Exception:
		logger.warning("could not save the attached image as a file", exc_info=True)
		return None


@frappe.whitelist()
@has_page_write()
def run(
	prompt: str,
	page_id: str,
	model: str | None = None,
	session_id: str | None = None,
	selected_block_ids: list | None = None,
	image_data: str | None = None,
	selected_block_context: list | None = None,
	display_text: str | None = None,
):
	"""Single entry point: run the agent for one user turn of the in-editor chat.

	The server edits the page authoritatively from draft_blocks and mirrors the
	accepted ops to the canvas.
	"""
	logger.info(f"run: page_id={page_id}, model={model}, session_id={session_id}")

	image_url = BlockCodec.validate_image_data(image_data) if image_data else None

	# Guard concurrency for an established session first — nothing may persist on the
	# busy path. The worker takes the atomic run lock; this check just gives a fast
	# 429 instead of a queued rejection.
	if session_id and AISession.is_session_running(session_id):
		frappe.local.response.http_status_code = 429
		return {"status": "busy", "message": _("Another AI request is still processing. Please wait.")}

	# A pasted image is a one-turn data URI: saved as a site file it gains a real URL
	# that later turns can replay and a generation brief can carry as REFERENCE IMAGE.
	image_file_url = save_attached_image(image_url) if image_url else None

	# Append the user turn for an established session.
	if session_id:
		session = AISession.get(session_id, page_id=page_id)
		msg_meta: dict = {"selectedBlockContext": selected_block_context or []}
		if image_data:
			msg_meta["attachedImageUrl"] = image_file_url or image_data
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
			_("{0} can't view images. Pick a vision-capable model or remove the image.").format(
				resolved_model
			)
		)
	api_key = resolve_api_key(resolved_model)

	# Background queue (not now=True): a streaming generation can run 30-60s, and
	# now=True would hold this web worker open for the entire stream — exhausting the
	# worker pool under concurrency. Realtime events flow over Redis pub/sub regardless
	# of which process runs the job.
	frappe.enqueue(
		run_agent_job,
		queue="default",
		timeout=600,
		prompt=prompt,
		model=resolved_model,
		api_key=api_key,
		user=frappe.session.user,
		page_id=page_id,
		session_id=session_id,
		enqueue_after_commit=True,
		selected_block_ids=selected_block_ids,
		image_url=image_url,
		image_file_url=image_file_url,
	)
	frappe.local.response.http_status_code = 202
	return {"status": "accepted", "session_id": session_id}


IMPROVE_PROMPT_INSTRUCTION = """You rewrite a user's draft prompt for a website-builder AI into a sharper version of ITSELF.
Preserve every stated fact, constraint, language and the request's SCOPE: a small edit request stays a small edit request, only made clearer; a vague page or section request gains concrete specifics (purpose, audience, section list, tone, style direction).
Write it as the user speaking, plain text, no headings or bullets unless the draft had them, under 120 words. Do not use em dashes. Output ONLY the rewritten prompt."""


@frappe.whitelist()
def improve_prompt(prompt: str, model: str | None = None) -> str:
	"""One cheap completion that sharpens the composer draft in place — the user
	reviews and edits the result before sending it."""
	from builder.ai import llm

	prompt = (prompt or "").strip()
	if not prompt:
		frappe.throw(_("Type a prompt first"))
	resolved_model = ModelRegistry.get_default(model or "openrouter")
	text = llm.complete(
		resolved_model,
		[
			{"role": "system", "content": IMPROVE_PROMPT_INSTRUCTION},
			{"role": "user", "content": prompt},
		],
		llm.TASK_PARAMS["simple"],
		stream=False,
		api_key=resolve_api_key(resolved_model),
	)
	return (text or "").strip()


def ensure_session_owner(session_id: str) -> None:
	owner = frappe.db.get_value(AISession.DOCTYPE, session_id, "session_user")
	if not owner:
		frappe.throw(_("Session not found"))
	if owner != frappe.session.user and "System Manager" not in frappe.get_roles():
		frappe.throw(_("This chat belongs to another user"), frappe.PermissionError)


@frappe.whitelist()
def confirm_pending_settings(message_id: str, decision: str = "apply"):
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
		outcome = "Skipped. Nothing was changed."
		AISession.try_append_message(msg.session, "assistant", outcome, message_type="status")
		resumed = resume_after_action(msg.session, outcome)
		return {"status": "skipped", "resumed": resumed}

	meta = AISession.load_metadata(msg.metadata_json)
	result = apply_pending_action(meta.get("kind"), meta.get("payload") or {})
	frappe.db.set_value(AISession.MESSAGE_DOCTYPE, message_id, "status", "action_applied")
	# The OUTCOME becomes part of the conversation — visible in the chat after a
	# reload, and context for the agent's next turn (it knows what was applied).
	AISession.try_append_message(msg.session, "assistant", result, message_type="status")
	resumed = resume_after_action(msg.session, result)
	return {"status": "applied", "message": result, "resumed": resumed}


def resume_after_action(session_id: str, outcome: str) -> bool:
	"""Carry on with the plan once a confirm-gated action has been decided.

	A confirm card authorises a step, it does not change the plan, so ending the turn
	there left the user typing "continue" to re-trigger the job. Best effort: the
	action is already applied and must not be undone by a queue failure.
	"""
	if AISession.is_session_running(session_id):
		return False
	try:
		page_id, model = frappe.db.get_value(AISession.DOCTYPE, session_id, ["page", "selected_model"])
		if not page_id:
			return False
		resolved_model = ModelRegistry.get_default(model or "openrouter")
		frappe.enqueue(
			run_agent_job,
			queue="default",
			timeout=600,
			# run_agent_job does not persist its prompt, so no phantom "continue" in the chat
			prompt=f"{outcome}\n\nContinue with what you were doing. Do not repeat this step.",
			model=resolved_model,
			api_key=resolve_api_key(resolved_model),
			user=frappe.session.user,
			page_id=page_id,
			session_id=session_id,
			enqueue_after_commit=True,
		)
		return True
	except Exception:
		logger.warning(f"could not resume session {session_id} after a confirmed action", exc_info=True)
		return False


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


PROVIDER_FIELDS = (
	"provider_name",
	"route_prefix",
	"litellm_provider",
	"api_base",
	"enabled",
)


@frappe.whitelist()
def save_ai_provider(provider: dict, name: str | None = None) -> str:
	"""Create or update a provider from the settings UI. An omitted api_key keeps
	the stored one: the client never receives it (keys live in __Auth), so without
	this, editing the API base would wipe the key."""
	if not frappe.has_permission("Builder AI Provider", "write"):
		frappe.throw(_("You are not permitted to manage AI providers"), frappe.PermissionError)

	doc = (
		frappe.get_doc("Builder AI Provider", name)
		if name and frappe.db.exists("Builder AI Provider", name)
		else frappe.new_doc("Builder AI Provider")
	)
	for field in PROVIDER_FIELDS:
		if field in provider:
			doc.set(field, provider[field])
	if provider.get("api_key"):
		doc.api_key = provider["api_key"]
	doc.save()
	return doc.name


# Embeddings and rerankers answer /v1/models too, and fail as chat models.
NON_CHAT_MARKERS = ("embed", "embedding", "rerank", "reranker", "whisper", "tts", "moderation")


@frappe.whitelist()
def import_provider_models(provider: str) -> dict:
	"""Add every chat model an OpenAI-compatible provider advertises at /models.

	Saves typing model ids by hand, and is the only way to discover what a private
	or self-hosted gateway actually serves. Existing rows are left alone, so this
	is safe to re-run when a provider adds a model."""
	if not frappe.has_permission("Builder AI Model", "create"):
		frappe.throw(_("You are not permitted to manage AI models"), frappe.PermissionError)

	doc = frappe.get_doc("Builder AI Provider", provider)
	if not doc.api_base:
		frappe.throw(_("This provider has no API Base to ask"))

	import requests

	url = f"{doc.api_base.rstrip('/')}/models"
	headers = {"Content-Type": "application/json"}
	if key := (doc.resolved_key() or resolve_api_key()):
		headers["Authorization"] = f"Bearer {key}"
	try:
		response = requests.get(url, headers=headers, timeout=20)
		response.raise_for_status()
		listed = response.json().get("data") or []
	except Exception as e:
		logger.warning(f"import_provider_models failed for {provider}: {e}")
		frappe.throw(_("Could not reach {0}: {1}").format(url, str(e)[:200]))

	added, skipped = [], []
	for entry in listed:
		model_id = (entry or {}).get("id")
		if not model_id:
			continue
		if any(marker in model_id.lower() for marker in NON_CHAT_MARKERS):
			skipped.append(model_id)
			continue
		if frappe.db.exists("Builder AI Model", f"{doc.route_prefix}/{model_id}"):
			continue
		frappe.get_doc(
			{"doctype": "Builder AI Model", "provider": provider, "model_id": model_id, "enabled": 1}
		).insert()
		added.append(model_id)

	return {"added": added, "skipped": skipped, "found": len(listed)}


@frappe.whitelist()
@has_page_write()
def get_ai_models():
	return ModelRegistry.available()


@frappe.whitelist()
@has_page_write()
def ai_setup_state():
	"""What the setup flow needs to decide whether to run: the provider catalogue,
	and whether anything usable is already configured. Never returns a key."""
	from builder.ai import presets

	# An install that hasn't migrated has no provider table at all. Say so plainly
	# rather than raising behind a screen that then renders empty.
	if not frappe.db.exists("DocType", "Builder AI Provider"):
		return {"configured": False, "models": 0, "providers": 0, "needs_migrate": True, "presets": []}

	providers = frappe.get_all("Builder AI Provider", filters={"enabled": 1}, fields=["name", "api_key"])
	settings_key = frappe.get_single("Builder Settings").get_password("ai_api_key", raise_exception=False)
	# A provider carrying its own key is enough on its own — a self-hosted gateway
	# never needs the shared OpenRouter one.
	has_key = bool(settings_key) or any(p.api_key for p in providers)
	return {
		"configured": has_key and bool(frappe.db.count("Builder AI Model", {"enabled": 1})),
		"models": frappe.db.count("Builder AI Model", {"enabled": 1}),
		"providers": len(providers),
		"presets": [presets.public_preset(p) for p in presets.PRESETS],
	}


@frappe.whitelist()
@has_page_write()
def verify_ai_key(preset: str, api_key: str = "", api_base: str = "", model_id: str = ""):
	"""Make one small real call so a bad key fails here, not on the first build."""
	from builder.ai import presets

	found = presets.find_preset(preset)
	if not found:
		frappe.throw(_("Unknown provider: {0}").format(preset))
	model = model_id or next((m[0] for m in found["models"] if m[3]), "")
	if not model:
		return {"success": False, "severity": "error", "message": _("Enter a model id to test with")}
	# Re-entering setup for a provider that's already connected shows an empty key
	# box, because a stored key is never sent back. Test the stored one rather than
	# making someone dig out a key the site already has.
	if not api_key and found["name"] and frappe.db.exists("Builder AI Provider", found["name"]):
		api_key = frappe.get_cached_doc("Builder AI Provider", found["name"]).resolved_key() or ""
	return presets.verify_key(found, api_key, api_base, model)


@frappe.whitelist()
@has_page_write()
def start_codex_login():
	"""Begin a ChatGPT browser sign-in: the URL to open, the state to poll on,
	and whether the localhost redirect can be captured from here."""
	from builder.ai import codex_login

	return codex_login.start()


@frappe.whitelist()
@has_page_write()
def poll_codex_login(state: str):
	"""Where a started sign-in stands: pending, connected, failed or expired.
	Connecting installs the ChatGPT provider; models come from setup_ai_provider."""
	from builder.ai import codex_login

	return codex_login.poll(state)


@frappe.whitelist()
@has_page_write()
def finish_codex_login(redirect_url: str):
	"""Complete a sign-in from the pasted redirect URL, for when the localhost
	listener couldn't see it (remote server, port in use)."""
	from builder.ai import codex_login
	from builder.ai.codex import CodexError

	try:
		return codex_login.finish(redirect_url)
	except CodexError as e:
		return {"status": "failed", "message": str(e)}


@frappe.whitelist()
@has_page_write()
def setup_ai_provider(
	preset: str,
	api_key: str = "",
	api_base: str = "",
	models: list | str | None = None,
	provider_name: str = "",
):
	"""Finish setup: save the provider and switch on the chosen models."""
	from builder.ai import presets

	found = presets.find_preset(preset)
	if not found:
		frappe.throw(_("Unknown provider: {0}").format(preset))
	chosen = parse_model_ids(models)
	if not chosen:
		frappe.throw(_("Pick at least one model"))
	name = presets.install_preset(found, api_key, api_base, chosen, provider_name)
	# `installed` is what THIS call switched on, not the site total: when the two
	# disagree with what was ticked, the client can say so instead of reporting
	# success over a selection that never arrived.
	return {
		"provider": name,
		"installed": chosen,
		"models": frappe.db.count("Builder AI Model", {"enabled": 1}),
	}


def parse_model_ids(models) -> list[str]:
	"""Take the selected ids in whatever shape they survived the request in.

	A list does not cross the wire intact: form encoding collapses it to its first
	value, and a JSON body can hand back the raw string. Both used to be iterated
	as-is, so three ticked models became one, and a JSON string became one model
	per CHARACTER ('anthropic/[', 'anthropic/"', …)."""
	if not models:
		return []
	if isinstance(models, str):
		text = models.strip()
		try:
			parsed = frappe.parse_json(text)
		except Exception:
			parsed = None
		if isinstance(parsed, list):
			models = parsed
		elif isinstance(parsed, str):
			models = [parsed]
		else:
			models = re.split(r"[,\n]", text)
	if not isinstance(models, list | tuple):
		models = [models]
	seen, out = set(), []
	for m in models:
		mid = str(m).strip()
		if mid and mid not in seen:
			seen.add(mid)
			out.append(mid)
	return out


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
def new_ai_session(page_id: str, model: str | None = None):
	"""Start a fresh chat session on this page — existing sessions stay untouched
	and switchable (VS Code-style parallel chats). An empty session the user never
	used IS a fresh chat, so hand that back rather than stacking up another: a few
	taps of New chat otherwise fill the switcher with identical blank entries."""
	if not page_id or page_id == "new" or not frappe.db.exists("Builder Page", page_id):
		frappe.throw(_("Save the page before starting a chat session"))
	filters = {"page": page_id, "session_user": frappe.session.user}
	blank = frappe.db.get_value(
		AISession.DOCTYPE, {**filters, "status": "Active", "title": ["is", "not set"]}, "name"
	)
	if blank and not frappe.db.count(AISession.MESSAGE_DOCTYPE, {"session": blank}):
		return {"session_id": blank, "messages": []}
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
	# The session's on_trash takes its messages with it.
	frappe.delete_doc(AISession.DOCTYPE, session_id, ignore_permissions=True)
	return {"status": "ok"}


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
def test_api_key(provider: str | None = None):
	"""Call the cheapest model this key can reach and report what happened. With a
	provider, tests THAT provider's key and one of its models; without, the
	OpenRouter key in Builder Settings."""
	if provider:
		model = frappe.db.get_value("Builder AI Model", {"provider": provider, "enabled": 1}, "name")
		if not model:
			return {"success": False, "message": _("Add a model to this provider first")}
		actual_model = model
		api_key = resolve_api_key(model)
	else:
		api_key = frappe.get_single("Builder Settings").get_password("ai_api_key", raise_exception=False)
		if not api_key:
			return {"success": False, "message": _("Please set an OpenRouter API key")}
		actual_model = ModelRegistry.get_default("openrouter")

	from builder.ai.llm import route

	call_model, overrides, api_key = route(actual_model, api_key)
	try:
		litellm.completion(
			model=call_model,
			**overrides,
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
	"""The in-flight generation stream for this page, so an editor that loads (or
	refreshes) mid-build replays the live preview instead of the stale draft."""
	from builder.ai.agent.artifact import stream_buffer_key

	raw = frappe.cache().get_value(stream_buffer_key(page_id))
	return frappe.parse_json(raw) if raw else None
