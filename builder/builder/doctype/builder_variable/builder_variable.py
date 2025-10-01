# Copyright (c) 2025, Frappe Technologies Pvt Ltd and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.model.naming import append_number_if_name_exists
from frappe.modules.export_file import delete_folder, export_to_files
from frappe.utils.caching import redis_cache

from builder.utils import camel_case_to_kebab_case


class BuilderVariable(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		dark_value: DF.Data | None
		is_standard: DF.Check
		type: DF.Literal["Color", "Spacing"]
		value: DF.Data
		variable_name: DF.Data
	# end: auto-generated types

	def autoname(self):
		self.name = append_number_if_name_exists("Builder Variable", frappe.scrub(self.variable_name))

	def after_insert(self):
		get_css_variables.clear_cache()

	def on_update(self):
		get_css_variables.clear_cache()
		if self.is_standard:
			export_to_files(
				record_list=[["Builder Variable", self.name, "builder_variable"]], record_module="builder"
			)

		if self.has_value_changed("is_standard") and not self.is_standard:
			delete_folder("builder", "builder_variable", self.name)

	def on_trash(self):
		get_css_variables.clear_cache()
		if self.is_standard:
			delete_folder("builder", "builder_variable", self.name)


@redis_cache(ttl=10 * 24 * 3600)
def get_css_variables():
	builder_variables = frappe.get_all("Builder Variable", fields=["variable_name", "value", "dark_value"])
	css_variables = {}
	dark_mode_css_variables = {}

	for builder_variable in builder_variables:
		if builder_variable.variable_name and builder_variable.value:
			variable_name = f"--{camel_case_to_kebab_case(builder_variable.variable_name, True)}"
			css_variables[variable_name] = builder_variable.value

			if hasattr(builder_variable, "dark_value") and builder_variable.dark_value:
				dark_mode_css_variables[variable_name] = builder_variable.dark_value

	return css_variables, dark_mode_css_variables


def clear_builder_variable_cache(doc, method):
	get_css_variables.clear_cache()
