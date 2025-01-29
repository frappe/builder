# Copyright (c) 2023, asdf and Contributors
# See license.txt

import frappe
from frappe.desk.form.load import getdoc
from frappe.tests.utils import FrappeTestCase
from frappe.website.serve import get_response_content


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

	@classmethod
	def tearDownClass(cls):
		cls.page.delete()
		cls.page_with_dynamic_route.delete()
