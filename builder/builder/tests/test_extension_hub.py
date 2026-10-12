# Copyright (c) 2026, Frappe Technologies Pvt Ltd and Contributors
# See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase

from builder.extensions.hub import ensure_protocol, resolve_hub_url


class TestHubUrl(FrappeTestCase):
	"""The release from the Hub holds the package sha256, so a bare host must not mean plain HTTP."""

	def test_a_bare_host_gets_https(self):
		self.assertEqual(ensure_protocol("hub.example.com/"), "https://hub.example.com")

	def test_keeps_an_explicit_http_for_a_local_hub(self):
		self.assertEqual(ensure_protocol("http://hub.localhost:8000"), "http://hub.localhost:8000")

	def test_the_site_setting_gets_https(self):
		settings = frappe.get_single("Builder Settings")
		self.addCleanup(frappe.db.set_single_value, "Builder Settings", "hub_url", settings.hub_url)
		frappe.db.set_single_value("Builder Settings", "hub_url", "hub.example.com")

		self.assertEqual(resolve_hub_url(), "https://hub.example.com")
