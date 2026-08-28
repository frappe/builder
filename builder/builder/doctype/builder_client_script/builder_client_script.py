# Copyright (c) 2023, Frappe Technologies Pvt Ltd and contributors
# For license information, please see license.txt

import os

import frappe
from csscompressor import compress
from frappe.model.document import Document
from frappe.modules.export_file import export_to_files
from frappe.utils import get_files_path
from frappe.utils.telemetry import capture
from jsmin import jsmin

from builder.export_import_standard_page import StandardFileSync
from builder.utils import is_bulk_import


class BuilderClientScript(StandardFileSync, Document):
	export_subdir = "client_scripts"
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		public_url: DF.ReadOnly | None
		script: DF.Code
		script_type: DF.Autocomplete
	# end: auto-generated types

	def before_insert(self):
		if not self.name:
			self.name = f"{self.script_type}-{frappe.generate_hash(length=5)}"
		self.update_script_file()
		capture("builder_client_script_created", "builder")

	def on_update(self):
		self.update_script_file()
		self.update_exported_script()
		self.export_standard_files()

	def on_trash(self):
		self.delete_script_file()
		self.delete_standard_exported_files()

	def export_standard_files(self) -> None:
		if not frappe.conf.developer_mode or is_bulk_import():
			return
		from builder.export_import_standard_page import export_client_scripts

		for app in self.referencing_apps:
			client_scripts_path = os.path.join(frappe.get_app_path(app), "builder_files", "client_scripts")
			export_client_scripts([self.name], client_scripts_path)

	def get_referencing_pages(
		self, filters: dict | None = None, fields: list[str] | None = None
	) -> list[dict]:
		"""Return the pages that use this script.

		Args:
		filters: Filters to apply to the pages.
		fields: Fields to return from the pages.
		"""
		refs = frappe.get_all(
			"Builder Page Client Script",
			filters={"builder_script": self.name},
			fields=["parent"],
		)

		filters = filters or {}
		filters["name"] = ["in", [ref.parent for ref in refs]]
		fields = fields or ["name"]
		pages = frappe.get_all("Builder Page", filters=filters, fields=fields)
		return pages

	def update_script_file(self):
		script_type = self.script_type or ""
		file_name = self.get_file_name_from_url()
		file_extension = "js" if script_type == "JavaScript" else "css"
		if not file_name:
			name = self.name.strip() if self.name else "unnamed"
			file_name = f"{name}-{frappe.generate_hash(length=10)}.{file_extension}"
		folder_name = "page_scripts" if script_type == "JavaScript" else "page_styles"
		file_path = get_files_path(f"{folder_name}/{file_name}")
		os.makedirs(os.path.dirname(file_path), exist_ok=True)
		with open(file_path, "w") as f:
			script = self.script or ""
			if script_type == "JavaScript":
				script = jsmin(script, quote_chars="'\"`")
			if script_type == "CSS":
				script = compress(script)
			f.write(script)

		public_url = f"/files/{folder_name}/{file_name}?v={frappe.generate_hash(length=10)}"
		self.db_set("public_url", public_url, commit=True)

	def delete_script_file(self):
		script_type = self.script_type or ""
		folder_name = "page_scripts" if script_type == "JavaScript" else "page_styles"
		file_name = self.get_file_name_from_url()
		file_path = get_files_path(f"{folder_name}/{file_name}")
		if os.path.exists(file_path):
			os.remove(file_path)

	def get_file_name_from_url(self):
		public_url = self.public_url or ""
		if "?" in public_url:
			public_url = public_url.split("?")[0]
		return public_url.split("/")[-1]

	def update_exported_script(self):
		if not frappe.conf.developer_mode:
			return
		script_path = os.path.join(
			frappe.get_app_path("builder"), "builder", "builder_client_script", self.name or ""
		)
		if os.path.exists(script_path):
			export_to_files(
				record_list=[["Builder Client Script", self.name, "builder_client_script"]],
				record_module="builder",
			)
