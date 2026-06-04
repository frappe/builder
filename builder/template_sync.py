"""Import/export of builder template groups.

A template group is a set of highly-functional pages (landing, contact, ...)
that share one set of Builder Components and Builder Variables (the variable
`group` matches the template group). Fixtures live on disk at
builder/builder/builder_templates/<group>/:

	<group>/
		template.json                       # UI manifest: title, description, preview, pages order
		pages/<page>/<page>.json
		components/<component_id>/<component_id>.json
		variables/<uuid>/<uuid>.json
		client_scripts/<name>/<name>.json
		fonts/<name>/<name>.json

Group assets (images, page previews, font files) are committed to
builder/www/builder_assets/<group>/ and served at /builder_assets/<group>/.

The committed fixtures are the source of truth. They are authored in developer
mode — saving a template page auto-exports its whole group via
`export_template_group` — and imported on every install/migrate via
`sync_builder_templates`. In production, template pages are read-only and only
surface through the template selector.

A page is part of a shipped template group when both `is_template` and
`template_group` are set. Pages with only `is_template` (saved as template by a
user) are left alone by the sync and the read-only guard.
"""

import json
import os
import shutil
from urllib.parse import unquote

import frappe
from frappe.modules.export_file import strip_default_fields
from frappe.modules.import_file import import_file_by_path
from frappe.utils import get_url

from builder.export_import_standard_page import extract_fonts_from_blocks, import_fonts
from builder.utils import (
	export_client_scripts,
	extract_components_from_blocks,
	make_records,
)


def get_templates_root():
	return frappe.get_module_path("builder", "builder_templates")


def get_group_assets_root(group_folder):
	return os.path.join(frappe.get_app_path("builder"), "www", "builder_assets", group_folder)


# ---------------------------------------------------------------------------
# import
# ---------------------------------------------------------------------------
def sync_builder_templates():
	"""Import all template group fixtures from disk. Called on install/migrate."""
	templates_root = get_templates_root()
	if not os.path.isdir(templates_root):
		return

	groups_pages = {}
	for group in sorted(os.listdir(templates_root)):
		group_path = os.path.join(templates_root, group)
		if not os.path.isdir(group_path) or group.startswith((".", "_")):
			continue
		print(f"Syncing builder template group: {group}")
		make_records(os.path.join(group_path, "variables"))
		make_records(os.path.join(group_path, "components"))
		make_records(os.path.join(group_path, "client_scripts"))
		import_fonts(os.path.join(group_path, "fonts"))
		groups_pages[group] = import_template_pages(os.path.join(group_path, "pages"), group)

	reconcile_deleted_templates(groups_pages)


def import_template_pages(pages_path, group):
	"""Import page fixtures of a group and re-stamp template invariants."""
	page_names = []
	if not os.path.isdir(pages_path):
		return page_names

	for fname in sorted(os.listdir(pages_path)):
		page_file = os.path.join(pages_path, fname, f"{fname}.json")
		if not os.path.isfile(page_file):
			continue
		with open(page_file, encoding="utf-8") as f:
			fixture = frappe.parse_json(f.read())
		page_name = fixture.get("name") or fname
		import_file_by_path(page_file)
		if frappe.db.exists("Builder Page", page_name):
			# import_file_by_path skips files whose db timestamp is newer, so
			# enforce the invariants (and the committed preview) directly —
			# templates are never live routes
			values = {"is_template": 1, "template_group": group, "published": 0, "published_at": None}
			if fixture.get("preview"):
				values["preview"] = fixture["preview"]
			frappe.db.set_value("Builder Page", page_name, values, update_modified=False)
			page_names.append(page_name)
	return page_names


def reconcile_deleted_templates(groups_pages):
	"""Delete template pages whose fixtures were removed from disk.

	Skipped in developer mode, where the DB is being authored and fixtures may
	not exist yet. Pages without a template_group (user templates) are left alone.
	Shared components/variables are not reconciled — orphans are harmless, while
	deleting them could break pages that still reference them.
	"""
	if frappe.conf.developer_mode:
		return

	template_pages = frappe.get_all(
		"Builder Page",
		filters={"is_template": 1, "template_group": ("is", "set")},
		fields=["name", "template_group"],
	)
	for page in template_pages:
		if page.name not in (groups_pages.get(page.template_group) or []):
			frappe.delete_doc("Builder Page", page.name, force=True, ignore_permissions=True)


# ---------------------------------------------------------------------------
# export (developer mode)
# ---------------------------------------------------------------------------
def export_template_group(group):
	"""Export every page of a template group — with the shared components,
	variables, client scripts, fonts and assets — to its fixture folder."""
	group_folder = frappe.scrub(group)
	group_path = os.path.join(get_templates_root(), group_folder)
	paths = {
		key: os.path.join(group_path, key)
		for key in ("pages", "components", "variables", "client_scripts", "fonts")
	}
	for path in paths.values():
		os.makedirs(path, exist_ok=True)

	pages = frappe.get_all(
		"Builder Page",
		filters={"is_template": 1, "template_group": group},
		pluck="name",
		order_by="creation",
	)
	components = set()
	fonts = set()
	for page_name in pages:
		page_doc = frappe.get_doc("Builder Page", page_name)
		blocks = export_template_page(page_doc, paths["pages"], group_folder)
		components.update(extract_components_from_blocks(blocks))
		fonts.update(extract_fonts_from_blocks(blocks))
		export_client_scripts(page_doc, paths["client_scripts"])

	for component_id in components:
		component_blocks = export_template_component(component_id, paths["components"], group_folder)
		fonts.update(extract_fonts_from_blocks(component_blocks))

	export_template_variables(group, paths["variables"])
	export_template_fonts(fonts, paths["fonts"], group_folder)
	update_template_manifest(group_path, pages, title=group)


def export_template_page(page_doc, pages_path, group_folder):
	"""Write one page fixture; returns the exported blocks."""
	preview_url = ensure_template_preview(page_doc)

	page_config = page_doc.as_dict(no_nulls=True)
	page_config = strip_default_fields(page_doc, page_config)

	blocks = frappe.parse_json(page_config.get("draft_blocks") or page_config.get("blocks") or "[]")
	copy_block_assets(blocks, group_folder, str(page_doc.name))
	page_config["blocks"] = blocks
	page_config["draft_blocks"] = None
	page_config["is_template"] = 1
	page_config["template_group"] = page_doc.template_group
	page_config["published"] = 0
	page_config["published_at"] = None
	page_config["project_folder"] = None
	# point at the committed preview (the db field may still hold the fallback
	# if the .webp already existed from a prior export and generation was skipped)
	if preview_url:
		page_config["preview"] = preview_url

	for field in ("favicon", "meta_image"):
		if page_config.get(field):
			new_url = copy_file_url_to_group_assets(page_config[field], group_folder, str(page_doc.name))
			if new_url:
				page_config[field] = new_url

	export_name = frappe.scrub(str(page_doc.name))
	page_dir = os.path.join(pages_path, export_name)
	os.makedirs(page_dir, exist_ok=True)
	with open(os.path.join(page_dir, f"{export_name}.json"), "w", encoding="utf-8") as f:
		f.write(frappe.as_json(page_config, ensure_ascii=False))
	return blocks


def export_template_component(component_id, components_path, group_folder):
	"""Write one component fixture; returns the component's blocks."""
	component_doc = frappe.get_doc("Builder Component", component_id)
	component_blocks = frappe.parse_json(component_doc.block or "{}")
	copy_block_assets(component_blocks, group_folder, "components")

	component_config = component_doc.as_dict(no_nulls=True)
	component_config = strip_default_fields(component_doc, component_config)
	component_config["block"] = frappe.as_json(component_blocks, indent=0)
	# page references are site-local and meaningless in fixtures
	component_config["for_web_page"] = None

	export_name = frappe.scrub(str(component_doc.name)).replace("/", "_")
	component_dir = os.path.join(components_path, export_name)
	os.makedirs(component_dir, exist_ok=True)
	with open(os.path.join(component_dir, f"{export_name}.json"), "w", encoding="utf-8") as f:
		f.write(frappe.as_json(component_config, ensure_ascii=False))
	return component_blocks


def export_template_variables(group, variables_path):
	"""Write fixtures for all variables of the group, pinning their uuid names
	so var(--<uuid>) references in blocks survive the round-trip."""
	for var in frappe.get_all(
		"Builder Variable",
		filters={"group": group},
		fields=["name", "variable_name", "type", "value", "dark_value", "group"],
	):
		var_config = {
			"doctype": "Builder Variable",
			"name": var.name,
			"variable_name": var.variable_name,
			"type": var.type,
			"value": var.value,
			"dark_value": var.dark_value,
			"group": var.group,
		}
		var_dir = os.path.join(variables_path, var.name)
		os.makedirs(var_dir, exist_ok=True)
		with open(os.path.join(var_dir, f"{var.name}.json"), "w", encoding="utf-8") as f:
			f.write(frappe.as_json(var_config, ensure_ascii=False))


def export_template_fonts(fonts, fonts_path, group_folder):
	"""Write User Font fixtures (and their font files) for custom fonts used by
	the group. Fonts without a User Font record (e.g. bundled fonts) are skipped."""
	for font_name in fonts:
		font = frappe.db.get_value(
			"User Font", {"font_name": font_name}, ["name", "font_name", "font_file"], as_dict=True
		)
		if not font:
			continue

		font_file = font.font_file
		if font_file:
			source_path = resolve_asset_source_path(font_file)
			if source_path:
				font_file = copy_file_to_group_assets(source_path, group_folder, "fonts")

		font_config = {
			"doctype": "User Font",
			"name": font.name,
			"font_name": font.font_name,
			"font_file": font_file,
		}
		export_name = frappe.scrub(font.font_name)
		font_dir = os.path.join(fonts_path, export_name)
		os.makedirs(font_dir, exist_ok=True)
		with open(os.path.join(font_dir, f"{export_name}.json"), "w", encoding="utf-8") as f:
			f.write(frappe.as_json(font_config, ensure_ascii=False))


def ensure_template_preview(page_doc):
	"""Generate the page preview image if it isn't on disk yet, and return the
	public preview url whenever the .webp exists (so the fixture's preview field
	is correct even when generation is skipped). Preview generation needs an
	external service, so failures are non-fatal."""
	from builder.utils import get_builder_page_preview_file_paths

	public_path, local_path = get_builder_page_preview_file_paths(page_doc)
	if not os.path.exists(local_path):
		try:
			# render explicitly — template pages are unpublished, so they don't
			# resolve through the regular website path resolution
			page_doc.generate_page_preview_image(html=render_template_page(page_doc))
		except Exception:
			frappe.log_error(f"Failed to generate preview for template page {page_doc.name}")
	return public_path if os.path.exists(local_path) else None


def render_template_page(page_doc):
	"""Render an unpublished template page to HTML, like the preview endpoint does."""
	from frappe.utils import set_request

	from builder.builder.doctype.builder_page.builder_page import BuilderPageRenderer

	set_request(method="GET", path=f"/{page_doc.route or ''}")
	frappe.local.request.for_preview = True
	renderer = BuilderPageRenderer(path="")
	renderer.docname = page_doc.name
	renderer.doctype = "Builder Page"
	frappe.local.no_cache = 1
	renderer.init_context()
	response = renderer.render()
	return str(response.data, "utf-8")


def update_template_manifest(group_path, page_names, title=None):
	"""Refresh the pages list in template.json, preserving human-authored
	title/description/preview and page order."""
	manifest_path = os.path.join(group_path, "template.json")
	manifest = {}
	if os.path.exists(manifest_path):
		with open(manifest_path, encoding="utf-8") as f:
			try:
				manifest = json.load(f)
			except ValueError:
				manifest = {}

	manifest.setdefault("title", (title or "").title() or os.path.basename(group_path))
	manifest.setdefault("description", "")

	pages = [
		page
		for page in manifest.get("pages", [])
		if isinstance(page, dict) and page.get("name") in page_names
	]
	known = {page["name"] for page in pages}
	pages += [{"name": name} for name in page_names if name not in known]
	manifest["pages"] = pages

	with open(manifest_path, "w", encoding="utf-8") as f:
		f.write(frappe.as_json(manifest, ensure_ascii=False))


def delete_template_page_fixture(page_doc):
	"""Remove a template page's fixture and assets (dev-mode on_trash). Shared
	components/variables of the group are intentionally left in place."""
	group_folder = frappe.scrub(str(page_doc.template_group))
	group_path = os.path.join(get_templates_root(), group_folder)

	page_dir = os.path.join(group_path, "pages", frappe.scrub(str(page_doc.name)))
	if os.path.exists(page_dir):
		shutil.rmtree(page_dir)

	assets_dir = os.path.join(get_group_assets_root(group_folder), str(page_doc.name))
	if os.path.exists(assets_dir):
		shutil.rmtree(assets_dir)

	pages_path = os.path.join(group_path, "pages")
	if os.path.isdir(pages_path):
		remaining = []
		for fname in sorted(os.listdir(pages_path)):
			page_file = os.path.join(pages_path, fname, f"{fname}.json")
			if os.path.isfile(page_file):
				with open(page_file, encoding="utf-8") as f:
					remaining.append(frappe.parse_json(f.read()).get("name") or fname)
		update_template_manifest(group_path, remaining)


# ---------------------------------------------------------------------------
# manifest / assets helpers
# ---------------------------------------------------------------------------
def get_group_manifest(group_folder):
	manifest_path = os.path.join(get_templates_root(), group_folder, "template.json")
	if not os.path.exists(manifest_path):
		return {}
	with open(manifest_path, encoding="utf-8") as f:
		try:
			return json.load(f)
		except ValueError:
			return {}


def get_all_group_manifests():
	"""{group_folder: manifest} for all template groups on disk."""
	templates_root = get_templates_root()
	if not os.path.isdir(templates_root):
		return {}
	return {
		group: get_group_manifest(group)
		for group in sorted(os.listdir(templates_root))
		if os.path.isdir(os.path.join(templates_root, group)) and not group.startswith((".", "_"))
	}


def copy_block_assets(blocks, group_folder, subpath):
	"""Copy /files/* assets referenced by a block tree into the group's
	committed assets and rewrite srcs to /builder_assets/<group>/<subpath>/."""
	if not isinstance(blocks, list):
		blocks = [blocks]
	for block in blocks:
		if not isinstance(block, dict):
			continue
		if block.get("element") in ("img", "video"):
			attributes = block.get("attributes") or {}
			new_src = copy_file_url_to_group_assets(attributes.get("src"), group_folder, subpath)
			if new_src:
				attributes["src"] = new_src
		copy_block_assets(block.get("children") or [], group_folder, subpath)


def copy_file_url_to_group_assets(file_url, group_folder, subpath):
	"""Copy a site /files/* url into the group assets folder; returns the new
	public url, or None if the url doesn't point to a copyable site file."""
	if not file_url or not isinstance(file_url, str):
		return None

	site_url = get_url()
	if file_url.startswith(f"{site_url}/files"):
		file_url = file_url.split(site_url)[1]
	if not file_url.startswith("/files/"):
		return None

	file_url = unquote(file_url)
	file_name = frappe.db.get_value("File", {"file_url": file_url}, "name")
	if not file_name:
		return None

	source_path = frappe.get_doc("File", file_name).get_full_path()
	return copy_file_to_group_assets(source_path, group_folder, subpath, os.path.basename(file_url))


def copy_file_to_group_assets(source_path, group_folder, subpath, filename=None):
	filename = filename or os.path.basename(source_path)
	dest_dir = os.path.join(get_group_assets_root(group_folder), subpath)
	os.makedirs(dest_dir, exist_ok=True)
	shutil.copy2(source_path, os.path.join(dest_dir, filename))
	return f"/builder_assets/{group_folder}/{subpath}/{filename}"


def resolve_asset_source_path(file_url):
	"""Resolve a /files/* or /builder_assets/* url to a local filesystem path."""
	if not file_url or not isinstance(file_url, str):
		return None
	if file_url.startswith("/files/"):
		path = os.path.join(frappe.local.site_path, "public", file_url.lstrip("/"))
	elif file_url.startswith("/builder_assets/"):
		path = os.path.join(frappe.get_app_path("builder"), "www", file_url.lstrip("/"))
	else:
		return None
	return path if os.path.exists(path) else None
