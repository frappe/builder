# Copyright (c) 2023, asdf and contributors
# For license information, please see license.txt

import contextlib
import os
import re

import bs4 as bs
import frappe
import frappe.utils
# import frappe
from frappe.model.document import Document
from frappe.website.serve import get_response_content, get_response
from frappe.website.website_generator import WebsiteGenerator
from builder.html_preview_image import generate_preview
from frappe.utils.safe_exec import safe_exec
from frappe.utils.caching import redis_cache
from frappe.website.page_renderers.document_page import DocumentPage
from frappe.utils.jinja import render_template
from jinja2.exceptions import TemplateSyntaxError



import json

MOBILE_BREAKPOINT = 576
TABLET_BREAKPOINT = 768
DESKTOP_BREAKPOINT = 1024

class BuilderPage(WebsiteGenerator):
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
			self.generate_page_preview_image()
		self.save()
		return self.route

	website = frappe._dict(
		template = "templates/generators/webpage.html",
		condition_field = "published",
		page_title_field = "page_title",
	)

	def get_context(self, context):
		# show breadcrumbs
		page_data = self.get_page_data()
		if page_data.get("title"):
			context.title = page_data.get("page_title")

		blocks = self.blocks
		if frappe.flags.show_preview and self.draft_blocks:
			blocks = self.draft_blocks

		content, style, fonts = get_block_html(blocks)
		context.fonts = fonts
		context.content = content
		context.style = style
		context.style_file_path = get_style_file_path()
		context.script = self.client_script
		context.update(page_data)
		self.set_meta_tags(context=context)
		try:
			context["content"] = render_template(context.content, context)
			context["no_cache"] = 1
		except TemplateSyntaxError:
			raise

	def set_meta_tags(self, context):
		context.metatags = {
			"title": self.page_title or "My Page",
			"description": self.meta_description or self.page_title,
			"image": self.meta_image or self.preview
		}

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
		file_name=f"{self.name}{frappe.generate_hash()}.jpeg"
		generate_preview(html or get_response_content(self.route), os.path.join(
			frappe.local.site_path, "public", "files", file_name
		))
		with contextlib.suppress(frappe.DoesNotExistError):
			attached_files = frappe.get_all("File", {
				"attached_to_field": "preview",
				"attached_to_doctype": "Builder Page",
				"attached_to_name": self.name
			})
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
		def get_tag(block, soup, repeater_child=False):
			block = extend_with_component(block)
			set_dynamic_content_placeholder(block, repeater_child)
			element = block.get("originalElement") or block.get("element")
			# temp fix: since p inside p is illegal
			if element in ["p", "__raw_html__"]:
				element = "div"
			tag = soup.new_tag(element)
			tag.attrs = block.get("attributes", {})
			classes = block.get("classes", [])
			if block.get("baseStyles", {}):
				style_class = f"frappe-builder-{frappe.generate_hash(length=8)}"
				base_styles = block.get("baseStyles", {})
				mobile_styles = block.get("mobileStyles", {})
				tablet_styles = block.get("tabletStyles", {})
				set_fonts([base_styles, mobile_styles, tablet_styles], font_map)
				append_style(block.get("baseStyles", {}), style_tag, style_class)
				append_style(block.get("rawStyles", {}), style_tag, style_class)
				append_style(block.get("tabletStyles", {}), style_tag, style_class, device="tablet")
				append_style(block.get("mobileStyles", {}), style_tag, style_class, device="mobile")
				classes.append(style_class)

			tag.attrs["class"] = get_class(classes)

			innerContent = block.get("innerHTML")
			if innerContent:
				inner_soup = bs.BeautifulSoup(innerContent, "html.parser")
				set_fonts_from_html(inner_soup, font_map)
				tag.append(inner_soup)

			block_data = []
			if block.get("isRepeaterBlock") and block.get("children"):
				tag.append("{% for _data in " + block.get("dataKey").get("key") + " %}")
				tag.append(get_tag(block.get("children")[0], soup, True))
				tag.append("{% endfor %}")
			else:
				for child in block.get("children", []):
					tag.append(get_tag(child, soup, repeater_child))

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
	text = re.sub(r'(?<!^)(?=[A-Z])', '-', text).lower()
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
		style_string = f"@media only screen and (min-width: {MOBILE_BREAKPOINT + 1}px) and (max-width: {DESKTOP_BREAKPOINT - 1}px) {{ {style_string} }}"
	style_tag.append(style_string)

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
					font_map[font] = { "weights": ["400"] }

def extend_with_component(block):
	if block.get("extendedFromComponent"):
		component = frappe.get_cached_value("Builder Component", block["extendedFromComponent"], ["block", "name"], as_dict=True)
		component_block = frappe.parse_json(component.block)
		if component_block:
			extend_block(component_block, block)
			block = component_block

	return block

def extend_block(block, overridden_block):
	block["baseStyles"].update(overridden_block["baseStyles"])
	block["mobileStyles"].update(overridden_block["mobileStyles"])
	block["tabletStyles"].update(overridden_block["tabletStyles"])
	block["rawStyles"].update(overridden_block["rawStyles"])
	block["attributes"].update(overridden_block["attributes"])
	block["classes"].extend(overridden_block["classes"])
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


def set_dynamic_content_placeholder(block, repeater_child=False):
	data_key = block.get("dataKey")
	if data_key and data_key.get("key"):
		key = f"_data.{data_key.get('key')}" if repeater_child else data_key.get("key")
		value = "{{" + key + "}}"
		if data_key.get("type") == "attribute":
			block["attributes"][data_key.get("property")] = value
		elif data_key.get("type") == "style":
			block["baseStyles"][data_key.get("property")] = value
		elif data_key.get("type") == "key" and not block.get("isRepeaterBlock"):
			block[data_key.get("property")] = value

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

@redis_cache(ttl=60 * 60)
def get_web_pages_with_dynamic_routes() -> dict[str, str]:
	return frappe.get_all(
		"Builder Page", fields=["name", "route", "modified"], filters=dict(published=1, dynamic_route=1),
		update={"doctype": "Builder Page"}
	)

@frappe.whitelist()
def get_page_preview_html(page: str, **kwarg) -> str:
	# to load preview without publishing
	frappe.form_dict.update(kwarg)
	renderer = DocumentPage(path="")
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
		html=str(response.data, 'utf-8'),
		queue="short",
	)
	return response
