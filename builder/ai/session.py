import json

import frappe
from frappe import _


class AISession:
	DOCTYPE = "Builder AI Session"
	MAX_MESSAGES = 100

	def __init__(self, doc):
		self._doc = doc

	@classmethod
	def get_or_create(cls, page_id: str, model: str | None = None, user: str | None = None):
		user = user or frappe.session.user

		session_name = frappe.db.get_value(
			cls.DOCTYPE,
			{"page": page_id, "session_user": user, "status": "Active"},
			"name",
		)
		if session_name:
			doc = frappe.get_doc(cls.DOCTYPE, str(session_name))
			if model and not doc.selected_model:
				doc.selected_model = model
				doc.save(ignore_permissions=True)
			return cls(doc)

		doc = frappe.get_doc(
			{
				"doctype": cls.DOCTYPE,
				"page": page_id,
				"session_user": user,
				"status": "Active",
				"selected_model": model or "",
				"messages_json": "[]",
				"last_interaction_on": frappe.utils.now_datetime(),
			}
		)
		doc.insert(ignore_permissions=True)
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
	def try_append_message(cls, session_id: str | None, role: str, content: str, **kwargs):
		if session_id and frappe.db.exists(cls.DOCTYPE, session_id):
			cls(frappe.get_doc(cls.DOCTYPE, session_id)).append_message(role, content, **kwargs)

	@classmethod
	def build_context_from_id(cls, session_id: str | None) -> str:
		if not session_id or not frappe.db.exists(cls.DOCTYPE, session_id):
			return ""
		return cls(frappe.get_doc(cls.DOCTYPE, session_id)).build_context_string()

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

	def get_messages(self) -> list[dict]:
		try:
			messages = json.loads(self._doc.messages_json or "[]")
		except json.JSONDecodeError:
			return []
		return messages if isinstance(messages, list) else []

	def save_messages(self, messages: list[dict], task_type: str | None = None):
		trimmed = messages[-self.MAX_MESSAGES :]
		self._doc.messages_json = json.dumps(trimmed, separators=(",", ":"))
		self._doc.last_interaction_on = frappe.utils.now_datetime()
		self._doc.last_task_type = task_type or self._doc.last_task_type
		self._doc.save(ignore_permissions=True)

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
		messages = self.get_messages()
		messages.append(
			{
				"id": frappe.generate_hash(length=10),
				"role": role,
				"content": content,
				"message_type": message_type,
				"task_type": task_type,
				"block_id": block_id,
				"created_at": str(frappe.utils.now_datetime()),
				"metadata": metadata or {},
			}
		)
		self.save_messages(messages, task_type=task_type)

	def update_last_assistant_metadata(self, extra_metadata: dict):
		"""Merge extra_metadata into the most recent assistant message and persist."""
		messages = self.get_messages()
		for msg in reversed(messages):
			if msg.get("role") == "assistant":
				msg.setdefault("metadata", {}).update(extra_metadata)
				break
		self.save_messages(messages)

	def set_running(self):
		"""Mark session as having an active AI job running."""
		frappe.db.set_value(self.DOCTYPE, self._doc.name, "is_running", 1, update_modified=False)
		frappe.db.commit()

	def clear_running(self):
		"""Clear the running flag when the job finishes."""
		frappe.db.set_value(self.DOCTYPE, self._doc.name, "is_running", 0, update_modified=False)
		frappe.db.commit()

	@classmethod
	def is_session_running(cls, session_id: str) -> bool:
		"""Return True if there is already a job running for this session."""
		if not session_id or not frappe.db.exists(cls.DOCTYPE, session_id):
			return False
		return bool(frappe.db.get_value(cls.DOCTYPE, session_id, "is_running"))

	@classmethod
	def has_clarification_messages(cls, session_id: str | None) -> bool:
		"""Return True if the session already has clarification messages (we're mid Q&A)."""
		if not session_id or not frappe.db.exists(cls.DOCTYPE, session_id):
			return False
		messages = cls(frappe.get_doc(cls.DOCTYPE, session_id)).get_messages()
		return any(m.get("message_type") == "clarification" for m in messages)

	@classmethod
	def last_assistant_was_plan(cls, session_id: str | None) -> bool:
		"""True if the most recent assistant message proposed a plan — i.e. the
		current user turn is likely approving it, so generation is imminent."""
		if not session_id or not frappe.db.exists(cls.DOCTYPE, session_id):
			return False
		messages = cls(frappe.get_doc(cls.DOCTYPE, session_id)).get_messages()
		for m in reversed(messages):
			if m.get("role") == "assistant":
				return (m.get("metadata") or {}).get("status") == "plan_summary"
		return False

	def build_context_string(self) -> str:
		history_lines = []
		for message in self.get_messages()[-10:]:
			role = message.get("role") or "user"
			content = (message.get("content") or "").strip()
			if not content:
				continue
			prefix = "User" if role == "user" else "Assistant"
			history_lines.append(f"{prefix}: {content}")

		if not history_lines:
			return ""
		return "Conversation history for this page:\n" + "\n".join(history_lines)

	def clear(self):
		self._doc.messages_json = "[]"
		self._doc.last_task_type = None
		self._doc.last_interaction_on = frappe.utils.now_datetime()
		self._doc.save(ignore_permissions=True)
