# Copyright (c) 2026, Frappe Technologies Pvt Ltd and contributors
# For license information, please see license.txt

import uuid

import frappe
from frappe.model.document import Document


class BuilderExtensionDocTypeGrant(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		delete: DF.Literal["not asked", "allowed", "denied"]
		document_type: DF.Link
		installation: DF.Link
		read: DF.Literal["not asked", "allowed", "denied"]
		write: DF.Literal["not asked", "allowed", "denied"]
	# end: auto-generated types

	def autoname(self):
		# a uuid, and (installation, document_type) is looked up by field, the way
		# Builder Extension State looks up (installation, state_key). A composite name
		# would go stale the first time a doctype is renamed
		if not self.name:
			self.name = str(uuid.uuid4())


TABLE = "tabBuilder Extension DocType Grant"
UNIQUE_INDEX = "unique_installation_doctype"


def on_doctype_update():
	"""One answer per installation and doctype."""
	frappe.db.add_unique(
		"Builder Extension DocType Grant", ["installation", "document_type"], constraint_name=UNIQUE_INDEX
	)
