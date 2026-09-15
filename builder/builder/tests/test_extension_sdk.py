# Copyright (c) 2026, Frappe Technologies Pvt Ltd and Contributors
# See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase
from werkzeug.test import EnvironBuilder
from werkzeug.wrappers import Request

from builder.extensions.sdk import ExtensionSDKRenderer

SDK_URL = "/builder_extension_asset/sdk/extension-sdk.js"


class TestExtensionSDKRenderer(FrappeTestCase):
	"""The route serves the SDK, and nothing else.

	An extension's own code never travels by URL now. Every user has their own
	copy, and a frame sends no session, so a route could not tell whose copy a
	request wanted. The editor reads the file and posts the code instead.
	"""

	def render(self, headers=None):
		self.addCleanup(setattr, frappe.local, "request", getattr(frappe.local, "request", None))
		frappe.local.request = Request(EnvironBuilder(path=SDK_URL, headers=headers).get_environ())

		response = ExtensionSDKRenderer(path=SDK_URL).render()
		self.addCleanup(response.close)
		return response

	def test_serves_the_sdk_every_frame_shares(self):
		self.assertTrue(ExtensionSDKRenderer(path=SDK_URL).can_render())

	def test_serves_nothing_but_the_sdk(self):
		for path in [
			"/builder_extension_asset/sdk/other.js",
			"/builder_extension_asset/sdk/../hooks.py",
			"/builder_extension_asset/acme-icons@1.0.0/main.js",
			"/builder/page/home",
		]:
			self.assertFalse(ExtensionSDKRenderer(path=path).can_render(), path)

	def test_the_response_is_a_javascript_module(self):
		self.assertEqual(self.render().mimetype, "text/javascript")

	def test_the_response_allows_any_origin(self):
		"""A frame at an opaque origin makes every request cross-origin."""
		self.assertEqual(self.render().headers["Access-Control-Allow-Origin"], "*")

	def test_it_revalidates_because_the_name_never_changes(self):
		"""One fixed URL cannot be immutable, or a rebuilt SDK never reaches a browser."""
		cache_control = self.render().headers["Cache-Control"]

		self.assertNotIn("immutable", cache_control)
		self.assertIn("no-cache", cache_control)

	def test_the_etag_follows_the_file(self):
		renderer = ExtensionSDKRenderer(path=SDK_URL)
		stat = renderer.file_path.stat()

		self.assertEqual(renderer.etag, f'"{stat.st_mtime_ns}-{stat.st_size}"')

	def test_an_unchanged_build_answers_not_modified(self):
		etag = self.render().headers["ETag"]

		self.assertEqual(self.render(headers={"If-None-Match": etag}).status_code, 304)
