# Copyright (c) 2026, Frappe Technologies Pvt Ltd and contributors
# For license information, please see license.txt

import uuid

import frappe
from frappe.model.document import Document


class BuilderExtensionGrant(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		delete_access: DF.Literal["not asked", "allowed", "denied"]
		document_type: DF.Link
		installation: DF.Link
		read_access: DF.Literal["not asked", "allowed", "denied"]
		write_access: DF.Literal["not asked", "allowed", "denied"]
	# end: auto-generated types

	def autoname(self):
		# a uuid, and (installation, document_type) is looked up by field, the way
		# Builder Extension State looks up (installation, key). A composite name
		# would go stale the first time a doctype is renamed
		if not self.name:
			self.name = str(uuid.uuid4())


TABLE = "tabBuilder Extension Grant"
UNIQUE_INDEX = "unique_installation_doctype"
OLD_UNIQUE_INDEX = "unique_user_extension_doctype"


def on_doctype_update():
	"""One answer per installation and doctype.

	The old key named the user and the extension, which is the installation's
	identity minus its source. Two copies of one extension shared one answer, and
	uninstalling either took both. The old index is dropped here, because Frappe
	leaves a removed field's column behind and a unique index over empty columns
	would let one doctype be granted once for the whole site.
	"""
	if frappe.db.has_index(TABLE, OLD_UNIQUE_INDEX):
		frappe.db.sql_ddl(f"alter table `{TABLE}` drop index `{OLD_UNIQUE_INDEX}`")

	frappe.db.add_unique(
		"Builder Extension Grant", ["installation", "document_type"], constraint_name=UNIQUE_INDEX
	)
