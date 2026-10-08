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
		state: DF.JSON | None
		user: DF.Link
	# end: auto-generated types

	def autoname(self):
		# The code finds a row by installation and user, not by name.
		if not self.name:
			self.name = str(uuid.uuid4())


UNIQUE_INDEX = "unique_installation_user"


def on_doctype_update():
	"""Adds a unique index. Each user and installation can have one row only."""
	frappe.db.add_unique("Builder Extension State", ["installation", "user"], constraint_name=UNIQUE_INDEX)
