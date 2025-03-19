import os

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import get_files_path
from frappe.utils.caching import redis_cache


class BuilderSettings(Document):
	def on_update(self):
		self.handle_script_update("script", "JavaScript", "js", "page_scripts")
		self.handle_script_update("style", "css", "css", "page_styles")
		if self.has_value_changed("home_page"):
			frappe.cache.delete_key("home_page")

	def handle_script_update(self, attribute, script_type, extension, folder_name):
		if self.has_value_changed(attribute):
			if getattr(self, attribute):
				self.update_script_file(attribute, script_type, extension, folder_name)
			else:
				self.delete_script_file(attribute, extension, folder_name)

	def update_script_file(self, attribute, script_type, extension, folder_name):
		script = self.script if script_type == "JavaScript" else self.style
		file_name = f"builder-asset-{attribute}.{extension}"
		file_path = self.get_file_path(file_name, folder_name)
		self.write_to_file(file_path, script)
		public_url = f"/files/{folder_name}/{file_name}?v={frappe.generate_hash(length=10)}"
		self.db_set(f"{attribute}_public_url", public_url, commit=True)

	def delete_script_file(self, script_type, extension, folder_name):
		file_name = f"builder-asset-{script_type}.{extension}"
		file_path = self.get_file_path(file_name, folder_name)
		if os.path.exists(file_path):
			os.remove(file_path)
		self.db_set(f"{script_type.lower()}_public_url", "", commit=True)

	def get_file_path(self, file_name, folder_name):
		file_path = get_files_path(f"{folder_name}/{file_name}")
		os.makedirs(os.path.dirname(file_path), exist_ok=True)
		return file_path

	def write_to_file(self, file_path, content):
		with open(file_path, "w") as f:
			f.write(content)


def get_website_user_home_page(session_user=None):
	home_page = frappe.get_cached_value("Builder Settings", None, "home_page")
	return home_page


@frappe.whitelist()
def get_components():
	# in label value format
	return frappe.get_all("Builder Component", fields=["name as value", "component_name as label"])


@frappe.whitelist()
def replace_component(target_component: str, replace_with: str, filters=None):
	if not target_component or not replace_with:
		return
	# check permissions
	if not frappe.has_permission("Builder Page", ptype="write"):
		frappe.throw(_("You don't have permission to access this component"), frappe.PermissionError)

	# check if the replace_with component exists
	if not frappe.db.exists("Builder Component", replace_with):
		frappe.throw(_("The component you are trying to replace with does not exist"))

	# go through all the pages and replace the old component with the new component
	pages = frappe.get_all(
		"Builder Page",
		fields=["name"],
		filters=filters,
		or_filters={
			"blocks": ["like", f"%{target_component}%"],
			"draft_blocks": ["like", f"%{target_component}%"],
		},
	)
	for page in pages:
		doc = frappe.get_doc("Builder Page", page.name)
		doc.replace_component(target_component, replace_with)


@frappe.whitelist()
@redis_cache()
def get_component_usage_count(component_id: str, filters=None):
	pages = frappe.get_all(
		"Builder Page",
		filters=filters,
		fields=["name", "page_title", "route", "preview"],
		or_filters={
			"blocks": ["like", f"%{component_id}%"],
			"draft_blocks": ["like", f"%{component_id}%"],
		},
	)
	return {
		"count": len(pages),
		"pages": pages,
	}
