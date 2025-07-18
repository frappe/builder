# Copyright (c) 2023, asdf and Contributors
# See license.txt

import frappe
from frappe.desk.form.load import getdoc
from frappe.tests.utils import FrappeTestCase
from frappe.website.serve import get_response_content

repeater_page_data_script = """
data.update({
	"items": [
		{"name": "Item 1", "price": "$10"},
		{"name": "Item 2", "price": "$20"}
	]
})
"""

page_data_script = """
data.update({
	"name": "John Doe",
	"color": "red",
	"padding": "20px",
	"link": "https://example.com",
})
"""


class TestBuilderPage(FrappeTestCase):
	@classmethod
	def setUpClass(cls):
		cls.page = frappe.get_doc(
			{
				"doctype": "Builder Page",
				"name": "test-page",
				"page_title": "Test Page",
				"published": 1,
				"route": "/test-page",
				"blocks": [
					{
						"element": "body",
						"baseStyles": {"background": "red", "fontFamily": "Inter"},
						"customAttributes": {"dir": "ltr"},
						"children": [
							{
								"element": "h1",
								"innerHTML": "Hello World!",
								"baseStyles": {
									"color": "blue",
									"fontFamily": "Comic Sans MS",
									"fontWeight": "500",
								},
							}
						],
					}
				],
			}
		).insert(ignore_if_duplicate=True)
		cls.page_with_dynamic_route = frappe.get_doc(
			{
				"doctype": "Builder Page",
				"page_title": "Test Page Dynamic Route",
				"published": 1,
				"route": "/test-page-dynamic-route/<name>",
				"dynamic_route": 1,
				"blocks": [
					{"element": "body", "children": [{"element": "h1", "innerHTML": "Dynamic Content!"}]}
				],
			}
		).insert(ignore_if_duplicate=True)

	def test_can_render(self):
		content = get_response_content("/test-page")
		self.assertTrue("Hello World!" in content)

	def test_onload(self):
		getdoc("Builder Page", self.page.name)
		self.assertEqual(frappe.response.docs[0].get("__onload").get("builder_path"), "builder")

	def test_dynamic_route(self):
		from frappe.utils import get_html_for_route

		content = get_html_for_route("/test-page-dynamic-route/123")
		self.assertTrue("Dynamic Content!" in content)

	def test_publish_unpublish(self):
		self.page.unpublish()
		from frappe.utils import get_html_for_route

		content = get_html_for_route("/test-page")
		self.assertTrue("window.is_404 = true;" in content)

		self.page.publish()
		content = get_response_content("/test-page")
		self.assertTrue("Hello World!" in content)

	def test_dynamic_values(self):
		page = frappe.get_doc(
			{
				"doctype": "Builder Page",
				"page_title": "Dynamic Values Test",
				"published": 1,
				"route": "/dynamic-values-test",
				"page_data_script": page_data_script,
				"blocks": [
					{
						"element": "body",
						"attributes": {"style": "background: #f0f0f0;"},
						"children": [
							{
								"element": "h1",
								"innerHTML": "Hello",
								"attributes": {"style": "background: #f0f0f0;"},
								"dynamicValues": [{"key": "name", "type": "key", "property": "innerHTML"}],
							},
							{
								"element": "h2",
								"innerHTML": "Content",
								"attributes": {"style": "background: #f0f0f0;"},
								"dynamicValues": [
									{"key": "color", "type": "style", "property": "color"},
									{"key": "padding", "type": "style", "property": "padding"},
								],
								"baseStyles": {},
							},
							{
								"element": "a",
								"innerHTML": "Link",
								"attributes": {},
								"dynamicValues": [{"key": "link", "type": "attribute", "property": "href"}],
							},
						],
					}
				],
			}
		).insert()

		try:
			content = get_response_content("/dynamic-values-test")
			self.assertTrue("John Doe" in get_html_for(content, "tag", "h1"))
			self.assertTrue("color: red;padding: 20px;" in get_html_for(content, "tag", "h2"))
			self.assertTrue('href="https://example.com"' in get_html_for(content, "tag", "a"))
		finally:
			page.delete()

	def test_repeater_block_dynamic_values(self):
		page = frappe.get_doc(
			{
				"doctype": "Builder Page",
				"page_title": "Repeater Block Test",
				"published": 1,
				"route": "/repeater-block-test",
				"page_data_script": repeater_page_data_script,
				"blocks": [
					{
						"element": "body",
						"children": [
							{
								"element": "div",
								"isRepeaterBlock": True,
								"dataKey": {"key": "items", "type": "key", "property": "dataKey"},
								"children": [
									{
										"element": "div",
										"children": [
											{
												"element": "h2",
												"innerHTML": "",
												"attributes": {},
												"dynamicValues": [
													{"key": "name", "type": "key", "property": "innerHTML"}
												],
											},
											{
												"element": "span",
												"innerHTML": "",
												"attributes": {},
												"dynamicValues": [
													{"key": "price", "type": "key", "property": "innerHTML"}
												],
											},
										],
									}
								],
							}
						],
					}
				],
			}
		).insert()

		try:
			content = get_response_content("/repeater-block-test")
			self.assertTrue("Item 1" in get_html_for(content, "tag", "h2"))
			self.assertTrue("$10" in get_html_for(content, "tag", "span"))
			self.assertTrue("Item 2" in get_html_for(content, "tag", "h2", index=1))
			self.assertTrue("$20" in get_html_for(content, "tag", "span", index=1))

		finally:
			page.delete()

	@classmethod
	def tearDownClass(cls):
		cls.page.delete()
		cls.page_with_dynamic_route.delete()


def get_html_for(html, type, value, index=None):
	from bs4 import BeautifulSoup

	soup = BeautifulSoup(html, "html.parser")
	if type == "tag":
		results = soup.find_all(value)
		result = (
			results[index] if index is not None and index < len(results) else results[0] if results else None
		)
		return str(result) if result else ""
	if type == "attribute":
		results = soup.find_all(attrs=value)
		result = (
			results[index] if index is not None and index < len(results) else results[0] if results else None
		)
		return str(result) if result else ""
