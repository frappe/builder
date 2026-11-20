# Copyright (c) 2026, Frappe Technologies Pvt Ltd and Contributors
# See license.txt

"""What a site whose editor is isolated refuses on the server, as frappe.page's own site is through the
builder_is_isolated hook: its editor shares the origin with every member's dashboard, so no code it did
not ship may run there, and no ChatGPT plan login is stored on the shared host."""

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import set_request

from builder.ai import api
from builder.builder.tests.hosting_hooks import hosting_hooks, isolate
from builder.builder.tests.plugin_fixtures import INSTALLATION_DOCTYPE, drop_installations
from builder.plugins import bob
from builder.plugins.development import install_dev_plugin

CALLBACK = "http://localhost:1455/auth/callback?code=abc&state=xyz"


class TestIsolatedSite(FrappeTestCase):
	def setUp(self):
		# no X-FP-Mount header: only the hook isolates this site
		set_request(method="GET", path="/")

	def test_every_chatgpt_sign_in_step_is_refused(self):
		steps = {
			"start": api.start_codex_login,
			"poll": lambda: api.poll_codex_login("xyz"),
			"browser link": api.start_codex_browser_login,
			"finish": lambda: api.finish_codex_login(CALLBACK),
		}
		with hosting_hooks(builder_is_isolated=[isolate]):
			for step, call in steps.items():
				with self.subTest(step), self.assertRaises(frappe.PermissionError):
					call()

	def test_a_site_that_is_not_isolated_hands_out_a_browser_sign_in_link(self):
		with hosting_hooks(builder_is_isolated=[]):
			self.assertIn("state", api.start_codex_browser_login())

	def test_bob_writes_no_plugin(self):
		drop_installations("bob/isolated-check")
		with hosting_hooks(builder_is_isolated=[isolate]), self.assertRaises(frappe.PermissionError):
			bob.save_plugin("isolated-check", "Isolated", "", "export default { install() {} }")

		self.assertFalse(frappe.db.exists(INSTALLATION_DOCTYPE, {"plugin": "bob/isolated-check"}))

	def test_no_dev_server_plugin_is_installed_even_in_developer_mode(self):
		drop_installations("acme/isolated-dev")
		previous = frappe.conf.get("developer_mode")
		frappe.conf.developer_mode = 1
		self.addCleanup(setattr, frappe.conf, "developer_mode", previous)

		with hosting_hooks(builder_is_isolated=[isolate]), self.assertRaises(frappe.PermissionError):
			install_dev_plugin("acme/isolated-dev")

		self.assertFalse(frappe.db.exists(INSTALLATION_DOCTYPE, {"plugin": "acme/isolated-dev"}))
