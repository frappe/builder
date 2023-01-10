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
		options = json.loads(self.options)
		html = ""
		for option in options:
			element = soup.new_tag(option["element"])
			element.attrs = option.get("attributes", {})
			# style = ""
			# for (key, value) in option.get("styles", {}).items():
			# 	style = f"{style}{key}: {value};"
			element.attrs["style"] = option.get("styles", {})
			element.string = option.get("innerText", "")
			html = f"{html}{str(element)}"
		return html

		# with open("test.html", "w") as f:
		# 	f.write(self.options)
