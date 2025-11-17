import glob
import inspect
import json
import os
import re
import shutil
import socket
from dataclasses import dataclass
from os.path import join
from urllib.parse import unquote, urlparse

import frappe
from frappe.modules.export_file import export_to_files
from frappe.modules.import_file import import_file_by_path
from frappe.utils import get_site_base_path, get_site_path, get_url
from frappe.utils.safe_exec import (
	SERVER_SCRIPT_FILE_PREFIX,
	FrappeTransformer,
	NamespaceDict,
	get_python_builtins,
	get_safe_globals,
	is_safe_exec_enabled,
	safe_exec,
	safe_exec_flags,
)
from RestrictedPython import compile_restricted
from werkzeug.routing import Rule


@dataclass
class BlockDataKey:
	key: str
	property: str
	type: str


class Block:
	blockId: str = ""
	from typing import ClassVar

	children: ClassVar[list["Block"]] = []
	baseStyles: ClassVar[dict] = {}
	rawStyles: ClassVar[dict] = {}
	mobileStyles: ClassVar[dict] = {}
	tabletStyles: ClassVar[dict] = {}
	attributes: ClassVar[dict] = {}
	classes: ClassVar[list[str]] = []
	dataKey: BlockDataKey | None = None
	blockName: str | None = None
	element: str | None = None
	draggable: bool = False
	innerText: str | None = None
	innerHTML: str | None = None
	extendedFromComponent: str | None = None
	originalElement: str | None = None
	isChildOfComponent: str | None = None
	referenceBlockId: str | None = None
	isRepeaterBlock: bool = False
	visibilityCondition: str | None = None
	elementBeforeConversion: str | None = None
	customAttributes: dict | None = None
	dynamicValues: list[BlockDataKey] | None = None

	def __init__(self, **kwargs) -> None:
		for key, value in kwargs.items():
			if key == "children":
				value = [Block(**b) if b and isinstance(b, dict) else None for b in (value or [])]
			setattr(self, key, value)

	def as_dict(self):
		return {
			"blockId": self.blockId,
			"children": [child.as_dict() for child in self.children] if self.children else None,
			"baseStyles": self.baseStyles,
			"rawStyles": self.rawStyles,
			"mobileStyles": self.mobileStyles,
			"tabletStyles": self.tabletStyles,
			"attributes": self.attributes,
			"classes": self.classes,
			"dataKey": self.dataKey,
			"blockName": self.blockName,
			"element": self.element,
			"draggable": self.draggable,
			"innerText": self.innerText,
			"innerHTML": self.innerHTML,
			"extendedFromComponent": self.extendedFromComponent,
			"originalElement": self.originalElement,
			"isChildOfComponent": self.isChildOfComponent,
			"referenceBlockId": self.referenceBlockId,
			"isRepeaterBlock": self.isRepeaterBlock,
			"visibilityCondition": self.visibilityCondition,
			"elementBeforeConversion": self.elementBeforeConversion,
			"customAttributes": self.customAttributes,
			"dynamicValues": self.dynamicValues,
		}


def get_doc_as_dict(doctype, name):
	assert isinstance(doctype, str)
	assert isinstance(name, str)
	return frappe.get_doc(doctype, name).as_dict()


def get_cached_doc_as_dict(doctype, name):
	assert isinstance(doctype, str)
	assert isinstance(name, str)
	return frappe.get_cached_doc(doctype, name).as_dict()


def make_safe_get_request(url, **kwargs):
	parsed = urlparse(url)
	parsed_ip = socket.gethostbyname(parsed.hostname)
	if parsed_ip.startswith(("127", "10", "192", "172")):
		return

	return frappe.integrations.utils.make_get_request(url, **kwargs)


def safe_get_list(*args, **kwargs):
	if args and len(args) > 1 and isinstance(args[1], list):
		args = list(args)
		args[1] = remove_unsafe_fields(args[1])

	fields = kwargs.get("fields", [])
	if fields:
		kwargs["fields"] = remove_unsafe_fields(fields)

	return frappe.db.get_list(
		*args,
		**kwargs,
	)


def safe_get_all(*args, **kwargs):
	kwargs["ignore_permissions"] = True
	if "limit_page_length" not in kwargs:
		kwargs["limit_page_length"] = 0

	return safe_get_list(*args, **kwargs)


def remove_unsafe_fields(fields):
	return [f for f in fields if "(" not in f]


def get_safer_globals():
	safe_globals = get_safe_globals()

	form_dict = getattr(frappe.local, "form_dict", frappe._dict())

	if "_" in form_dict:
		del frappe.local.form_dict["_"]

	out = NamespaceDict(
		json=safe_globals["json"],
		as_json=frappe.as_json,
		dict=safe_globals["dict"],
		args=form_dict,
		frappe=NamespaceDict(
			db=NamespaceDict(
				count=frappe.db.count,
				exists=frappe.db.exists,
				get_all=safe_get_all,
				get_list=safe_get_list,
				get_single_value=frappe.db.get_single_value,
			),
			form_dict=form_dict,
			make_get_request=make_safe_get_request,
			get_doc=get_doc_as_dict,
			get_cached_doc=get_cached_doc_as_dict,
			_=frappe._,
			session=safe_globals["frappe"]["session"],
		),
	)

	out._write_ = safe_globals["_write_"]
	out._getitem_ = safe_globals["_getitem_"]
	out._getattr_ = safe_globals["_getattr_"]
	out._getiter_ = safe_globals["_getiter_"]
	out._iter_unpack_sequence_ = safe_globals["_iter_unpack_sequence_"]

	# add common python builtins
	out.update(get_python_builtins())

	return out


def safer_exec(
	script: str,
	_globals: dict | None = None,
	_locals: dict | None = None,
	*,
	script_filename: str | None = None,
):
	exec_globals = get_safer_globals()
	if _globals:
		exec_globals.update(_globals)

	filename = SERVER_SCRIPT_FILE_PREFIX
	if script_filename:
		filename += f": {frappe.scrub(script_filename)}"

	with safe_exec_flags():
		# execute script compiled by RestrictedPython
		exec(
			compile_restricted(script, filename=filename, policy=FrappeTransformer),
			exec_globals,
			_locals,
		)

	return exec_globals, _locals


def sync_page_templates():
	print("Syncing Builder Components")
	builder_component_path = frappe.get_module_path("builder", "builder_component")
	make_records(builder_component_path)

	print("Syncing Builder Scripts")
	builder_script_path = frappe.get_module_path("builder", "builder_script")
	make_records(builder_script_path)

	print("Syncing Builder Page Templates")
	builder_page_template_path = frappe.get_module_path("builder", "builder_page_template")
	make_records(builder_page_template_path)


def sync_block_templates():
	print("Syncing Builder Block Templates")
	builder_block_template_path = frappe.get_module_path("builder", "builder_block_template")
	make_records(builder_block_template_path)


def sync_builder_variables():
	print("Syncing Builder Builder Variables")
	builder_variable_path = frappe.get_module_path("builder", "builder_variable")
	make_records(builder_variable_path)


def make_records(path):
	if not os.path.isdir(path):
		return
	for fname in os.listdir(path):
		if os.path.isdir(join(path, fname)) and fname != "__pycache__":
			import_file_by_path(f"{path}/{fname}/{fname}.json")


# def generate_tailwind_css_file_from_html(html):
# 	# execute tailwindcss cli command to generate css file
# 	# create temp folder
# 	temp_folder = os.path.join(get_site_base_path(), "temp")
# 	if os.path.exists(temp_folder):
# 		shutil.rmtree(temp_folder)
# 	os.mkdir(temp_folder)

# 	# create temp html file
# 	temp_html_file_path = os.path.join(temp_folder, "temp.html")
# 	with open(temp_html_file_path, "w") as f:
# 		f.write(html)

# 	# place tailwind.css file in public folder
# 	tailwind_css_file_path = os.path.join(get_site_path(), "public", "files", "tailwind.css")

# 	# create temp config file
# 	temp_config_file_path = os.path.join(temp_folder, "tailwind.config.js")
# 	with open(temp_config_file_path, "w") as f:
# 		f.write("module.exports = {content: ['./temp.html']}")

# 	# run tailwindcss cli command in production mode
# 	subprocess.run(
# 		["npx", "tailwindcss", "-o", tailwind_css_file_path, "--config", temp_config_file_path, "--minify"]
# 	)


def copy_img_to_asset_folder(block, page_doc):
	# Helper function to safely get attribute from block (dict or object)
	def safe_get(obj, attr, default=None):
		if isinstance(obj, dict):
			return obj.get(attr, default)
		else:
			return getattr(obj, attr, default)

	# Convert dict to frappe._dict for consistent access
	if isinstance(block, dict):
		block = frappe._dict(block)
		# Also convert children to frappe._dict for consistent access
		children = block.get("children", [])
		if children and isinstance(children, list):
			block.children = [frappe._dict(child) if isinstance(child, dict) else child for child in children]

	# Get element safely
	element = safe_get(block, "element")

	if element == "img":
		# Get attributes safely
		attributes = safe_get(block, "attributes")
		src = None

		if attributes:
			src = safe_get(attributes, "src")

		site_url = get_url()

		if src and (src.startswith(f"{site_url}/files") or src.startswith("/files")):
			# find file doc
			if src.startswith(f"{site_url}/files"):
				src = src.split(f"{site_url}")[1]
			# url decode
			src = unquote(src)
			files = frappe.get_all("File", filters={"file_url": src}, fields=["name"])
			if files:
				_file = frappe.get_doc("File", files[0].name)
				# copy physical file to new location
				assets_folder_path = get_template_assets_folder_path(page_doc)
				shutil.copy(_file.get_full_path(), assets_folder_path)

			new_src = f"/builder_assets/{page_doc.name}/{src.split('/')[-1]}"
			if attributes:
				if isinstance(attributes, dict):
					attributes["src"] = new_src
				else:
					attributes.src = new_src

	# Process children safely
	children = safe_get(block, "children", [])
	for child in children or []:
		copy_img_to_asset_folder(child, page_doc)


def get_template_assets_folder_path(page_doc):
	path = os.path.join(frappe.get_app_path("builder"), "www", "builder_assets", page_doc.name)
	if not os.path.exists(path):
		os.makedirs(path)
	return path


def get_builder_page_preview_file_paths(page_doc):
	public_path, public_path = None, None
	if page_doc.is_template:
		local_path = os.path.join(get_template_assets_folder_path(page_doc), "preview.webp")
		public_path = f"/builder_assets/{page_doc.name}/preview.webp"
	else:
		file_name = f"{page_doc.name}-preview.webp"
		local_path = os.path.join(frappe.local.site_path, "public", "files", file_name)
		random_hash = frappe.generate_hash(length=5)
		public_path = f"/files/{file_name}?v={random_hash}"
	return public_path, local_path


def is_component_used(blocks, component_id):
	blocks = frappe.parse_json(blocks)
	if not isinstance(blocks, list):
		blocks = [blocks]

	for block in blocks:
		if not block:
			continue
		if block.get("extendedFromComponent") == component_id:
			return True
		elif block.get("children"):
			return is_component_used(block.get("children"), component_id)

	return False


def escape_single_quotes(text):
	return (text or "").replace("'", "\\'")


def camel_case_to_kebab_case(text, remove_spaces=False):
	if not text:
		return ""
	text = re.sub(r"(?<!^)(?=[A-Z])", "-", text).lower()
	if remove_spaces:
		text = text.replace(" ", "")
	return text


def execute_script(script, _locals, script_filename):
	if is_safe_exec_enabled():
		safe_exec(script, None, _locals, script_filename=script_filename)
	else:
		safer_exec(script, None, _locals, script_filename=script_filename)


def get_dummy_blocks():
	return [
		{
			"element": "div",
			"extendedFromComponent": "component-1",
			"children": [
				{
					"element": "div",
					"children": [
						{
							"element": "div",
							"extendedFromComponent": "component-2",
							"children": [],
						},
					],
				},
			],
		},
	]


def clean_data(data):
	if isinstance(data, dict):
		return {
			k: clean_data(v)
			for k, v in data.items()
			if not inspect.isbuiltin(v) and not inspect.isfunction(v) and not inspect.ismethod(v)
		}
	elif isinstance(data, list):
		return [clean_data(i) for i in data]
	return data


class ColonRule(Rule):
	def __init__(self, string, *args, **kwargs):
		# Replace ':name' with '<name>' so Werkzeug can process it
		string = self.convert_colon_to_brackets(string)
		super().__init__(string, *args, **kwargs)

	@staticmethod
	def convert_colon_to_brackets(string):
		return re.sub(r":([a-zA-Z0-9_-]+)", r"<\1>", string)


def add_composite_index_to_web_page_view():
	"""
	Add a composite index to the Web Page View table.
	This is used to speed up queries that filter by creation, is_unique, and path.
	"""
	frappe.db.add_index("Web Page View", ["creation", "is_unique", "path"])


def split_styles(styles):
	if not styles:
		return {"regular": {}, "state": {}}

	return {
		"regular": {k: v for k, v in styles.items() if ":" not in k},
		"state": {k: v for k, v in styles.items() if ":" in k},
	}


def copy_assets_from_blocks(blocks, assets_path):
	if not isinstance(blocks, list):
		blocks = [blocks]

	for block in blocks:
		if isinstance(block, dict):
			process_block_assets(block, assets_path)
			children = block.get("children")
			if children and isinstance(children, list):
				copy_assets_from_blocks(children, assets_path)


def process_block_assets(block, assets_path):
	"""Process assets for a single block"""
	if block.get("element") in ("img", "video"):
		src = block.get("attributes", {}).get("src")
		if src:
			new_location = copy_asset_file(src, assets_path)
			if new_location:
				block["attributes"]["src"] = new_location


def copy_asset_file(file_url, assets_path):
	"""Copy a file from the source to assets directory and return new public path"""
	if not file_url or not isinstance(file_url, str):
		return None

	try:
		if file_url.startswith("/files/"):
			return copy_from_site_files(file_url, assets_path)
		elif file_url.startswith("/builder_assets/"):
			return copy_from_builder_assets(file_url, assets_path)
	except Exception as e:
		frappe.log_error(f"Failed to copy asset {file_url}: {e!s}")
	return None


def copy_from_site_files(file_url, assets_path):
	"""Copy file from site files directory"""
	source_path = os.path.join(frappe.local.site_path, "public", file_url.lstrip("/"))
	if os.path.exists(source_path):
		return copy_file_to_assets(source_path, file_url, assets_path)
	return None


def copy_from_builder_assets(file_url, assets_path):
	"""Copy file from builder assets directory"""
	source_path = os.path.join(frappe.get_app_path("builder"), "www", file_url.lstrip("/"))
	if os.path.exists(source_path):
		return copy_file_to_assets(source_path, file_url, assets_path)
	return None


def copy_file_to_assets(source_path, file_url, assets_path):
	"""Copy file to assets directory and return public path"""
	filename = os.path.basename(file_url)
	dest_path = os.path.join(assets_path, filename)
	shutil.copy2(source_path, dest_path)
	return f"/builder_assets/page_{os.path.basename(assets_path)}/{filename}"


def extract_components_from_blocks(blocks):
	"""Extract component IDs from blocks recursively"""
	components = set()
	if not isinstance(blocks, list):
		blocks = [blocks]

	for block in blocks:
		if isinstance(block, dict):
			if block.get("extendedFromComponent"):
				component_doc = frappe.get_cached_doc("Builder Component", block["extendedFromComponent"])
				if component_doc:
					components.update(
						extract_components_from_blocks(frappe.parse_json(component_doc.block or "{}"))
					)
				components.add(block["extendedFromComponent"])
			children = block.get("children")
			if children and isinstance(children, list):
				components.update(extract_components_from_blocks(children))

	return components


def export_client_scripts(page_doc, client_scripts_path):
	"""Export client scripts for a page"""
	from frappe.modules.export_file import strip_default_fields

	for script_row in page_doc.client_scripts:
		script_doc = frappe.get_doc("Builder Client Script", script_row.builder_script)
		script_config = script_doc.as_dict(no_nulls=True)
		script_config = strip_default_fields(script_doc, script_config)
		fname = frappe.scrub(str(script_doc.name))
		# ensure the target directory exists before writing the file
		script_dir = os.path.join(client_scripts_path, fname)
		os.makedirs(script_dir, exist_ok=True)
		script_file_path = os.path.join(script_dir, f"{fname}.json")

		with open(script_file_path, "w", encoding="utf-8") as f:
			f.write(frappe.as_json(script_config, ensure_ascii=False))


def export_components(components, components_path, assets_path):
	"""Export components to files"""
	for component_id in components:
		try:
			component_doc = frappe.get_doc("Builder Component", component_id)
			# replace assets in component blocks
			component_blocks = frappe.parse_json(component_doc.block or "[]")
			copy_assets_from_blocks(component_blocks, assets_path)
			component_doc.block = frappe.as_json(component_blocks)

			# Replace forward slashes with underscores to create valid directory names
			safe_component_name = frappe.scrub(component_doc.component_name).replace("/", "_")
			component_dir = os.path.join(components_path, safe_component_name)
			os.makedirs(component_dir, exist_ok=True)
			component_file_path = os.path.join(component_dir, f"{safe_component_name}.json")

			with open(component_file_path, "w") as f:
				f.write(frappe.as_json(component_doc.as_dict()))
		except Exception as e:
			print(e)
			frappe.log_error(f"Failed to export component {component_id}: {e!s}")


def create_export_directories(app_path, export_name):
	"""Create necessary directories for export and return paths"""
	paths = get_export_paths(app_path, export_name)
	setup_assets_symlink(app_path, paths["assets_path"])
	for path in paths.values():
		os.makedirs(path, exist_ok=True)

	return paths


def get_export_paths(app_path, export_name):
	"""Get all export directory paths"""
	builder_files_path = os.path.join(app_path, "builder_files")
	pages_path = os.path.join(builder_files_path, "pages")

	return {
		"page_path": os.path.join(pages_path, export_name),
		"assets_path": os.path.join(builder_files_path, "assets"),
		"client_scripts_path": os.path.join(builder_files_path, "client_scripts"),
		"components_path": os.path.join(builder_files_path, "components"),
		"builder_files_path": builder_files_path,
		"pages_path": pages_path,
	}


def setup_assets_symlink(app_path, assets_path):
	symlink_path = os.path.join(app_path, "www", "builder_assets", "page_assets")
	os.makedirs(os.path.dirname(symlink_path), exist_ok=True)
	os.makedirs(assets_path, exist_ok=True)
	if not os.path.islink(symlink_path):
		remove_existing_path(symlink_path)
		os.symlink(assets_path, symlink_path)


def remove_existing_path(path):
	if os.path.exists(path):
		if os.path.isdir(path):
			shutil.rmtree(path)
		else:
			os.remove(path)
