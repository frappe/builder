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
	# end: auto-generated types

	def autoname(self):
		# a uuid, and (installation, state_key) is looked up by field. A composite
		# name would hold a key the extension chose, in a document name
		if not self.name:
			self.name = str(uuid.uuid4())


TABLE = "tabBuilder Extension State"
UNIQUE_INDEX = "unique_installation_state_key"


def on_doctype_update():
	"""One row per key. `set_state` upserts by the pair, so a second would hide one."""
	frappe.db.add_unique(
		"Builder Extension State", ["installation", "state_key"], constraint_name=UNIQUE_INDEX
	)
