# Copyright (c) 2026, Frappe Technologies Pvt Ltd and contributors
# For license information, please see license.txt

from __future__ import annotations

import json

from frappe.model.document import Document


class BuilderAISession(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		last_interaction_on: DF.Datetime | None
		last_task_type: DF.Data | None
		messages_json: DF.LongText | None
		page: DF.Link
		selected_model: DF.Data | None
		session_user: DF.Link
		status: DF.Literal["Active", "Archived"]
	# end: auto-generated types

	def validate(self):
		if not self.messages_json:
			self.messages_json = "[]"
			return

		try:
			messages = json.loads(self.messages_json)
		except json.JSONDecodeError:
			self.messages_json = "[]"
			return

		if not isinstance(messages, list):
			self.messages_json = "[]"