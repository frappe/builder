# Copyright (c) 2026, Frappe Technologies Pvt Ltd and contributors
# For license information, please see license.txt

from __future__ import annotations

import frappe
from frappe import _
from frappe.model.document import Document


class BuilderAISession(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		last_interaction_on: DF.Datetime | None
		last_task_type: DF.Data | None
		page: DF.Link
		selected_model: DF.Data | None
		session_user: DF.Link
		status: DF.Literal["Active", "Archived"]
	# end: auto-generated types

	def on_trash(self):
		"""A session owns its messages. They live in their own doctype with a Link
		back here, so unless they go first the link guard refuses the delete — and
		since a page deletes its sessions, that made a chat the user had once opened
		enough to block deleting the page itself. on_trash runs before the link
		check, so clearing them here is what lets both deletes through."""
		from builder.ai.runs import AIRun

		if AIRun.active(self.name):
			frappe.throw(_("Stop the active Bob turn before deleting this chat or its page."))
		if frappe.db.exists("Builder AI Message", {"session": self.name, "status": "action_applying"}):
			frappe.throw(_("Resolve the applying Bob action before deleting this chat or its page."))
		for run in frappe.get_all("Builder AI Run", filters={"session": self.name}, pluck="name"):
			frappe.db.delete("Builder AI Event", {"run": run})
			frappe.db.delete("Builder AI Artifact", {"run": run})
		frappe.db.delete("Builder AI Message", {"session": self.name})
		frappe.db.delete("Builder AI Run", {"session": self.name})
