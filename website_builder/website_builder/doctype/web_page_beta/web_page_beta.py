# Copyright (c) 2023, asdf and contributors
# For license information, please see license.txt

import os
import re

import bs4 as bs
import frappe
import frappe.utils
# import frappe
from frappe.model.document import Document
from frappe.website.serve import get_response_content
from frappe.website.website_generator import WebsiteGenerator
from website_builder.html_preview_image import get_preview

import json

MOBILE_BREAKPOINT = 640
TABLET_BREAKPOINT = 768
DESKTOP_BREAKPOINT = 1024

class WebPageBeta(WebsiteGenerator):
	def before_insert(self):
		if isinstance(self.blocks, list):
			self.blocks = json.dumps(self.blocks)
		if not self.blocks:
			self.blocks = "[]"
		self.route = f"pages/{frappe.generate_hash(length=20)}"

	def autoname(self):
		if not self.name:
			self.name = f"page-{frappe.generate_hash(length=5)}"

	def on_update(self):
		file_name=f"{self.name}{frappe.generate_hash()}.png"
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
		content, style, fonts = get_block_html(self.blocks)
		context.fonts = fonts
		context.content = content
		context.style = style
		context.style_file_path = get_style_file_path()

def get_block_html(blocks):
	blocks = frappe.parse_json(blocks)
	if not isinstance(blocks, list):
		blocks = [blocks]
	soup = bs.BeautifulSoup("", "html.parser")
	style_tag = soup.new_tag("style")
	font_map = {}

	def get_html(blocks, soup):
		html = ""
		def get_tag(block, soup):
			block = extend_with_component(block)
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

			if block.get("blockData"):
				for i in block.get("blockData", []):
					tag.append(get_tag(block.get("children")[0], soup))
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

def extend_with_component(block):
	if block.get("extendedFromComponent"):
		component = frappe.get_cached_value("Web Page Component", block["extendedFromComponent"], ["block", "name"], as_dict=True)
		componentBlock = frappe.parse_json(component.block)
		if componentBlock:
			block.update(componentBlock)
	return block

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
