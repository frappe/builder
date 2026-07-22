import json

import frappe
from frappe import _

from builder.ai import locks


class AISession:
	DOCTYPE = "Builder AI Session"
	MESSAGE_DOCTYPE = "Builder AI Message"
	CONTEXT_WINDOW = 10  # how many prior turns to feed back to the model

	def __init__(self, doc):
		self._doc = doc

	# --- factories --------------------------------------------------------

	@classmethod
	def find_or_create(cls, filters: dict, model: str | None = None):
		"""Return the most recently used Active session matching `filters` (a page can
		hold several parallel sessions), or insert one with those values. A late model
		pick is saved onto a session created without one."""
		name = frappe.db.get_value(
			cls.DOCTYPE,
			{**filters, "status": "Active"},
			"name",
			order_by="last_interaction_on desc, modified desc",
		)
		if name:
			doc = frappe.get_doc(cls.DOCTYPE, str(name))
			if model and not doc.selected_model:
				doc.selected_model = model
				doc.save(ignore_permissions=True)
			return cls(doc)
		return cls.create({**filters}, model)

	@classmethod
	def create(cls, values: dict, model: str | None = None):
		"""Insert a fresh Active session — the 'new chat' action and the create branch
		of find_or_create share this."""
		doc = frappe.get_doc(
			{
				"doctype": cls.DOCTYPE,
				"session_user": frappe.session.user,
				**values,
				"status": "Active",
				"selected_model": model or "",
				"last_interaction_on": frappe.utils.now_datetime(),
			}
		).insert(ignore_permissions=True)
		return cls(doc)

	@classmethod
	def get_or_create(cls, page_id: str, model: str | None = None, user: str | None = None):
		return cls.find_or_create({"page": page_id, "session_user": user or frappe.session.user}, model)

	@classmethod
	def get_or_create_general(cls, user: str | None = None, model: str | None = None):
		"""The page-less dashboard chat session (session_kind='general'). One active
		general session per user, reused across turns so the conversation continues."""
		return cls.find_or_create(
			{"session_kind": "general", "session_user": user or frappe.session.user}, model
		)

	@classmethod
	def create_subagent_session(cls, user: str | None = None, model: str | None = None):
		"""A fresh, isolated session for one fan-out sub-agent. Always a NEW row (never
		reused) and page-less, so a sub-agent's internal turns never pollute the parent
		chat nor the editor's per-page session — even when it builds a specific page
		(the page_id is passed to the runner directly, not via the session)."""
		doc = frappe.get_doc(
			{
				"doctype": cls.DOCTYPE,
				"session_kind": "general",
				"session_user": user or frappe.session.user,
				"status": "Active",
				"selected_model": model or "",
				"last_interaction_on": frappe.utils.now_datetime(),
			}
		).insert(ignore_permissions=True)
		return cls(doc)

	@classmethod
	def get(cls, session_id: str, page_id: str | None = None, user: str | None = None):
		user = user or frappe.session.user
		if not frappe.db.exists(cls.DOCTYPE, session_id):
			frappe.throw(_("AI session not found"))
		doc = frappe.get_doc(cls.DOCTYPE, session_id)
		if doc.session_user != user:
			frappe.throw(_("You do not have access to this AI session"))
		if page_id and doc.page != page_id:
			frappe.throw(_("AI session does not belong to this page"))
		return cls(doc)

	@classmethod
	def try_append_message(cls, session_id: str | None, role: str, content: str, **kwargs) -> str | None:
		if session_id and frappe.db.exists(cls.DOCTYPE, session_id):
			return cls(frappe.get_doc(cls.DOCTYPE, session_id)).append_message(role, content, **kwargs)
		return None

	@classmethod
	def build_context_messages_from_id(cls, session_id: str | None) -> list[dict]:
		if not session_id or not frappe.db.exists(cls.DOCTYPE, session_id):
			return []
		return cls(frappe.get_doc(cls.DOCTYPE, session_id)).build_context_messages()

	# --- properties -------------------------------------------------------

	@property
	def name(self):
		return self._doc.name

	@property
	def page(self):
		return self._doc.page

	@property
	def selected_model(self):
		return self._doc.selected_model

	@property
	def last_task_type(self):
		return self._doc.last_task_type

	# --- message read -----------------------------------------------------

	@staticmethod
	def load_metadata(metadata_json: str | None) -> dict:
		"""Parse a metadata_json column into a dict, tolerating null/blank/malformed input."""
		try:
			meta = json.loads(metadata_json) if metadata_json else {}
		except (json.JSONDecodeError, TypeError):
			meta = {}
		return meta if isinstance(meta, dict) else {}

	@staticmethod
	def row_to_message(row: dict) -> dict:
		"""Reshape a Builder AI Message DB row into the ChatMessage dict shape
		the frontend renders."""
		metadata = AISession.load_metadata(row.get("metadata_json"))
		# `status` lives in its own column for queryability; surface it in the
		# returned metadata dict so callers see the same shape as before.
		if row.get("status"):
			metadata["status"] = row["status"]
		return {
			"id": row.get("name"),
			"role": row.get("role"),
			"content": row.get("content") or "",
			"message_type": row.get("message_type"),
			"task_type": row.get("task_type") or None,
			"block_id": row.get("block_id") or None,
			"created_at": str(row.get("creation")) if row.get("creation") else None,
			"metadata": metadata,
		}

	_FIELDS = (
		"name",
		"role",
		"content",
		"message_type",
		"task_type",
		"block_id",
		"status",
		"metadata_json",
		"creation",
	)

	@classmethod
	def collect_design_svgs(cls, session_id: str | None) -> list[str]:
		"""The design-flow wireframes the user actually approved, for the generation
		stream: the SVG sketch of the layout option the user tapped (plus the plan
		card's page-strip SVG on older sessions — new plan cards carry a `mock` atom
		instead, whose sections/colors replay as text). Cards replay into the
		transcript as plain text where svg renders as just '[sketch]', so generation
		would never see the approved composition without this targeted extraction
		from message metadata."""
		if not session_id:
			return []
		rows = frappe.db.get_all(
			cls.MESSAGE_DOCTYPE,
			filters={"session": session_id},
			# status is hoisted to its own column by append_message — it is NOT
			# inside metadata_json.
			fields=["role", "content", "status", "metadata_json"],
			order_by="creation asc",
			limit_page_length=0,
		)
		plan_svg = None
		chosen_svg = None
		for i, row in enumerate(rows):
			if row.get("role") != "assistant" or row.get("status") != "ui":
				continue
			meta = cls.load_metadata(row.get("metadata_json"))
			ui = meta.get("ui") or []
			kinds = {el.get("kind") for el in ui if isinstance(el, dict)}
			# The plan card is the one carrying both a wireframe and the note brief.
			if "svg" in kinds and "note" in kinds:
				svg = next((el.get("svg") for el in ui if el.get("kind") == "svg" and el.get("svg")), None)
				plan_svg = svg or plan_svg
				continue
			# A layout card: match the option the user's NEXT message names.
			reply = next((r.get("content") or "" for r in rows[i + 1 :] if r.get("role") == "user"), "")
			for el in ui:
				if el.get("kind") != "choices":
					continue
				for option in el.get("options") or []:
					label = (option.get("label") or "").strip()
					if label and option.get("svg") and label in reply:
						chosen_svg = option["svg"]
		out = [s for s in (plan_svg, chosen_svg) if s]
		return [s[:4000] for s in out[:2]]

	def get_messages(self) -> list[dict]:
		"""Return ALL messages for this session in chronological order, shaped
		for the frontend's ChatMessage interface."""
		rows = frappe.db.get_all(
			self.MESSAGE_DOCTYPE,
			filters={"session": self._doc.name},
			fields=list(self._FIELDS),
			order_by="creation asc",
			limit_page_length=0,
		)
		return [self.row_to_message(r) for r in rows]

	def build_context_messages(self) -> list[dict]:
		"""Return the last N prior turns as proper role-tagged messages.

		Excludes the current-turn user message (the agent loop appends a fresh
		one) and transient chatter (running/error/cancelled turns). Durable
		status notes — e.g. the outcome of a confirmed action — stay in, so the
		model knows on later turns what was actually applied."""
		# Fetch one extra (the current user message) and drop it.
		rows = frappe.db.get_all(
			self.MESSAGE_DOCTYPE,
			filters={"session": self._doc.name},
			fields=["role", "content", "message_type", "status", "metadata_json"],
			order_by="creation desc",
			limit_page_length=self.CONTEXT_WINDOW + 1,
		)
		# Skip the most recent row (current user msg) and reverse to chrono order.
		history = list(reversed(rows[1:])) if rows else []
		out: list[dict] = []
		for r in history:
			content = (r.get("content") or "").strip()
			role = r.get("role")
			if not content or role not in ("user", "assistant"):
				continue
			if r.get("status") in ("running", "error", "cancelled"):
				continue
			# A proposed plan is persisted as just its headline (its sections and
			# palette live in metadata, which the chat UI renders separately). Without
			# them here, the model sees only a one-line headline — it can't tell it
			# already proposed a full plan, so on approval it re-proposes instead of
			# building. Restore the full plan so both the model and the downstream
			# generator see what was proposed and approved.
			if role == "assistant" and r.get("status") == "plan_summary":
				content = self.plan_context_content(content, r.get("metadata_json"))
			out.append({"role": role, "content": content})
		return out

	@staticmethod
	def plan_context_content(headline: str, metadata_json: str | None) -> str:
		"""Reconstruct a proposed plan's full text (headline + sections + palette)
		from its stored metadata, for replay into the model's context."""
		meta = AISession.load_metadata(metadata_json)
		sections = [str(s).strip() for s in (meta.get("sections") or []) if str(s).strip()]
		palette = (meta.get("palette") or "").strip()
		lines = [headline]
		if sections:
			lines.append("Sections:")
			lines.extend(f"- {s}" for s in sections)
		if palette:
			lines.append(f"Palette: {palette}")
		return "\n".join(lines)

	# --- message write ----------------------------------------------------

	def append_message(
		self,
		role: str,
		content: str,
		*,
		message_type: str = "chat",
		task_type: str | None = None,
		block_id: str | None = None,
		metadata: dict | None = None,
	):
		metadata = metadata or {}
		# Hoist status to its own column for cheap filtered queries; keep
		# everything else in metadata_json.
		status = ""
		meta_clean: dict = {}
		if isinstance(metadata, dict):
			status = (metadata.get("status") or "").strip()
			meta_clean = {k: v for k, v in metadata.items() if k != "status"}

		msg = frappe.get_doc(
			{
				"doctype": self.MESSAGE_DOCTYPE,
				"session": self._doc.name,
				"role": role,
				"content": content,
				"message_type": message_type,
				"status": status,
				"task_type": task_type or "",
				"block_id": block_id or "",
				"metadata_json": json.dumps(meta_clean, separators=(",", ":")) if meta_clean else "",
			}
		).insert(ignore_permissions=True)

		# Touch the parent's bookkeeping fields atomically (no full re-save).
		updates: dict = {"last_interaction_on": frappe.utils.now_datetime()}
		if task_type:
			updates["last_task_type"] = task_type
		frappe.db.set_value(self.DOCTYPE, self._doc.name, updates, update_modified=False)
		return msg.name

	def update_last_assistant_metadata(self, extra_metadata: dict):
		"""Merge extra_metadata into the most recent assistant message's
		metadata_json. One-row UPDATE — no read-modify-write of a giant blob."""
		row = frappe.db.get_value(
			self.MESSAGE_DOCTYPE,
			{"session": self._doc.name, "role": "assistant"},
			["name", "metadata_json"],
			order_by="creation desc",
			as_dict=True,
		)
		if not row:
			return
		meta = self.load_metadata(row.metadata_json)
		meta.update(extra_metadata or {})
		frappe.db.set_value(
			self.MESSAGE_DOCTYPE,
			row.name,
			"metadata_json",
			json.dumps(meta, separators=(",", ":")),
			update_modified=False,
		)

	# --- run lock (one turn per session at a time) -------------------------
	# Redis NX+TTL via builder.ai.locks: atomic (the old is_running DB flag was a
	# check-then-set race) and self-healing — a crashed worker's lock expires
	# instead of bricking the session until someone edits the row.

	@staticmethod
	def start_run(session_id: str) -> str | None:
		"""Try to claim this session's turn slot. Returns the release token, or None
		when another turn is still running."""
		return locks.acquire(locks.session_key(session_id), locks.SESSION_LOCK_TTL)

	@staticmethod
	def end_run(session_id: str, token: str | None) -> None:
		locks.release(locks.session_key(session_id), token)

	@classmethod
	def is_session_running(cls, session_id: str) -> bool:
		return bool(session_id) and locks.held(locks.session_key(session_id))

	# --- lifecycle --------------------------------------------------------

	def truncate_from_turn(self, message_id: str):
		"""Delete the turn that produced `message_id` and everything after it: the
		assistant message, its triggering user prompt, and all later messages. Used by
		the chat "revert" action to rewind the conversation alongside the page."""
		target = frappe.db.get_value(
			self.MESSAGE_DOCTYPE, {"name": message_id, "session": self._doc.name}, "creation"
		)
		if not target:
			return
		# The prompt that started this turn is the most recent user message at/before
		# the assistant reply; deleting from there removes the whole exchange.
		user_creation = frappe.db.get_value(
			self.MESSAGE_DOCTYPE,
			{"session": self._doc.name, "role": "user", "creation": ["<=", target]},
			"creation",
			order_by="creation desc",
		)
		cutoff = user_creation or target
		frappe.db.delete(self.MESSAGE_DOCTYPE, {"session": self._doc.name, "creation": [">=", cutoff]})
		frappe.db.commit()

	def clear(self):
		"""Wipe all messages for this session and reset transient state."""
		frappe.db.delete(self.MESSAGE_DOCTYPE, {"session": self._doc.name})
		frappe.db.set_value(
			self.DOCTYPE,
			self._doc.name,
			{
				"last_task_type": None,
				"last_interaction_on": frappe.utils.now_datetime(),
			},
			update_modified=False,
		)
		frappe.db.commit()
