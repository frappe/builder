import json

import frappe
from frappe import _


class AISession:
	DOCTYPE = "Builder AI Session"
	MAX_MESSAGES = 24

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
