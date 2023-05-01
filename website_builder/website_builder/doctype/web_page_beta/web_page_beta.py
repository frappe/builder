# Copyright (c) 2023, asdf and contributors
# For license information, please see license.txt

import json
import re

import bs4 as bs
import frappe
# import frappe
from frappe.model.document import Document
from frappe.website.website_generator import WebsiteGenerator


class WebPageBeta(WebsiteGenerator):
	website = frappe._dict(
		template = "templates/generators/webpage.html",
		condition_field = "published",
		page_title_field = "page_name",
	)

	def get_context(self, context):
		# show breadcrumbs
		context.title = "page"
		context.fonts = {}
		content, style = self.get_content(context)
		context.content = content
		context.style = style

	def get_content(self, context):
		soup = bs.BeautifulSoup("", "html.parser")
		blocks = json.loads(self.blocks)
		style_tag = soup.new_tag("style")

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
					setFonts([base_styles, mobile_styles, tablet_styles], context)
					append_style(node.get("baseStyles", {}), style_tag, style_class)
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

			return html, str(style_tag)

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
		style_string = f"@media only screen and (max-width: 425px) {{ {style_string} }}"
	elif device == "tablet":
		style_string = f"@media only screen and (min-width: 426px) and (max-width: 768px) {{ {style_string} }}"
	style_tag.append(style_string)

def setFonts(styles, context):
	for style in styles:
		font = style.get("fontFamily")
		if font:
			if font in context.fonts:
				if style.get("fontWeight") and style.get("fontWeight") not in context.fonts[font]["weights"]:
					context.fonts[font]["weights"].append(style.get("fontWeight"))
			else:
				context.fonts[font] = { "weights": [style.get("fontWeight") or "400"] }