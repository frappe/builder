# Copyright (c) 2023, asdf and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document
from frappe.website.website_generator import WebsiteGenerator
import frappe
import json

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
		context.content = self.get_content()

	def get_content(self):
		soup = bs.BeautifulSoup("", "html.parser")
		blocks = json.loads(self.blocks)

		def get_html(blocks, soup):
			html = ""
			def get_tag(node, soup):
				tag = soup.new_tag(node["element"])
				tag.attrs = node.get("attributes", {})
				tag.attrs["style"] = node.get("styles", {})
				for child in node.get("children", []):
					print(child)
					if child.get("node_type") == "Text":
						tag.append(child.get("node_value", ""))
					else:
						tag.append(get_tag(child, soup))
				return tag

			for block in blocks:
				html += str(get_tag(block, soup))
			return html

		return get_html(blocks, soup)