import glob
import inspect
import os
import re
import shutil
import socket
import subprocess
from dataclasses import dataclass
from os.path import join
from urllib.parse import unquote, urlparse

import frappe
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
	children: list["Block"] = None
	baseStyles: dict = None
	rawStyles: dict = None
	mobileStyles: dict = None
	tabletStyles: dict = None
	attributes: dict = None
	classes: list[str] = None
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
	if parsed_ip.startswith("127", "10", "192", "172"):
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


def copy_img_to_asset_folder(block: Block, page_doc):
	if block.get("element") == "img":
		src = block.get("attributes", {}).get("src")
		site_url = get_url()

		if src and (src.startswith(f"{site_url}/files") or src.startswith("/files")):
			# find file doc
			if src.startswith(f"{site_url}/files"):
				src = src.split(f"{site_url}")[1]
			# url decode
			src = unquote(src)
			print(f"src: {src}")
			files = frappe.get_all("File", filters={"file_url": src}, fields=["name"])
			print(f"files: {files}")
			if files:
				_file = frappe.get_doc("File", files[0].name)
				# copy physical file to new location
				assets_folder_path = get_template_assets_folder_path(page_doc)
				shutil.copy(_file.get_full_path(), assets_folder_path)
			block["attributes"]["src"] = f"/builder_assets/{page_doc.name}/{src.split('/')[-1]}"
	for child in block.get("children", []) or []:
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
