# Copyright (c) 2023, Frappe Technologies Pvt Ltd and Contributors
# See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase

PAGE_CACHE_KEY = "website_page::test-client-script-page"


class TestBuilderClientScript(FrappeTestCase):
	def test_saving_a_script_clears_the_pages_that_link_it(self):
		script = frappe.get_doc(
			{"doctype": "Builder Client Script", "script_type": "CSS", "script": ".a { color: red; }"}
		).insert()
		frappe.get_doc(
			{
				"doctype": "Builder Page",
				"page_title": "Client Script Page",
				"route": "test-client-script-page",
				"client_scripts": [{"builder_script": script.name}],
			}
		).insert()
		frappe.cache.set_value(PAGE_CACHE_KEY, {"en": "<html>old</html>"})

		script.script = ".a { color: blue; }"
		script.save()

		self.assertIsNone(frappe.cache.get_value(PAGE_CACHE_KEY))
