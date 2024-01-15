# Copyright (c) 2023, Frappe Technologies Pvt Ltd and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
import os
from frappe.utils import get_files_path

class BuilderClientScript(Document):
	def before_insert(self):
		if not self.name:
			self.name = f"{self.script_type}-{frappe.generate_hash(length=5)}"
		self.update_script_file()

	def on_update(self):
		self.update_script_file()

	def on_trash(self):
		self.delete_script_file()

	def update_script_file(self):
		script = self.script or ""
		script_type = self.script_type or ""
		file_name = self.get_file_name_from_url()
		file_extension = "js" if script_type == "JavaScript" else "css"
		if not file_name:
			file_name = f"{self.name.strip()}-{frappe.generate_hash(length=10)}.{file_extension}"
		folder_name = "page_scripts" if script_type == "JavaScript" else "page_styles"
		file_path = get_files_path(f"{folder_name}/{file_name}")
		os.makedirs(os.path.dirname(file_path), exist_ok=True)
		with open(file_path, "w") as f:
			f.write(self.script)

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