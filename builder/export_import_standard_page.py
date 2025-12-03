import os

import frappe
from frappe.modules.export_file import strip_default_fields

from builder.utils import (
	copy_asset_file,
	copy_assets_from_blocks,
	create_export_directories,
	export_client_scripts,
	export_components,
	extract_components_from_blocks,
	make_records,
)


def export_page_as_standard(page_name, target_app):
	"""Export a builder page as standard files to the specified app"""
	page_doc = frappe.get_doc("Builder Page", page_name)
	export_name = frappe.scrub(page_doc.page_name)

	app_path = frappe.get_app_path(target_app)
	if not app_path:
		frappe.throw(f"App '{target_app}' not found")

	paths = create_export_directories(app_path, export_name)

	page_config = page_doc.as_dict(no_nulls=True)
	page_config = strip_default_fields(page_doc, page_config)

	config_file_path = os.path.join(paths["page_path"], f"{export_name}.json")

	blocks = frappe.parse_json(page_config.get("draft_blocks") or page_config["blocks"])
	if blocks:
		copy_assets_from_blocks(blocks, paths["assets_path"])
		page_config["blocks"] = blocks
		page_config["draft_blocks"] = None

	if page_doc.favicon:
		page_config["favicon"] = copy_asset_file(page_doc.favicon, paths["assets_path"])
	if page_doc.meta_image:
		page_config["meta_image"] = copy_asset_file(page_doc.meta_image, paths["assets_path"])

	page_config["project_folder"] = target_app
	page_config = frappe.as_json(page_config, ensure_ascii=False)

	with open(config_file_path, "w", encoding="utf-8") as f:
		f.write(page_config)

	export_client_scripts(page_doc, paths["client_scripts_path"])

	if blocks:
		components = extract_components_from_blocks(blocks)
		export_components(components, paths["components_path"], paths["assets_path"])


def sync_standard_builder_pages(app_name=None):
	print("Syncing Standard Builder Pages")

	apps_to_sync = [app_name] if app_name else frappe.get_installed_apps()

	for app in apps_to_sync:
		app_path = frappe.get_app_path(app)
		pages_path = os.path.join(app_path, "builder_files", "pages")
		components_path = os.path.join(app_path, "builder_files", "components")
		scripts_path = os.path.join(app_path, "builder_files", "client_scripts")
		if os.path.exists(components_path):
			print(f"Importing components from {components_path}")
			make_records(components_path)
		if os.path.exists(scripts_path):
			print(f"Importing scripts from {scripts_path}")
			make_records(scripts_path)
		if os.path.exists(pages_path):
			frappe.get_doc(
				{
					"doctype": "Builder Project Folder",
					"folder_name": app,
					"is_standard": 1,
				}
			).insert(ignore_if_duplicate=True)
			print(f"Importing page from {pages_path}")
			make_records(pages_path)
