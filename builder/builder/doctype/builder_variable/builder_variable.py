# Copyright (c) 2025, Frappe Technologies Pvt Ltd and contributors
# For license information, please see license.txt

import os
import uuid

import frappe
from frappe.model.document import Document
from frappe.modules.export_file import delete_folder, export_to_files
from frappe.utils.caching import redis_cache
from frappe.website.utils import delete_page_cache


class BuilderVariable(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		dark_value: DF.Data | None
		group: DF.Data | None
		is_standard: DF.Check
		type: DF.Literal["Color", "Dimension"]
		value: DF.Data
		variable_name: DF.Data
	# end: auto-generated types

	def autoname(self):
		if not self.name:
			self.name = str(uuid.uuid4())

	def after_insert(self):
		clear_builder_variable_cache()

	def on_update(self):
		clear_builder_variable_cache()
		if self.is_standard:
			export_to_files(
				record_list=[["Builder Variable", self.name, "builder_variable"]], record_module="builder"
			)

		if self.has_value_changed("is_standard") and not self.is_standard:
			delete_folder("builder", "builder_variable", self.name)

		if frappe.conf.developer_mode:
			from builder.export_import_standard_page import export_variables

			referencing_standard_pages = self.get_referencing_pages(
				filters={"is_standard": 1}, fields=["app"]
			)
			referencing_apps = [page.app for page in referencing_standard_pages]
			for app in referencing_apps:
				app_path = frappe.get_app_path(app)
				builder_files_path = os.path.join(app_path, "builder_files")
				export_variables([self.variable_name], builder_files_path)

	def on_trash(self):
		clear_builder_variable_cache()
		if self.is_standard:
			delete_folder("builder", "builder_variable", self.name)
		self.delete_standard_exported_files()

	def after_rename(self, old: str, new: str, merge: bool = False) -> None:
		self.delete_standard_exported_files(old)

	def get_referencing_pages(self, filters: dict | None = None, fields: list[str] | None = None):
		filters = filters or {}
		fields = fields or ["name"]

		pages = frappe.get_all(
			"Builder Page",
			filters=filters,
			fields=fields,
			or_filters={
				"blocks": ["like", f"%var(--{self.variable_name})%"],
				"draft_blocks": ["like", f"%var(--{self.variable_name})%"],
			},
		)
		return pages

	def delete_standard_exported_files(self, old_name: str | None = None):
		if frappe.conf.developer_mode:
			from builder.export_import_standard_page import delete_standard_variable_files

			all_installed_apps = frappe.get_installed_apps()
			for app in all_installed_apps:
				delete_standard_variable_files(old_name or self.name, app)


@redis_cache(ttl=10 * 24 * 3600)
def get_css_variables():
	builder_variables = frappe.get_all("Builder Variable", fields=["name", "value", "dark_value"])
	css_variables = {}
	dark_mode_css_variables = {}

	for builder_variable in builder_variables:
		if not builder_variable.value:
			continue
		key = f"--{builder_variable.name}"
		css_variables[key] = builder_variable.value
		if builder_variable.dark_value:
			dark_mode_css_variables[key] = builder_variable.dark_value

	return css_variables, dark_mode_css_variables


def get_variables_css() -> str:
	"""Render the CSS variables as an inline `:root {...}` rule.

	The /builder_assets/variables.css route is a dynamically rendered page, not a
	real file, so the preview/PDF generator can't fetch it (it blocks access to
	non-existent local paths). Preview rendering inlines this string instead of
	linking the route. Mirrors www/builder_assets/variables.css."""
	css_variables, dark_mode_css_variables = get_css_variables()
	if not css_variables:
		return ""

	declarations = []
	for key, value in css_variables.items():
		dark_value = (dark_mode_css_variables or {}).get(key)
		if dark_value is not None and dark_value != value:
			declarations.append(f"{key}: light-dark({value}, {dark_value});")
		else:
			declarations.append(f"{key}: {value};")

	return ":root {\n" + "\n".join(declarations) + "\n}"


def clear_builder_variable_cache(doc=None, method=None):
	get_css_variables.clear_cache()
	# bust the rendered page cache for /builder_assets/variables.css
	delete_page_cache("builder_assets/variables.css")
