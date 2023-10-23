# Copyright (c) 2023, asdf and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document

class BuilderComponent(Document):
	def before_insert(self):
		if not self.component_id:
			# Generate a ID for the component so that it is uniquely identifiable if copied to different site
			self.component_id = frappe.generate_hash(length=16)
