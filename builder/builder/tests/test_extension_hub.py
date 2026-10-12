# Copyright (c) 2026, Frappe Technologies Pvt Ltd and Contributors
# See license.txt

from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

from builder.builder.tests.extension_fixtures import drop_installations, make_installation
from builder.extensions.hub import assert_installable, ensure_protocol, resolve_hub_url

EXTENSION = "acme/installing"


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


class TestRetry(FrappeTestCase):
	"""A retry must not start a second job on a row whose job still runs."""

	def setUp(self):
		drop_installations(EXTENSION)
		make_installation(EXTENSION, install_state="Installing", enabled=0)

	def test_refuses_while_the_job_is_queued_or_running(self):
		with patch("builder.extensions.hub.is_job_enqueued", return_value=True):
			self.assertRaises(frappe.ValidationError, assert_installable, EXTENSION)

	def test_allows_once_the_job_is_gone(self):
		with patch("builder.extensions.hub.is_job_enqueued", return_value=False):
			assert_installable(EXTENSION)
