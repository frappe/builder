# Copyright (c) 2023, asdf and Contributors
# See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.website.serve import get_response_content


class TestBuilderPage(FrappeTestCase):
	def setUp(self):
		self.page = frappe.get_doc(
			{
				"doctype": "Builder Page",
				"name": "test-page",
				"page_title": "Test Page",
				"published": 1,
				"route": "/test-page",
				"blocks": [{"element": "body", "children": [{"element": "h1", "innerHTML": "Hello World!"}]}],
			}
		).insert(ignore_if_duplicate=True)
		print(self.page.name)

	def test_can_render(self):
		content = get_response_content("/test-page")
		self.assertTrue("Hello World!" in content)
