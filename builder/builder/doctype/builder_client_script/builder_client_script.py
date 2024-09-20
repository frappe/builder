# Copyright (c) 2023, Frappe Technologies Pvt Ltd and contributors
# For license information, please see license.txt

import os

import frappe
from csscompressor import compress
from frappe.model.document import Document
from frappe.modules.export_file import export_to_files
from frappe.utils import get_files_path
from jsmin import jsmin


class BuilderClientScript(Document):
	def before_insert(self):
		if not self.name:
			self.name = f"{self.script_type}-{frappe.generate_hash(length=5)}"
		self.update_script_file()

	def on_update(self):
		self.update_script_file()
		self.update_exported_script()

	def on_trash(self):
		self.delete_script_file()

	def update_script_file(self):
		script_type = self.script_type or ""
		file_name = self.get_file_name_from_url()
		file_extension = "js" if script_type == "JavaScript" else "css"
		if not file_name:
			file_name = f"{self.name.strip()}-{frappe.generate_hash(length=10)}.{file_extension}"
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
			frappe.get_app_path("builder"), "builder", "builder_client_script", self.name
		)
		if os.path.exists(script_path):
			export_to_files(
				record_list=[["Builder Client Script", self.name, "builder_client_script"]],
				record_module="builder",
			)
