# Copyright (c) 2023, Frappe Technologies Pvt Ltd and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
import os


class BuilderClientScript(Document):
	def before_insert(self):
		if self.script_type == "Javascript":
			self.create_file("js", "page_scripts")
		else:
			self.create_file("css", "page_styles")

	def create_file(self, file_type, folder_name):
		file_name = f"{self.name.strip()}-{frappe.generate_hash(length=10)}.{file_type}"
		file_path = f"./assets/builder/{folder_name}/{file_name}"
		# create missing folders
		os.makedirs(os.path.dirname(file_path), exist_ok=True)
		with open(file_path, "w") as f:
			f.write(self.script)
		self.public_url = f"/assets/builder/{folder_name}/{file_name}"
		print(self.public_url)

	def on_update(self):
		if self.script_type == "Javascript":
			self.update_file("js", "page_scripts")
		else:
			self.update_file("css", "page_styles")

	def update_file(self, file_type, folder_name):
		file_name = self.public_url.split("/")[-1]
		print(file_name)
		file_path = f"./assets/builder/{folder_name}/{file_name}"
		with open(file_path, "w") as f:
			f.write(self.script)

	def on_trash(self):
		return
		if self.script_type == "Javascript":
			self.delete_file("js", "page_scripts")
		else:
			self.delete_file("css", "page_styles")

	def delete_file(self, file_type, folder_name):
		if not self.public_url:
			return
		file_name = self.public_url.split("/")[-1]
		file_path = f"assets/builder/{folder_name}/{file_name}"
		os.remove(file_path)
