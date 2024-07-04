# Copyright (c) 2023, asdf and contributors
# For license information, please see license.txt

import contextlib
import os
import re
import shutil
from io import BytesIO
from urllib.parse import unquote

import bs4 as bs
import frappe
import frappe.utils
import requests
from frappe.core.doctype.file.file import get_local_image
from frappe.core.doctype.file.utils import delete_file
from frappe.model.document import Document
from frappe.modules.export_file import export_to_files
from frappe.utils.caching import redis_cache
from frappe.utils.jinja import render_template
from frappe.utils.safe_exec import is_safe_exec_enabled, safe_exec
from frappe.utils.telemetry import capture
from frappe.website.page_renderers.document_page import DocumentPage
from frappe.website.path_resolver import evaluate_dynamic_routes
from frappe.website.path_resolver import resolve_path as original_resolve_path
from frappe.website.serve import get_response_content
from frappe.website.utils import clear_cache
from frappe.website.website_generator import WebsiteGenerator
from jinja2.exceptions import TemplateSyntaxError
from PIL import Image
from werkzeug.routing import Rule

from builder.html_preview_image import generate_preview
from builder.utils import safer_exec

MOBILE_BREAKPOINT = 576
TABLET_BREAKPOINT = 768
DESKTOP_BREAKPOINT = 1024


class BuilderPageRenderer(DocumentPage):
	def can_render(self):
		if page := find_page_with_path(self.path):
			self.doctype = "Builder Page"
			self.docname = page
			return True

		for d in get_web_pages_with_dynamic_routes():
			if evaluate_dynamic_routes([Rule(f"/{d.route}", endpoint=d.name)], self.path):
				self.doctype = "Builder Page"
				self.docname = d.name
				return True

		return False


class BuilderPage(WebsiteGenerator):
	def add_comment(
		self,
		comment_type="Comment",
		text=None,
		comment_email=None,
		comment_by=None,
	):
		if comment_type in ["Attachment Removed", "Attachment"]:
			return
		super().add_comment(
			comment_type=comment_type,
			text=text,
			comment_email=comment_email,
			comment_by=comment_by,
		)

	def before_insert(self):
		if isinstance(self.blocks, list):
			self.blocks = frappe.as_json(self.blocks, indent=None)
		if isinstance(self.draft_blocks, list):
			self.draft_blocks = frappe.as_json(self.draft_blocks, indent=None)
		if not self.blocks:
			self.blocks = "[]"
		if self.preview:
			self.flags.skip_preview = True
		else:
			self.preview = "/assets/builder/images/fallback.png"
		if not self.page_title:
			self.page_title = "My Page"
		self.route = (
			f"pages/{camel_case_to_kebab_case(self.page_title, True)}-{frappe.generate_hash(length=4)}"
		)

	def on_update(self):
		if self.has_value_changed("dynamic_route") or self.has_value_changed("route"):
			get_web_pages_with_dynamic_routes.clear_cache()
			find_page_with_path.clear_cache()

		if self.has_value_changed("published") and not self.published:
			find_page_with_path.clear_cache()
			clear_cache(self.route)
			# if this is homepage then clear homepage from builder settings
			if frappe.get_cached_value("Builder Settings", None, "home_page") == self.route:
				frappe.db.set_value("Builder Settings", None, "home_page", None)

		if frappe.conf.developer_mode and self.is_template:
			# move all assets to www/builder_assets/{page_name}
			if self.draft_blocks:
				self.publish()
			if not self.template_name:
				self.template_name = self.page_title

			blocks = frappe.parse_json(self.blocks)
			for block in blocks:
				copy_img_to_asset_folder(block, self)
			self.db_set("draft_blocks", None)
			self.db_set("blocks", frappe.as_json(blocks, indent=None))
			self.reload()
			export_to_files(
				record_list=[["Builder Page", self.name, "builder_page_template"]], record_module="builder"
			)

			components = set()

			def get_component(block):
				if block.get("extendedFromComponent"):
					component = block.get("extendedFromComponent")
					components.add(component)
					# export nested components as well
					component_doc = frappe.get_cached_doc("Builder Component", component)
					if component_doc.block:
						component_block = frappe.parse_json(component_doc.block)
						get_component(component_block)
				for child in block.get("children", []):
					get_component(child)

			for block in blocks:
				get_component(block)

			if components:
				export_to_files(
					record_list=[["Builder Component", c, "builder_component"] for c in components],
					record_module="builder",
				)

	def on_trash(self):
		if self.is_template and frappe.conf.developer_mode:
			from frappe.modules import scrub

			page_template_folder = os.path.join(
				frappe.get_app_path("builder"), "builder", "builder_page_template", scrub(self.name)
			)
			if os.path.exists(page_template_folder):
				shutil.rmtree(page_template_folder)
			assets_path = get_template_assets_folder_path(self)
			if os.path.exists(assets_path):
				shutil.rmtree(assets_path)

	def autoname(self):
		if not self.name:
			self.name = f"page-{frappe.generate_hash(length=8)}"

	@frappe.whitelist()
	def publish(self, **kwargs):
		frappe.form_dict.update(kwargs)
		self.published = 1
		if self.draft_blocks:
			self.blocks = self.draft_blocks
			self.draft_blocks = None
		self.save()
		frappe.enqueue_doc(
			self.doctype,
			self.name,
			"generate_page_preview_image",
			queue="short",
		)
		capture("page_published", "builder", properties={"page": self.name})

		return self.route

	website = frappe._dict(
		template="templates/generators/webpage.html",
		condition_field="published",
		page_title_field="page_title",
	)

	def get_context(self, context):
		# delete default favicon
		del context.favicon

		page_data = self.get_page_data()
		if page_data.get("title"):
			context.title = page_data.get("page_title")

		blocks = self.blocks
		context.preview = frappe.flags.show_preview

		if self.dynamic_route or page_data:
			context.no_cache = 1

		if frappe.flags.show_preview and self.draft_blocks:
			blocks = self.draft_blocks

		content, style, fonts = get_block_html(blocks)
		context.fonts = fonts
		context.content = content
		context.style = render_template(style, page_data)
		builder_path = frappe.conf.builder_path or "builder"
		context.editor_link = f"/{builder_path}/page/{self.name}"

		if self.dynamic_route and hasattr(frappe.local, "request"):
			context.base_url = frappe.utils.get_url(frappe.local.request.path or self.route)
		else:
			context.base_url = frappe.utils.get_url(self.route)

		self.set_style_and_script(context)
		context.update(page_data)
		self.set_meta_tags(context=context, page_data=page_data)
		self.set_favicon(context)

		try:
			context["content"] = render_template(context.content, context)
		except TemplateSyntaxError:
			raise

	def set_meta_tags(self, context, page_data=None):
		if not page_data:
			page_data = {}

		metatags = {
			"title": self.page_title or "My Page",
			"description": self.meta_description or self.page_title,
			"image": self.meta_image or self.preview,
		}
		metatags.update(page_data.get("metatags", {}))
		context.metatags = metatags

	def set_favicon(self, context):
		if not context.get("favicon"):
			context.favicon = self.favicon
		if not context.get("favicon"):
			context.favicon = frappe.get_cached_value("Builder Settings", None, "favicon")

	def is_component_used(self, component_id):
		if self.blocks and is_component_used(self.blocks, component_id):
			return True
		elif self.draft_blocks and is_component_used(self.draft_blocks, component_id):
			return True

	def set_style_and_script(self, context):
		for script in self.get("client_scripts", []):
			script_doc = frappe.get_cached_doc("Builder Client Script", script.builder_script)
			if script_doc.script_type == "JavaScript":
				context.setdefault("scripts", []).append(script_doc.public_url)
			else:
				context.setdefault("styles", []).append(script_doc.public_url)

		builder_settings = frappe.get_cached_doc("Builder Settings", "Builder Settings")
		if builder_settings.script:
			context.setdefault("scripts", []).append(builder_settings.script_public_url)
		if builder_settings.style:
			context.setdefault("styles", []).append(builder_settings.style_public_url)

	@frappe.whitelist()
	def get_page_data(self, args=None):
		if args:
			args = frappe.parse_json(args)
			frappe.form_dict.update(args)
		page_data = frappe._dict()
		if self.page_data_script:
			_locals = dict(data=frappe._dict())
			if is_safe_exec_enabled():
				safe_exec(self.page_data_script, None, _locals, script_filename=self.name)
			else:
				safer_exec(self.page_data_script, None, _locals, script_filename=self.name)
			page_data.update(_locals["data"])
		return page_data

	def generate_page_preview_image(self, html=None):
		public_path, local_path = get_builder_page_preview_paths(self)
		generate_preview(
			html or get_response_content(self.route),
			local_path,
		)
		self.db_set("preview", public_path, commit=True, update_modified=False)


def get_block_html(blocks):
	blocks = frappe.parse_json(blocks)
	if not isinstance(blocks, list):
		blocks = [blocks]
	soup = bs.BeautifulSoup("", "html.parser")
	style_tag = soup.new_tag("style")
	font_map = {}

	def get_html(blocks, soup):
		html = ""

		def get_tag(block, soup, data_key=None):
			block = extend_with_component(block)
			set_dynamic_content_placeholder(block, data_key)
			element = block.get("originalElement") or block.get("element")

			if not element:
				return ""

			classes = block.get("classes", [])
			if element in (
				"span",
				"h1",
				"p",
				"b",
				"h2",
				"h3",
				"h4",
				"h5",
				"h6",
				"label",
				"a",
			):
				classes.insert(0, "__text_block__")

			# temp fix: since p inside p is illegal
			if element in ["p", "__raw_html__"]:
				element = "div"

			tag = soup.new_tag(element)
			tag.attrs = block.get("attributes", {})

			customAttributes = block.get("customAttributes", {})
			if customAttributes:
				for key, value in customAttributes.items():
					tag[key] = value

			if block.get("baseStyles", {}):
				style_class = f"frappe-builder-{frappe.generate_hash(length=8)}"
				base_styles = block.get("baseStyles", {})
				mobile_styles = block.get("mobileStyles", {})
				tablet_styles = block.get("tabletStyles", {})
				set_fonts([base_styles, mobile_styles, tablet_styles], font_map)
				append_style(block.get("baseStyles", {}), style_tag, style_class)
				plain_styles = {k: v for k, v in block.get("rawStyles", {}).items() if ":" not in k}
				state_styles = {k: v for k, v in block.get("rawStyles", {}).items() if ":" in k}
				append_style(plain_styles, style_tag, style_class)
				append_state_style(state_styles, style_tag, style_class)
				append_style(
					block.get("tabletStyles", {}),
					style_tag,
					style_class,
					device="tablet",
				)
				append_style(
					block.get("mobileStyles", {}),
					style_tag,
					style_class,
					device="mobile",
				)
				classes.insert(0, style_class)

			tag.attrs["class"] = get_class(classes)

			innerContent = block.get("innerHTML")
			if innerContent:
				inner_soup = bs.BeautifulSoup(innerContent, "html.parser")
				set_fonts_from_html(inner_soup, font_map)
				tag.append(inner_soup)

			if block.get("isRepeaterBlock") and block.get("children") and block.get("dataKey"):
				_key = block.get("dataKey").get("key")
				if data_key:
					_key = f"{data_key}.{_key}"

				item_key = f"key_{block.get('blockId')}"
				tag.append(f"{{% for {item_key} in {_key} %}}")
				tag.append(get_tag(block.get("children")[0], soup, item_key))
				tag.append("{% endfor %}")
			else:
				for child in block.get("children", []):
					if child.get("visibilityCondition"):
						key = child.get("visibilityCondition")
						if data_key:
							key = f"{data_key}.{key}"
						tag.append(f"{{% if {key} %}}")
					tag.append(get_tag(child, soup, data_key=data_key))
					if child.get("visibilityCondition"):
						tag.append("{% endif %}")

			if element == "body":
				tag.append("{% include 'templates/generators/webpage_scripts.html' %}")

			return tag

		for block in blocks:
			html += str(get_tag(block, soup))

		return html, str(style_tag), font_map

	data = get_html(blocks, soup)
	return data


def get_style(style_obj):
	return (
		"".join(
			f"{camel_case_to_kebab_case(key)}: {value};"
			for key, value in style_obj.items()
			if value is not None and value != ""
		)
		if style_obj
		else ""
	)


def get_class(class_list):
	return " ".join(class_list)


def camel_case_to_kebab_case(text, remove_spaces=False):
	if not text:
		return ""
	text = re.sub(r"(?<!^)(?=[A-Z])", "-", text).lower()
	if remove_spaces:
		text = text.replace(" ", "")
	return text


def append_style(style_obj, style_tag, style_class, device="desktop"):
	style = get_style(style_obj)
	if not style:
		return

	style_string = f".{style_class} {{ {style} }}"
	if device == "mobile":
		style_string = f"@media only screen and (max-width: {MOBILE_BREAKPOINT}px) {{ {style_string} }}"
	elif device == "tablet":
		style_string = f"@media only screen and (max-width: {DESKTOP_BREAKPOINT - 1}px) {{ {style_string} }}"
	style_tag.append(style_string)


def append_state_style(style_obj, style_tag, style_class):
	for key, value in style_obj.items():
		state, property = key.split(":", 1)
		style_tag.append(f".{style_class}:{state} {{ {property}: {value} }}")


def set_fonts(styles, font_map):
	for style in styles:
		font = style.get("fontFamily")
		if font:
			if font in font_map:
				if style.get("fontWeight") and style.get("fontWeight") not in font_map[font]["weights"]:
					font_map[font]["weights"].append(style.get("fontWeight"))
					font_map[font]["weights"].sort()
			else:
				font_map[font] = {"weights": [style.get("fontWeight") or "400"]}


def set_fonts_from_html(soup, font_map):
	# get font-family from inline styles
	for tag in soup.find_all(style=True):
		styles = tag.attrs.get("style").split(";")
		for style in styles:
			if "font-family" in style:
				font = style.split(":")[1].strip()
				if font:
					font_map[font] = {"weights": ["400"]}


def extend_with_component(block):
	if block.get("extendedFromComponent"):
		component = frappe.get_cached_value(
			"Builder Component",
			block["extendedFromComponent"],
			["block", "name"],
			as_dict=True,
		)
		component_block = frappe.parse_json(component.block)
		if component_block:
			extend_block(component_block, block)
			block = component_block

	return block


def extend_block(block, overridden_block):
	block["baseStyles"].update(overridden_block["baseStyles"])
	block["mobileStyles"].update(overridden_block["mobileStyles"])
	block["tabletStyles"].update(overridden_block["tabletStyles"])
	block["attributes"].update(overridden_block["attributes"])
	if overridden_block.get("visibilityCondition"):
		block["visibilityCondition"] = overridden_block.get("visibilityCondition")

	if not block.get("customAttributes"):
		block["customAttributes"] = {}
	block["customAttributes"].update(overridden_block.get("customAttributes", {}))

	if not block.get("rawStyles"):
		block["rawStyles"] = {}
	block["rawStyles"].update(overridden_block.get("rawStyles", {}))

	block["classes"].extend(overridden_block["classes"])
	dataKey = overridden_block.get("dataKey", {})
	if not block.get("dataKey"):
		block["dataKey"] = {}
	if dataKey:
		block["dataKey"].update({k: v for k, v in dataKey.items() if v is not None})
	if overridden_block.get("innerHTML"):
		block["innerHTML"] = overridden_block["innerHTML"]
	component_children = block.get("children", [])
	overridden_children = overridden_block.get("children", [])
	for overridden_child in overridden_children:
		component_child = next(
			(
				child
				for child in component_children
				if child.get("blockId")
				in [
					overridden_child.get("blockId"),
					overridden_child.get("referenceBlockId"),
				]
			),
			None,
		)
		if component_child:
			extend_block(component_child, overridden_child)
		else:
			component_children.insert(overridden_children.index(overridden_child), overridden_child)


def set_dynamic_content_placeholder(block, data_key=False):
	block_data_key = block.get("dataKey")
	if block_data_key and block_data_key.get("key"):
		key = f"{data_key}.{block_data_key.get('key')}" if data_key else block_data_key.get("key")
		if data_key:
			# convert a.b to (a or {}).get('b', {})
			# to avoid undefined error in jinja
			keys = key.split(".")
			key = f"({keys[0]} or {{}})"
			for k in keys[1:]:
				key = f"{key}.get('{k}', {{}})"

		_property = block_data_key.get("property")
		_type = block_data_key.get("type")
		if _type == "attribute":
			block["attributes"][
				_property
			] = f"{{{{ {key} or '{escape_single_quotes(block['attributes'].get(_property, ''))}' }}}}"
		elif _type == "style":
			block["baseStyles"][
				_property
			] = f"{{{{ {key} or '{escape_single_quotes(block['baseStyles'].get(_property, ''))}' }}}}"
		elif _type == "key" and not block.get("isRepeaterBlock"):
			block[_property] = f"{{{{ {key} or '{escape_single_quotes(block.get(_property, ''))}' }}}}"


def get_style_file_path():
	# TODO: Redo this, currently it loads the first matching file
	# from frappe.utils import get_url
	# return get_url("/files/tailwind.css")
	import glob

	folder_path = "./assets/builder/frontend/assets/"
	file_pattern = "index.*.css"
	matching_files = glob.glob(f"{folder_path}/{file_pattern}")
	if matching_files:
		return frappe.utils.get_url(matching_files[0].lstrip("."))


def escape_single_quotes(text):
	return (text or "").replace("'", "\\'")


# def generate_tailwind_css_file_from_html(html):
# 	# execute tailwindcss cli command to generate css file
# 	import subprocess
# 	import os
# 	import json
# 	import shutil
# 	from frappe.utils import get_site_path, get_site_base_path

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
# 	subprocess.run(["npx", "tailwindcss", "-o", tailwind_css_file_path, "--config", temp_config_file_path, "--minify"])


@frappe.whitelist()
def get_page_preview_html(page: str, **kwarg) -> str:
	# to load preview without publishing
	frappe.form_dict.update(kwarg)
	renderer = BuilderPageRenderer(path="")
	renderer.docname = page
	renderer.doctype = "Builder Page"
	frappe.flags.show_preview = True
	frappe.local.no_cache = 1
	renderer.init_context()
	response = renderer.render()
	page = frappe.get_cached_doc("Builder Page", page)
	frappe.enqueue_doc(
		page.doctype,
		page.name,
		"generate_page_preview_image",
		html=str(response.data, "utf-8"),
		queue="short",
	)
	return response


@redis_cache(ttl=60 * 60)
def find_page_with_path(route):
	try:
		return frappe.db.get_value("Builder Page", dict(route=route, published=1), "name", cache=True)
	except frappe.DoesNotExistError:
		pass


@redis_cache(ttl=60 * 60)
def get_web_pages_with_dynamic_routes() -> dict[str, str]:
	return frappe.get_all(
		"Builder Page",
		fields=["name", "route", "modified"],
		filters=dict(published=1, dynamic_route=1),
		update={"doctype": "Builder Page"},
	)


def resolve_path(path):
	if find_page_with_path(path):
		return path
	elif evaluate_dynamic_routes(
		[Rule(f"/{d.route}", endpoint=d.name) for d in get_web_pages_with_dynamic_routes()],
		path,
	):
		return path

	return original_resolve_path(path)


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


def copy_img_to_asset_folder(block, self):
	if block.get("element") == "img":
		src = block.get("attributes", {}).get("src")
		site_url = frappe.utils.get_url()

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
				assets_folder_path = get_template_assets_folder_path(self)
				shutil.copy(_file.get_full_path(), assets_folder_path)
			block["attributes"]["src"] = f"/builder_assets/{self.name}/{src.split('/')[-1]}"
	for child in block.get("children", []):
		copy_img_to_asset_folder(child, self)


def get_builder_page_preview_paths(page_doc):
	public_path, public_path = None, None
	if page_doc.is_template:
		local_path = os.path.join(get_template_assets_folder_path(page_doc), "preview.jpeg")
		public_path = f"/builder_assets/{page_doc.name}/preview.jpeg"
	else:
		file_name = f"{page_doc.name}-preview.jpeg"
		local_path = os.path.join(frappe.local.site_path, "public", "files", file_name)
		random_hash = frappe.generate_hash(length=5)
		public_path = f"/files/{file_name}?v={random_hash}"
	return public_path, local_path


def get_template_assets_folder_path(page_doc):
	path = os.path.join(frappe.get_app_path("builder"), "www", "builder_assets", page_doc.name)
	if not os.path.exists(path):
		os.makedirs(path)
	return path


@frappe.whitelist()
def upload_builder_asset():
	from frappe.handler import upload_file

	image_file = upload_file()
	if image_file.file_url.endswith((".png", ".jpeg", ".jpg")) and frappe.get_cached_value(
		"Builder Settings", None, "auto_convert_images_to_webp"
	):
		convert_to_webp(file_doc=image_file)
	return image_file


@frappe.whitelist()
def convert_to_webp(image_url: str | None = None, file_doc: Document | None = None) -> str:
	"""BETA: Convert image to webp format"""

	CONVERTIBLE_IMAGE_EXTENSIONS = ["png", "jpeg", "jpg"]

	def can_convert_image(extn):
		return extn.lower() in CONVERTIBLE_IMAGE_EXTENSIONS

	def get_extension(filename):
		return filename.split(".")[-1].lower()

	def convert_and_save_image(image, path):
		image.save(path, "WEBP")
		return path

	def update_file_doc_with_webp(file_doc, image, extn):
		webp_path = file_doc.get_full_path().replace(extn, "webp")
		convert_and_save_image(image, webp_path)
		delete_file(file_doc.get_full_path())
		file_doc.file_url = f"{file_doc.file_url.replace(extn, 'webp')}"
		file_doc.save()
		return file_doc.file_url

	def create_new_webp_file_doc(file_url, image, extn):
		files = frappe.get_all("File", filters={"file_url": file_url}, fields=["name"], limit=1)
		if files:
			_file = frappe.get_doc("File", files[0].name)
			webp_path = _file.get_full_path().replace(extn, "webp")
			convert_and_save_image(image, webp_path)
			new_file = frappe.copy_doc(_file)
			new_file.file_name = f"{_file.file_name.replace(extn, 'webp')}"
			new_file.file_url = f"{_file.file_url.replace(extn, 'webp')}"
			new_file.save()
			return new_file.file_url
		return file_url

	def handle_image_from_url(image_url):
		image_url = unquote(image_url)
		response = requests.get(image_url)
		image = Image.open(BytesIO(response.content))
		filename = image_url.split("/")[-1]
		extn = get_extension(filename)
		if can_convert_image(extn):
			_file = frappe.get_doc(
				{
					"doctype": "File",
					"file_name": f"{filename.replace(extn, 'webp')}",
					"file_url": f"/files/{filename.replace(extn, 'webp')}",
				}
			)
			webp_path = _file.get_full_path()
			convert_and_save_image(image, webp_path)
			_file.save()
			return _file.file_url
		return image_url

	if not image_url and not file_doc:
		return ""

	if file_doc:
		if file_doc.file_url.startswith("/files"):
			image, filename, extn = get_local_image(file_doc.file_url)
			if can_convert_image(extn):
				return update_file_doc_with_webp(file_doc, image, extn)
		return file_doc.file_url

	if image_url.startswith("/files"):
		image, filename, extn = get_local_image(image_url)
		if can_convert_image(extn):
			return create_new_webp_file_doc(image_url, image, extn)
		return image_url

	if image_url.startswith("/builder_assets"):
		image_path = os.path.abspath(frappe.get_app_path("builder", "www", image_url.lstrip("/")))
		image_path = image_path.replace("_", "-")
		image_path = image_path.replace("/builder-assets", "/builder_assets")

		image = Image.open(image_path)
		extn = get_extension(image_path)
		if can_convert_image(extn):
			webp_path = image_path.replace(extn, "webp")
			convert_and_save_image(image, webp_path)
			return image_url.replace(extn, "webp")
		return image_url

	if image_url.startswith("http"):
		return handle_image_from_url(image_url)

	return image_url
