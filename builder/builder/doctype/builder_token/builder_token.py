# Copyright (c) 2025, Frappe Technologies Pvt Ltd and contributors
# For license information, please see license.txt

import uuid

import frappe
from frappe.model.document import Document
from frappe.modules.export_file import delete_folder, export_to_files
from frappe.utils.caching import redis_cache
from frappe.website.utils import delete_page_cache


class BuilderToken(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		dark_value: DF.Data | None
		group: DF.Data | None
		is_standard: DF.Check
		type: DF.Literal["Color", "Dimension", "Font"]
		value: DF.Data
		token_name: DF.Data
	# end: auto-generated types

	def autoname(self):
		if not self.name:
			self.name = str(uuid.uuid4())

	def after_insert(self):
		clear_builder_token_cache()

	def on_update(self):
		clear_builder_token_cache()
		if self.is_standard:
			export_to_files(
				record_list=[["Builder Token", self.name, "builder_token"]], record_module="builder"
			)

		if self.has_value_changed("is_standard") and not self.is_standard:
			delete_folder("builder", "builder_token", self.name)

	def on_trash(self):
		clear_builder_token_cache()
		if self.is_standard:
			delete_folder("builder", "builder_token", self.name)


@redis_cache(ttl=10 * 24 * 3600)
def get_css_variables():
	builder_tokens = frappe.get_all("Builder Token", fields=["name", "value", "dark_value"])
	css_variables = {}
	dark_mode_css_variables = {}

	for builder_token in builder_tokens:
		if not builder_token.value:
			continue
		key = f"--{builder_token.name}"
		css_variables[key] = builder_token.value
		if builder_token.dark_value:
			dark_mode_css_variables[key] = builder_token.dark_value

	return css_variables, dark_mode_css_variables


def get_variables_css() -> str:
	"""Render the CSS variables as an inline `:root {...}` rule.

	The /builder_assets/tokens.css route is a dynamically rendered page, not a
	real file, so the preview/PDF generator can't fetch it (it blocks access to
	non-existent local paths). Preview rendering inlines this string instead of
	linking the route. Mirrors www/builder_assets/tokens.css."""
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


def clear_builder_token_cache(doc=None, method=None):
	get_css_variables.clear_cache()
	# bust the rendered page cache for tokens.css and its compat alias variables.css
	delete_page_cache("builder_assets/tokens.css")
	delete_page_cache("builder_assets/variables.css")
