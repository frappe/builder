import os
import re
import shutil

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
		copy_assets_from_blocks(blocks, paths["assets_path"], target_app)
		page_config["blocks"] = blocks
		page_config["draft_blocks"] = None

	if page_doc.favicon:
		page_config["favicon"] = copy_asset_file(page_doc.favicon, paths["assets_path"], target_app)
	if page_doc.meta_image:
		page_config["meta_image"] = copy_asset_file(page_doc.meta_image, paths["assets_path"], target_app)

	page_config["project_folder"] = target_app
	page_config = frappe.as_json(page_config, ensure_ascii=False)

	with open(config_file_path, "w", encoding="utf-8") as f:
		f.write(page_config)

	export_client_scripts(page_doc, paths["client_scripts_path"])

	if blocks:
		components = extract_components_from_blocks(blocks)
		export_components(components, paths["components_path"], paths["assets_path"], target_app)

		fonts = extract_fonts_from_blocks(blocks)
		variables = extract_variables_from_blocks(blocks)

		for component_id in components:
			try:
				component_doc = frappe.get_cached_doc("Builder Component", component_id)
				component_blocks = frappe.parse_json(component_doc.block or "[]")
				copy_assets_from_blocks(component_blocks, paths["assets_path"], target_app)
				fonts.update(extract_fonts_from_blocks(component_blocks))
				variables.update(extract_variables_from_blocks(component_blocks))
			except Exception:
				pass

		export_fonts(fonts, paths["builder_files_path"], paths["assets_path"], target_app)
		export_variables(variables, paths["builder_files_path"])


def sync_standard_builder_pages(app_name=None):
	print("Syncing Standard Builder Pages")

	apps_to_sync = [app_name] if app_name else frappe.get_installed_apps()

	for app in apps_to_sync:
		app_path = frappe.get_app_path(app)
		pages_path = os.path.join(app_path, "builder_files", "pages")
		components_path = os.path.join(app_path, "builder_files", "components")
		scripts_path = os.path.join(app_path, "builder_files", "client_scripts")
		fonts_path = os.path.join(app_path, "builder_files", "fonts")
		variables_path = os.path.join(app_path, "builder_files", "variables")
		if os.path.exists(components_path):
			print(f"Importing components from {components_path}")
			make_records(components_path)
		if os.path.exists(scripts_path):
			print(f"Importing scripts from {scripts_path}")
			make_records(scripts_path)
		if os.path.exists(fonts_path):
			print(f"Importing fonts from {fonts_path}")
			import_fonts(fonts_path)
		if os.path.exists(variables_path):
			print(f"Importing variables from {variables_path}")
			make_records(variables_path)
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


def extract_fonts_from_blocks(blocks):
	"""Extract font family names from blocks recursively"""
	fonts = set()
	if not isinstance(blocks, list):
		blocks = [blocks]

	for block in blocks:
		if not isinstance(block, dict):
			continue

		for style_key in ["baseStyles", "mobileStyles", "tabletStyles", "rawStyles"]:
			styles = block.get(style_key, {})
			if styles and isinstance(styles, dict):
				font = styles.get("fontFamily")
				if font and font.strip():
					font = font.replace("\\", "").strip()
					if font:
						fonts.add(font)

		inner_html = block.get("innerHTML", "")
		if inner_html:
			inline_fonts = re.findall(r'font-family:\s*([^;"]+)', inner_html)
			for font in inline_fonts:
				font = font.strip().strip("'\"")
				if font:
					fonts.add(font)

		children = block.get("children", [])
		if children and isinstance(children, list):
			fonts.update(extract_fonts_from_blocks(children))

	return fonts


def extract_variables_from_blocks(blocks):
	"""Extract CSS variable names from blocks recursively"""
	variables = set()
	if not isinstance(blocks, list):
		blocks = [blocks]

	# Regex to match var(--variable-name, ...) or var(--variable-name)
	var_pattern = re.compile(r"var\(--([a-zA-Z0-9_-]+)")

	def extract_vars_from_value(value):
		"""Extract variable names from a CSS value"""
		if not value or not isinstance(value, str):
			return
		matches = var_pattern.findall(value)
		for match in matches:
			variables.add(match)

	for block in blocks:
		if not isinstance(block, dict):
			continue

		for style_key in ["baseStyles", "mobileStyles", "tabletStyles", "rawStyles"]:
			styles = block.get(style_key, {})
			if styles and isinstance(styles, dict):
				for _prop, value in styles.items():
					extract_vars_from_value(value)

		attributes = block.get("attributes", {})
		if attributes and isinstance(attributes, dict):
			for _prop, value in attributes.items():
				extract_vars_from_value(value)

		inner_html = block.get("innerHTML", "")
		if inner_html:
			extract_vars_from_value(inner_html)

		children = block.get("children", [])
		if children and isinstance(children, list):
			variables.update(extract_variables_from_blocks(children))

	return variables


def export_fonts(fonts, builder_files_path, assets_path, target_app="builder"):
	"""Export User Font records and their font files"""
	if not fonts:
		return

	fonts_path = os.path.join(builder_files_path, "fonts")
	os.makedirs(fonts_path, exist_ok=True)

	for font_name in fonts:
		try:
			font_docs = frappe.get_all(
				"User Font", filters={"font_name": font_name}, fields=["name", "font_name", "font_file"]
			)
			if not font_docs:
				continue

			font_doc = font_docs[0]

			# Copy font file to assets
			if font_doc.font_file:
				new_font_path = copy_font_file(font_doc.font_file, assets_path, target_app)
				if new_font_path:
					font_doc["font_file"] = new_font_path

			font_config = {
				"doctype": "User Font",
				"font_name": font_doc.font_name,
				"font_file": font_doc.get("font_file"),
			}

			safe_font_name = frappe.scrub(font_name)
			font_dir = os.path.join(fonts_path, safe_font_name)
			os.makedirs(font_dir, exist_ok=True)
			font_file_path = os.path.join(font_dir, f"{safe_font_name}.json")

			with open(font_file_path, "w", encoding="utf-8") as f:
				f.write(frappe.as_json(font_config, ensure_ascii=False))

		except Exception as e:
			frappe.log_error(f"Failed to export font {font_name}: {e!s}")


def copy_font_file(file_url, assets_path, target_app="builder"):
	"""Copy a font file to assets directory"""
	if not file_url or not isinstance(file_url, str):
		return None

	try:
		if file_url.startswith("/files/"):
			source_path = os.path.join(frappe.local.site_path, "public", file_url.lstrip("/"))
		elif file_url.startswith("/assets/") and "/builder_files/" in file_url:
			# Extract app name from URL like /assets/{app}/builder_files/assets/file.png
			parts = file_url.split("/")
			if len(parts) >= 3:
				app_name = parts[2]
				source_path = os.path.join(frappe.get_app_path(app_name), "public", "/".join(parts[3:]))
			else:
				return None
		elif file_url.startswith("/builder_assets/"):
			# Legacy path - check www folder
			source_path = os.path.join(frappe.get_app_path("builder"), "www", file_url.lstrip("/"))
		else:
			return None

		if os.path.exists(source_path):
			filename = os.path.basename(file_url)
			dest_path = os.path.join(assets_path, filename)
			shutil.copy2(source_path, dest_path)
			return f"/assets/{target_app}/builder_files/assets/{filename}"
	except Exception as e:
		frappe.log_error(f"Failed to copy font file {file_url}: {e!s}")

	return None


def export_variables(variables, builder_files_path):
	"""Export Builder Variable records"""
	if not variables:
		return

	variables_path = os.path.join(builder_files_path, "variables")
	os.makedirs(variables_path, exist_ok=True)

	for var_name in variables:
		try:
			# Convert CSS variable name (kebab-case) to possible DB name (snake_case)
			db_name = var_name.replace("-", "_")

			# Try to find the variable by name
			var_docs = frappe.get_all(
				"Builder Variable",
				filters=[
					["variable_name", "in", [var_name, db_name, var_name.replace("-", " ").title()]],
				],
				fields=["name", "variable_name", "type", "value", "dark_value"],
			)

			if not var_docs:
				# Also try searching by the scrubbed name
				var_docs = frappe.get_all(
					"Builder Variable",
					filters={"name": db_name},
					fields=["name", "variable_name", "type", "value", "dark_value"],
				)

			if not var_docs:
				continue

			var_doc = var_docs[0]

			var_config = {
				"doctype": "Builder Variable",
				"variable_name": var_doc.variable_name,
				"type": var_doc.type,
				"value": var_doc.value,
				"dark_value": var_doc.dark_value,
			}

			safe_var_name = frappe.scrub(var_doc.variable_name)
			var_dir = os.path.join(variables_path, safe_var_name)
			os.makedirs(var_dir, exist_ok=True)
			var_file_path = os.path.join(var_dir, f"{safe_var_name}.json")

			with open(var_file_path, "w", encoding="utf-8") as f:
				f.write(frappe.as_json(var_config, ensure_ascii=False))

		except Exception as e:
			frappe.log_error(f"Failed to export variable {var_name}: {e!s}")


def import_fonts(fonts_path):
	"""Import User Font records from exported files"""
	if not os.path.isdir(fonts_path):
		return

	for fname in os.listdir(fonts_path):
		font_dir = os.path.join(fonts_path, fname)
		if os.path.isdir(font_dir) and fname != "__pycache__":
			font_file = os.path.join(font_dir, f"{fname}.json")
			if os.path.exists(font_file):
				try:
					with open(font_file) as f:
						font_config = frappe.parse_json(f.read())

					if frappe.db.exists("User Font", font_config.get("font_name")):
						continue

					font_doc = frappe.get_doc(
						{
							"doctype": "User Font",
							"font_name": font_config.get("font_name"),
							"font_file": font_config.get("font_file"),
						}
					)
					font_doc.insert(ignore_permissions=True)
				except Exception as e:
					frappe.log_error(f"Failed to import font {fname}: {e!s}")
