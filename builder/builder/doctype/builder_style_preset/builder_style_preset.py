# Copyright (c) 2026, Frappe Technologies Pvt Ltd and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document
from frappe.modules.export_file import delete_folder, export_to_files


class BuilderStylePreset(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		is_standard: DF.Check
		sort_order: DF.Int
		style_map: DF.JSON
		style_name: DF.Data
	# end: auto-generated types

	def on_update(self):
		if self.is_standard:
			export_to_files(
				record_list=[["Builder Style Preset", self.name, "builder_style_preset"]],
				record_module="builder",
			)
		if self.has_value_changed("is_standard") and not self.is_standard:
			delete_folder("builder", "builder_style_preset", self.name)

	def on_trash(self):
		if self.is_standard:
			delete_folder("builder", "builder_style_preset", self.name)

	pass
