# Copyright (c) 2023, asdf and contributors
# For license information, please see license.txt

import os

import frappe
from frappe.model.document import Document
from frappe.modules.export_file import export_to_files
from frappe.website.utils import clear_website_cache


class BuilderComponent(Document):
	def before_insert(self):
		if not self.component_id:
			self.component_id = frappe.generate_hash(length=16)

	def on_update(self):
		self.queue_action("clear_page_cache")
		self.update_exported_component()

	def clear_page_cache(self):
		pages = frappe.get_all("Builder Page", filters={"published": 1}, fields=["name"])
		for page in pages:
			page_doc = frappe.get_cached_doc("Builder Page", page.name)
			if page_doc.is_component_used(self.component_id):
				clear_website_cache(page_doc.route)

	def update_exported_component(self):
		if not frappe.conf.developer_mode:
			return
		component_path = os.path.join(
			frappe.get_app_path("builder"), "builder", "builder_component", self.name
		)
		if os.path.exists(component_path):
			export_to_files(
				record_list=[["Builder Component", self.name, "builder_component"]],
				record_module="builder",
			)
