# Copyright (c) 2023, asdf and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document
from frappe.website.website_generator import WebsiteGenerator
import frappe
import json
import re

import bs4 as bs

class WebPageBeta(WebsiteGenerator):
	website = frappe._dict(
		template = "templates/generators/webpage.html",
		condition_field = "published",
		page_title_field = "page_name",
	)

	def get_context(self, context):
		# show breadcrumbs
		context.title = "Page"
		content, style = self.get_content()
		context.content = content
		context.style = style

	def get_content(self):
		soup = bs.BeautifulSoup("", "html.parser")
		blocks = json.loads(self.blocks)
		style_tag = soup.new_tag("style")

		def get_html(blocks, soup):
			html = ""
			def get_tag(node, soup):
				tag = soup.new_tag(node["element"])
				tag.attrs = node.get("attributes", {})
				classes = node.get("classes", [])
				if node.get("styles", {}):
					style_class = f"--{frappe.generate_hash(length=8)}"
					append_style(node.get("styles", {}), style_tag, style_class)
					append_style(node.get("tabletStyles", {}), style_tag, style_class, device="tablet")
					append_style(node.get("mobileStyles", {}), style_tag, style_class, device="mobile")
					classes.append(style_class)

				tag.attrs["class"] = get_class(classes)
				for child in node.get("children", []):
					if child.get("node_type") == "Text":
						tag.append(child.get("node_value", ""))
					else:
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
		style_string = f"@media only screen and (max-width: 600px) {{ {style_string} }}"
	elif device == "tablet":
		style_string = f"@media only screen and (max-width: 992px) {{ {style_string} }}"
	style_tag.append(style_string)
