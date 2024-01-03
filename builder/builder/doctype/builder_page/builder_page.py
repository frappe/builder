# Copyright (c) 2023, asdf and contributors
# For license information, please see license.txt

import contextlib
import json
import os
import re

import bs4 as bs
import frappe
import frappe.utils
from builder.html_preview_image import generate_preview
from frappe.model.document import Document
from frappe.utils.caching import redis_cache
from frappe.utils.jinja import render_template
from frappe.utils.safe_exec import safe_exec
from frappe.website.page_renderers.document_page import DocumentPage
from frappe.website.path_resolver import evaluate_dynamic_routes
from frappe.website.path_resolver import resolve_path as original_resolve_path
from frappe.website.router import get_page_info_from_web_page_with_dynamic_routes
from frappe.website.serve import get_response, get_response_content
from frappe.website.website_generator import WebsiteGenerator
from jinja2.exceptions import TemplateSyntaxError
from werkzeug.routing import Rule

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
			if evaluate_dynamic_routes(
				[Rule(f"/{d.route}", endpoint=d.name)], self.path
			):
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
		self.route = f"pages/{camel_case_to_kebab_case(self.page_title, True)}-{frappe.generate_hash(length=4)}"

	def on_update(self):
		if self.has_value_changed("dynamic_route") or self.has_value_changed("route"):
			get_web_pages_with_dynamic_routes.clear_cache()
			find_page_with_path.clear_cache()

	def autoname(self):
		if not self.name:
			self.name = f"page-{frappe.generate_hash(length=5)}"

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
		return self.route

	website = frappe._dict(
		template="templates/generators/webpage.html",
		condition_field="published",
		page_title_field="page_title",
	)

	def get_context(self, context):
		# show breadcrumbs
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
		context.style = style
		context.editor_link = f"/builder/page/{self.name}"
		context.base_url = frappe.utils.get_url(".")

		self.set_style_and_script(context)
		context.update(page_data)
		self.set_meta_tags(context=context, page_data=page_data)
		try:
			context["content"] = render_template(context.content, context)
		except TemplateSyntaxError:
			raise

	def set_meta_tags(self, context, page_data={}):
		metatags = {
			"title": self.page_title or "My Page",
			"description": self.meta_description or self.page_title,
			"image": self.meta_image or self.preview,
		}
		metatags.update(page_data.get("metatags", {}))
		context.metatags = metatags

	def is_component_used(self, component_id):
		if self.blocks and is_component_used(self.blocks, component_id):
			return True
		elif self.draft_blocks and is_component_used(self.draft_blocks, component_id):
			return True

	def set_style_and_script(self, context):
		for script in self.get("client_scripts", []):
			script_doc = frappe.get_cached_doc(
				"Builder Client Script", script.builder_script
			)
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
			safe_exec(self.page_data_script, None, _locals)
			page_data.update(_locals["data"])
		return page_data

	def generate_page_preview_image(self, html=None):
		file_name = f"{self.name}{frappe.generate_hash()}.jpeg"
		generate_preview(
			html or get_response_content(self.route),
			os.path.join(frappe.local.site_path, "public", "files", file_name),
		)
		with contextlib.suppress(frappe.DoesNotExistError):
			attached_files = frappe.get_all(
				"File",
				{
					"attached_to_field": "preview",
					"attached_to_doctype": "Builder Page",
					"attached_to_name": self.name,
				},
			)
			for file in attached_files:
				preview_file = frappe.get_doc("File", file.name)
				preview_file.delete(ignore_permissions=True)

		self.db_set("preview", f"/files/{file_name}", commit=True)


def get_block_html(blocks, page_data={}):
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
				classes.append("__text_block__")

			# temp fix: since p inside p is illegal
			if element in ["p", "__raw_html__"]:
				element = "div"

			# temp fix: since img src is not absolute, it doesn't load in preview
			image_src = block.get("attributes", {}).get("src") or ""
			if element == "img" and image_src.startswith("/"):
				block["attributes"]["src"] = frappe.utils.get_url(image_src)

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
				plain_styles = {
					k: v for k, v in block.get("rawStyles", {}).items() if ":" not in k
				}
				state_styles = {
					k: v for k, v in block.get("rawStyles", {}).items() if ":" in k
				}
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
				classes.append(style_class)

			tag.attrs["class"] = get_class(classes)

			innerContent = block.get("innerHTML")
			if innerContent:
				inner_soup = bs.BeautifulSoup(innerContent, "html.parser")
				set_fonts_from_html(inner_soup, font_map)
				tag.append(inner_soup)

			block_data = []
			if (
				block.get("isRepeaterBlock")
				and block.get("children")
				and block.get("dataKey")
			):
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

			return tag

		for block in blocks:
			html += str(get_tag(block, soup))

		return html, str(style_tag), font_map

	data = get_html(blocks, soup)
	return data


def get_style(style_obj):
	return "".join(f"{camel_case_to_kebab_case(key)}: {value};" for key, value in style_obj.items()) if style_obj else ""

def get_class(class_list):
	return " ".join(class_list)


def camel_case_to_kebab_case(text, remove_spaces=False):
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
		state, property = key.split(":")
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
				font_map[font] = { "weights": [style.get("fontWeight") or "400"] }

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
			component_children.insert(
				overridden_children.index(overridden_child), overridden_child
			)


def set_dynamic_content_placeholder(block, data_key=False):
	block_data_key = block.get("dataKey")
	if block_data_key and block_data_key.get("key"):
		key = f"{data_key}.{block_data_key.get('key')}" if data_key else block_data_key.get("key")
		_property = block_data_key.get("property")
		_type = block_data_key.get("type")
		if _type == "attribute":
			block["attributes"][_property] = f"{{{{ {key} or '{escape_single_quotes(block['attributes'].get(_property, ''))}' }}}}"
		elif _type == "style":
			block["baseStyles"][_property] = f"{{{{ {key} or '{escape_single_quotes(block['baseStyles'].get(_property, ''))}' }}}}"
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
	return text.replace("'", "\\'")

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
		return frappe.db.get_value(
			"Builder Page", dict(route=route, published=1), "name", cache=True
		)
	except:
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
		[
			Rule(f"/{d.route}", endpoint=d.name)
			for d in get_web_pages_with_dynamic_routes()
		],
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
