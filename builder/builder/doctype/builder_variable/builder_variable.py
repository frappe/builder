# Copyright (c) 2025, Frappe Technologies Pvt Ltd and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.model.naming import append_number_if_name_exists
from frappe.modules.export_file import delete_folder, export_to_files


class BuilderVariable(Document):
	def autoname(self):
		self.name = append_number_if_name_exists("Builder Variable", frappe.scrub(self.variable_name))

	def on_update(self):
		if self.is_standard:
			export_to_files(
				record_list=[["Builder Variable", self.name, "builder_variable"]], record_module="builder"
			)

		if self.has_value_changed("is_standard") and not self.is_standard:
			delete_folder("builder", "builder_variable", self.name)

	def on_trash(self):
		if self.is_standard:
			delete_folder("builder", "builder_variable", self.name)
