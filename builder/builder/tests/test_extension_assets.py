# Copyright (c) 2026, Frappe Technologies Pvt Ltd and Contributors
# See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import set_request

from builder.builder.tests.extension_fixtures import drop_installations, make_installation
from builder.extensions.assets import SECURITY_HEADERS, ExtensionAssetRenderer

EXTENSION = "acme/served"


class TestExtensionAssets(FrappeTestCase):
	"""Tests the public route that serves the files of an installation."""

	def setUp(self):
		drop_installations(EXTENSION)
		self.installation = make_installation(EXTENSION)
		self.installation.write_extension_files(
			{
				"main.js": b"export const answer = 42;",
				"chunks/panel.js": b"export {};",
				"page.html": b"<p></p>",
			}
		)

	def fetch(self, path):
		set_request(method="GET", path=f"/{path}")
		frappe.set_user("Guest")
		self.addCleanup(frappe.set_user, "Administrator")
		response = ExtensionAssetRenderer(path).render()
		self.addCleanup(response.close)
		return response

	def url(self, file, checksum="sum123"):
		return f"builder_extension_asset/{self.installation.name}/{checksum}/{file}"

	def assert_sandboxed(self, response):
		for header, value in SECURITY_HEADERS.items():
			self.assertEqual(response.headers[header], value, header)

	def assert_not_found(self, path):
		response = self.fetch(path)
		self.assertEqual(response.status_code, 404)
		self.assert_sandboxed(response)

	def test_serves_the_entry_to_a_guest(self):
		response = self.fetch(self.url("main.js"))

		self.assertEqual(b"".join(response.response), b"export const answer = 42;")
		self.assertEqual(response.mimetype, "text/javascript")
		self.assertIn("immutable", response.headers["Cache-Control"])
		self.assert_sandboxed(response)

	def test_serves_a_chunk_in_a_folder(self):
		self.assertEqual(self.fetch(self.url("chunks/panel.js")).status_code, 200)

	def test_refuses_an_old_build(self):
		self.assert_not_found(self.url("main.js", checksum="sum000"))

	def test_refuses_an_installation_that_is_switched_off(self):
		make_installation(EXTENSION, enabled=0)

		self.assert_not_found(self.url("main.js"))

	def test_refuses_an_unknown_installation(self):
		self.assert_not_found("builder_extension_asset/missing/sum123/main.js")

	def test_refuses_a_path_outside_the_install(self):
		self.assert_not_found(self.url("../../../site_config.json"))

	def test_refuses_a_type_a_frame_does_not_load(self):
		self.assert_not_found(self.url("page.html"))

	def test_refuses_a_path_with_too_few_segments(self):
		self.assert_not_found(f"builder_extension_asset/{self.installation.name}/main.js")
