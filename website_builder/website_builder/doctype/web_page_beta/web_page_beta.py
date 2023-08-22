# Copyright (c) 2023, asdf and contributors
# For license information, please see license.txt

import os
import re

import bs4 as bs
import frappe
import frappe.utils
# import frappe
from frappe.model.document import Document
from frappe.website.serve import get_response_content, get_response
from frappe.website.website_generator import WebsiteGenerator
from website_builder.html_preview_image import get_preview
from frappe.utils.safe_exec import safe_exec
from frappe.utils.caching import redis_cache


import json

MOBILE_BREAKPOINT = 576
TABLET_BREAKPOINT = 768
DESKTOP_BREAKPOINT = 1024

class WebPageBeta(WebsiteGenerator):
	def before_insert(self):
		if isinstance(self.blocks, list):
			self.blocks = frappe.as_json(self.blocks, indent=None)
		if isinstance(self.draft_blocks, list):
			self.draft_blocks = frappe.as_json(self.draft_blocks, indent=None)
		if not self.blocks:
			self.blocks = "[]"
		if self.preview:
			self.flags.skip_preview = True
		self.route = f"pages/{frappe.generate_hash(length=20)}"

	def autoname(self):
		if not self.name:
			self.name = f"page-{frappe.generate_hash(length=5)}"

	def on_update(self):
		if self.published and self.draft_blocks:
			self.blocks = self.draft_blocks
			self.draft_blocks = None

		if not self.flags.skip_preview:
			file_name=f"{self.name}{frappe.generate_hash()}.jpeg"
			frappe.enqueue(
				method=get_preview,
				html=get_response_content(self.route),
				output_path=os.path.join(
					frappe.local.site_path, "public", "files", file_name
				),
			)
			self.db_set("preview", f"/files/{file_name}")

	website = frappe._dict(
		template = "templates/generators/webpage.html",
		condition_field = "published",
		page_title_field = "page_title",
	)

	def get_context(self, context):
		# show breadcrumbs
		context.title = self.page_title or "My Page"
		page_data = self.get_page_data()
		if page_data.get("title"):
			context.title = page_data.get("page_title")

		blocks = self.blocks
		if frappe.flags.show_preview and self.draft_blocks:
			blocks = self.draft_blocks

		content, style, fonts = get_block_html(blocks, page_data)
		context.fonts = fonts
		context.content = content
		context.style = style
		context.style_file_path = get_style_file_path()

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

def get_block_html(blocks, page_data={}):
	blocks = frappe.parse_json(blocks)
	if not isinstance(blocks, list):
		blocks = [blocks]
	soup = bs.BeautifulSoup("", "html.parser")
	style_tag = soup.new_tag("style")
	font_map = {}

	def get_html(blocks, soup):
		html = ""
		def get_tag(block, soup, data=None):
			block = extend_with_component(block, data)
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
			if block.get("isRepeaterBlock"):
				dataKey = block.get("dataKey")
				key = dataKey.get("key") if dataKey else ""
				if key:
					block_data = page_data.get(key, [])

			if block_data and block.get("children"):
				for data in block_data:
					tag.append(get_tag(block.get("children")[0], soup, data))
			else:
				for child in block.get("children", []):
					tag.append(get_tag(child, soup))
			return tag

		for block in blocks:
			html += str(get_tag(block, soup))

		return html, str(style_tag), font_map

	return get_html(blocks, soup)

def get_style(style_obj):
	return "".join(f"{camel_case_to_kebab_case(key)}: {value};" for key, value in style_obj.items()) if style_obj else ""

def get_class(class_list):
	return " ".join(class_list)

def camel_case_to_kebab_case(text):
	return re.sub(r'(?<!^)(?=[A-Z])', '-', text).lower()

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

def extend_with_component(block, data=None):
	if block.get("extendedFromComponent"):
		component = frappe.get_cached_value("Web Page Component", block["extendedFromComponent"], ["block", "name"], as_dict=True)
		component_block = frappe.parse_json(component.block)
		if component_block:
			extend_block(component_block, block, data=data)
			block = component_block

	return block

def extend_block(block, overridden_block, data=None):
	block["baseStyles"].update(overridden_block["baseStyles"])
	block["mobileStyles"].update(overridden_block["mobileStyles"])
	block["tabletStyles"].update(overridden_block["tabletStyles"])
	block["rawStyles"].update(overridden_block["rawStyles"])
	block["attributes"].update(overridden_block["attributes"])
	block["classes"].extend(overridden_block["classes"])
	if overridden_block.get("innerHTML"):
		block["innerHTML"] = overridden_block["innerHTML"]

	extend_with_data(block, data)

	component_children = block.get("children", [])
	overridden_children = overridden_block.get("children", [])

	for overridden_child in overridden_children:
		component_child = next((child for child in component_children if child.get("blockId") == overridden_child.get("blockId")), None)
		if component_child:
			extend_block(component_child, overridden_child, data=data)
		else:
			component_children.insert(overridden_children.index(overridden_child), overridden_child)



def extend_with_data(block, data):
	if not data:
		return
	data_key = block.get("dataKey")
	if data_key:
		value = data.get((data_key.get("key")))
		if value:
			if data_key.get("type") == "attribute":
				block["attributes"][data_key.get("property")] = value
			elif data_key.get("type") == "style":
				block["baseStyles"][data_key.get("property")] = value
			elif data_key.get("type") == "key":
				block[data_key.get("property")] = value

def get_style_file_path():
	# TODO: Redo this, currently it loads the first matching file
	# from frappe.utils import get_url
	# return get_url("/files/tailwind.css")
	import glob
	folder_path = "./assets/website_builder/frontend/assets/"
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
		"Web Page Beta", fields=["name", "route", "modified"], filters=dict(published=1, dynamic_route=1),
		update={"doctype": "Web Page Beta"}
	)

@frappe.whitelist()
def get_page_preview_html(page: str) -> str:
	"""Returns the HTML of the page preview"""
	page = frappe.get_cached_doc("Web Page Beta", page)
	frappe.flags.show_preview = True
	return get_response(page.route)
