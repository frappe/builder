# Copyright (c) 2023, asdf and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.website.utils import clear_website_cache

class BuilderComponent(Document):
	def before_insert(self):
		if not self.component_id:
			self.component_id = frappe.generate_hash(length=16)

	def on_update(self):
		self.queue_action("clear_page_cache")

	def clear_page_cache(self):
		pages = frappe.get_all("Builder Page", filters={"published": 1}, fields=["name"])
		for page in pages:
			page_doc = frappe.get_cached_doc("Builder Page", page.name)
			if page_doc.is_component_used(self.component_id):
				clear_website_cache(page_doc.route)


