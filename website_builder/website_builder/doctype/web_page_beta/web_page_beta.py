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

MOBILE_BREAKPOINT = 640
TABLET_BREAKPOINT = 768
DESKTOP_BREAKPOINT = 1024

class WebPageBeta(WebsiteGenerator):
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
		page_title_field = "page_name",
	)

	def get_context(self, context):
		# show breadcrumbs
		context.title = "page"
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
		def get_tag(node, soup):
			tag = soup.new_tag(node.get("originalElement") or node["element"])
			tag.attrs = node.get("attributes", {})
			classes = node.get("classes", [])
			if node.get("baseStyles", {}):
				style_class = f"--{frappe.generate_hash(length=8)}"
				base_styles = node.get("baseStyles", {})
				mobile_styles = node.get("mobileStyles", {})
				tablet_styles = node.get("tabletStyles", {})
				setFonts([base_styles, mobile_styles, tablet_styles], font_map)
				append_style(node.get("baseStyles", {}), style_tag, style_class)
				append_style(node.get("rawStyles", {}), style_tag, style_class)
				append_style(node.get("tabletStyles", {}), style_tag, style_class, device="tablet")
				append_style(node.get("mobileStyles", {}), style_tag, style_class, device="mobile")
				classes.append(style_class)

			tag.attrs["class"] = get_class(classes)
			if node.get("innerText"):
				tag.append(node.get("innerText"))

			for child in node.get("children", []):
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

def setFonts(styles, font_map):
	for style in styles:
		font = style.get("fontFamily")
		if font:
			if font in font_map:
				if style.get("fontWeight") and style.get("fontWeight") not in font_map[font]["weights"]:
					font_map[font]["weights"].append(style.get("fontWeight"))
					font_map[font]["weights"].sort()
			else:
				font_map[font] = { "weights": [style.get("fontWeight") or "400"] }

def get_style_file_path():
	# TODO: Redo this, currently it loads the first matching file
	import glob
	folder_path = "./assets/website_builder/frontend/assets/"
	file_pattern = "index.*.css"
	matching_files = glob.glob(f"{folder_path}/{file_pattern}")
	if matching_files:
		return frappe.utils.get_url(matching_files[0].lstrip("."))
