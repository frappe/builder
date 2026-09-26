# Copyright (c) 2026, Frappe Technologies Pvt Ltd and contributors
# For license information, please see license.txt

import uuid

import frappe
from frappe.model.document import Document


class BuilderExtensionState(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		installation: DF.Link
		state_key: DF.Data
		state_value: DF.JSON | None
		user: DF.Link
	# end: auto-generated types

	def autoname(self):
		# a uuid, and (installation, user, state_key) is looked up by field. A
		# composite name would hold a key the extension chose, in a document name
		if not self.name:
			self.name = str(uuid.uuid4())


TABLE = "tabBuilder Extension State"
UNIQUE_INDEX = "unique_installation_user_state_key"


def on_doctype_update():
	"""One row per user and key. `set_state` upserts by the three, so a second would hide one."""
	frappe.db.add_unique(
		"Builder Extension State", ["installation", "user", "state_key"], constraint_name=UNIQUE_INDEX
	)
