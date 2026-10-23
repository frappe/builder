# Copyright (c) 2023, Frappe Technologies Pvt Ltd and Contributors
# See license.txt

from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

from builder.extensions.safe_requests import BlockedRequest

PAGE_CACHE_KEY = "website_page::test-settings-page"


class TestBuilderSettings(FrappeTestCase):
	def test_saving_site_wide_code_clears_the_page_cache(self):
		settings = frappe.get_single("Builder Settings")
		for field in ("head_html", "body_html"):
			frappe.cache.set_value(PAGE_CACHE_KEY, {"en": "<html>old</html>"})
			settings.set(field, (settings.get(field) or "") + "\n<!-- changed -->")
			settings.save()
			self.assertIsNone(frappe.cache.get_value(PAGE_CACHE_KEY), field)

	def test_refuses_a_plain_http_hub_outside_developer_mode(self):
		settings = frappe.get_single("Builder Settings")
		settings.hub_url = "http://hub.example.com"
		with patch.dict(frappe.conf, {"developer_mode": 0}):
			self.assertRaises(BlockedRequest, settings.save)
