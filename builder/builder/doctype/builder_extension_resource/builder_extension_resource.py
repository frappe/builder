# Copyright (c) 2026, Frappe Technologies Pvt Ltd and contributors
# For license information, please see license.txt

import uuid

from frappe.model.document import Document


class BuilderExtensionResource(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		extension: DF.Link
		resource_name: DF.Data
		resource_type: DF.Literal["DocType", "Web Form", "Client Script"]
	# end: auto-generated types

	def autoname(self):
		# a uuid, and the pair (extension, resource_name) is looked up by field, the
		# way Builder Token and Builder Extension DocType Grant are
		if not self.name:
			self.name = str(uuid.uuid4())
