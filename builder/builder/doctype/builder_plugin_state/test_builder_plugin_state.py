# Copyright (c) 2026, Frappe Technologies Pvt Ltd and contributors
# See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase

from builder.builder.tests.plugin_fixtures import (
	drop_installations,
	make_installation,
	make_page_reader,
	make_user,
)
from builder.plugins.state import STATE_DOCTYPE, get_state, set_state, unset_state

PLUGIN = "acme/remembers"


class TestPluginState(FrappeTestCase):
	"""One user's drawer for one plugin."""

	def setUp(self):
		drop_installations(PLUGIN)
		self.installation = make_installation(PLUGIN)

	def test_merges_and_unsets_keys(self):
		set_state(PLUGIN, {"theme": "dark"})
		set_state(PLUGIN, {"page": 2})
		self.assertEqual(get_state(PLUGIN), {"theme": "dark", "page": 2})

		unset_state(PLUGIN, "theme")
		self.assertEqual(get_state(PLUGIN), {"page": 2})

	def test_another_users_store_is_not_this_one(self):
		"""The installation is the site's. What it stores is each user's."""
		set_state(PLUGIN, {"theme": "dark"})

		frappe.set_user(make_user())
		self.addCleanup(frappe.set_user, "Administrator")

		self.assertEqual(get_state(PLUGIN), {})

	def test_a_user_without_a_manager_role_stores_keys(self):
		frappe.set_user(make_page_reader(self))
		self.addCleanup(frappe.set_user, "Administrator")

		set_state(PLUGIN, {"theme": "dark"})

		self.assertEqual(get_state(PLUGIN), {"theme": "dark"})

	def test_refuses_an_plugin_the_site_has_not_installed(self):
		drop_installations("acme/absent")

		with self.assertRaises(frappe.PermissionError):
			get_state("acme/absent")

	def test_uninstall_takes_the_store_with_it(self):
		set_state(PLUGIN, {"theme": "dark"})

		self.installation.delete()

		self.assertEqual(frappe.get_all(STATE_DOCTYPE, filters={"installation": self.installation.name}), [])
