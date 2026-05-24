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
		export_variables(variables, paths["builder_files_path"], target_app)


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
		tokens_path = os.path.join(app_path, "builder_files", "tokens.json")
		if os.path.exists(components_path):
			print(f"Importing components from {components_path}")
			make_records(components_path)
		if os.path.exists(scripts_path):
			print(f"Importing scripts from {scripts_path}")
			make_records(scripts_path)
		if os.path.exists(fonts_path):
			print(f"Importing fonts from {fonts_path}")
			import_fonts(fonts_path)
		# Prefer the DTCG tokens.json bundle; fall back to legacy per-variable layout.
		if os.path.exists(tokens_path):
			print(f"Importing tokens from {tokens_path}")
			import_dtcg_tokens(tokens_path, default_group=app)
		elif os.path.exists(variables_path):
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
				"name": font_doc.name,
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
			parts = file_url.split("/")
			if len(parts) >= 3:
				app_name = parts[2]
				source_path = os.path.join(frappe.get_app_path(app_name), "public", "/".join(parts[3:]))
			else:
				return None
		elif file_url.startswith("/builder_assets/"):
			source_path = os.path.join(frappe.get_app_path("builder"), "www", file_url.lstrip("/"))
		else:
			return None

		if os.path.exists(source_path):
			filename = os.path.basename(file_url)
			dest_path = os.path.join(assets_path, filename)
			shutil.copy2(source_path, dest_path)
			return f"/assets/{target_app}/builder_assets/{filename}"
	except Exception as e:
		frappe.log_error(f"Failed to copy font file {file_url}: {e!s}")

	return None


_DTCG_EXTENSION_KEY = "io.frappe.builder"


def export_variables(variables, builder_files_path, source_app="builder"):
	"""Export Builder Variable records as a DTCG-formatted tokens.json bundle.

	`variables` is the set of names extracted from `var(--<name>)` refs in
	exported blocks. With stable IDs each `<name>` IS the doctype `name`.
	Unknown names (e.g. references to vars that no longer exist on this site)
	are silently skipped.

	The on-disk shape follows https://www.designtokens.org/tr/drafts/format/ —
	groups become nested objects, tokens carry `$type` + `$value`. Builder
	metadata that has no first-class spec slot (the stable id, dark mode value,
	source app) rides under `$extensions["io.frappe.builder"]`.
	"""
	if not variables:
		return

	tokens_root: dict = {}

	for var_name in variables:
		if not frappe.db.exists("Builder Variable", var_name):
			continue
		try:
			var_doc = frappe.get_cached_doc("Builder Variable", var_name)
			_insert_dtcg_token(tokens_root, var_doc, source_app)
		except Exception as e:
			frappe.log_error(f"Failed to export variable {var_name}: {e!s}")

	if not tokens_root:
		return

	tokens_file = os.path.join(builder_files_path, "tokens.json")
	with open(tokens_file, "w", encoding="utf-8") as f:
		f.write(frappe.as_json(tokens_root, ensure_ascii=False))


def _insert_dtcg_token(root: dict, var_doc, source_app: str) -> None:
	segments = [s for s in (var_doc.group or "").split("/") if s.strip()]
	leaf_name = var_doc.variable_name or var_doc.name

	cursor = root
	for seg in segments:
		cursor = cursor.setdefault(seg, {})

	token: dict = {
		"$type": (var_doc.type or "Color").lower(),  # color | dimension
		"$value": var_doc.value,
	}
	if var_doc.description:
		token["$description"] = var_doc.description

	extensions: dict = {"id": var_doc.name, "sourceApp": source_app}
	if var_doc.dark_value:
		extensions["darkValue"] = var_doc.dark_value
	token["$extensions"] = {_DTCG_EXTENSION_KEY: extensions}

	# Avoid colliding with an existing sub-group of the same name.
	if leaf_name in cursor and isinstance(cursor[leaf_name], dict) and "$value" not in cursor[leaf_name]:
		leaf_name = f"{leaf_name}-{var_doc.name}"
	cursor[leaf_name] = token


def import_dtcg_tokens(tokens_path: str, default_group: str | None = None) -> dict:
	"""Import a DTCG tokens.json file. Returns {'created': n, 'skipped': n}.

	Mirrors what the dedicated Variables page calls when a user uploads JSON.
	`default_group` is applied when a token sits at the root of the file with
	no group nesting (template imports use the source app name).
	"""
	try:
		with open(tokens_path, encoding="utf-8") as f:
			tree = frappe.parse_json(f.read())
	except Exception as e:
		frappe.log_error(f"Failed to read DTCG tokens from {tokens_path}: {e!s}")
		return {"created": 0, "skipped": 0}

	flat = list(_walk_dtcg_tree(tree, group_segments=[], inherited_type=None))
	created, skipped = 0, 0
	for token in flat:
		ext = (token.get("$extensions") or {}).get(_DTCG_EXTENSION_KEY) or {}
		token_id = ext.get("id")
		# Collision or missing id → mint a new one; the existing record wins.
		if not token_id or frappe.db.exists("Builder Variable", token_id):
			skipped += 1
			continue

		group_path = "/".join(token["_group"])
		if not group_path and default_group:
			group_path = default_group

		try:
			_insert_builder_variable_preserving_name(
				name=token_id,
				variable_name=token["_name"],
				value=token.get("$value") or "",
				dark_value=ext.get("darkValue") or "",
				type_=_dtcg_type_to_builder(token.get("$type")),
				group=group_path,
				description=token.get("$description") or "",
				ignore_permissions=True,
			)
			created += 1
		except Exception as e:
			frappe.log_error(f"Failed to import DTCG token {token_id}: {e!s}")
			skipped += 1
	return {"created": created, "skipped": skipped}


def _insert_builder_variable_preserving_name(
	*,
	name: str,
	variable_name: str,
	value: str,
	dark_value: str,
	type_: str,
	group: str,
	description: str,
	ignore_permissions: bool = False,
) -> None:
	"""Insert a Builder Variable with `name` preserved.

	Frappe's `set_new_name` resets `doc.name = None` before calling `autoname()`
	unless `frappe.flags.in_import` is set. The importer needs the original id
	preserved so block references in companion templates stay resolvable.
	"""
	prev_flag = frappe.flags.in_import
	frappe.flags.in_import = True
	try:
		doc = frappe.get_doc(
			{
				"doctype": "Builder Variable",
				"name": name,
				"variable_name": variable_name,
				"value": value,
				"dark_value": dark_value,
				"type": type_,
				"group": group,
				"description": description,
			}
		)
		doc.insert(ignore_permissions=ignore_permissions)
	finally:
		frappe.flags.in_import = prev_flag


def _walk_dtcg_tree(node, group_segments, inherited_type):
	"""Yield flat token dicts from a nested DTCG group structure."""
	if not isinstance(node, dict):
		return
	# Group-level $type cascades to children.
	current_type = node.get("$type", inherited_type)
	for key, value in node.items():
		if key.startswith("$"):
			continue
		if not isinstance(value, dict):
			continue
		if "$value" in value:
			yield {
				"_name": key,
				"_group": list(group_segments),
				"$type": value.get("$type", current_type),
				"$value": value["$value"],
				"$description": value.get("$description"),
				"$extensions": value.get("$extensions") or {},
			}
		else:
			yield from _walk_dtcg_tree(value, [*group_segments, key], current_type)


def _dtcg_type_to_builder(dtcg_type) -> str:
	if not dtcg_type:
		return "Color"
	t = str(dtcg_type).lower()
	if t == "dimension":
		return "Dimension"
	return "Color"


@frappe.whitelist()
def export_builder_variables_as_dtcg() -> dict:
	"""Return the entire Builder Variable store as a DTCG tokens.json structure."""
	tokens_root: dict = {}
	for var in frappe.get_all(
		"Builder Variable",
		fields=["name", "variable_name", "group", "description", "type", "value", "dark_value"],
	):
		_insert_dtcg_token(tokens_root, var, source_app=frappe.local.site or "builder")
	return tokens_root


@frappe.whitelist()
def import_builder_variables_from_dtcg(tokens_json: str, default_group: str | None = None) -> dict:
	"""Import tokens from a DTCG JSON payload uploaded by the user.

	The payload is the parsed contents of a tokens.json file (passed as a JSON
	string from the frontend).
	"""
	try:
		tree = frappe.parse_json(tokens_json)
	except Exception:
		frappe.throw("Invalid JSON")
	flat = list(_walk_dtcg_tree(tree, group_segments=[], inherited_type=None))
	created, skipped = 0, 0
	for token in flat:
		ext = (token.get("$extensions") or {}).get(_DTCG_EXTENSION_KEY) or {}
		token_id = ext.get("id") or frappe.generate_hash(length=10)
		if frappe.db.exists("Builder Variable", token_id):
			token_id = frappe.generate_hash(length=10)
		group_path = "/".join(token["_group"]) or (default_group or "")
		try:
			_insert_builder_variable_preserving_name(
				name=token_id,
				variable_name=token["_name"],
				value=token.get("$value") or "",
				dark_value=ext.get("darkValue") or "",
				type_=_dtcg_type_to_builder(token.get("$type")),
				group=group_path,
				description=token.get("$description") or "",
			)
			created += 1
		except Exception as e:
			frappe.log_error(f"Failed to import DTCG token {token_id}: {e!s}")
			skipped += 1
	return {"created": created, "skipped": skipped}


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
