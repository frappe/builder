# Copyright (c) 2026, Frappe Technologies Pvt Ltd and Contributors
# See license.txt


import frappe
from frappe.tests.utils import FrappeTestCase

from builder.builder.tests.plugin_fixtures import (
	drop_installations,
	make_installation,
	make_page_reader,
	make_user,
)
from builder.plugins.access import assert_plugin_access
from builder.plugins.installations import (
	can_manage_plugins,
	get_installations,
	set_plugin_enabled,
	uninstall_plugin,
)

PLUGIN = "acme/managed"


def names(installations: list[dict]) -> list[str]:
	return [installation["name"] for installation in installations]


def listed(name):
	return next((row for row in get_installations() if row["name"] == name), None)


class TestInstallations(FrappeTestCase):
	"""The listing the Plugins panel and the editor read."""

	def setUp(self):
		drop_installations(PLUGIN)
		self.addCleanup(frappe.set_user, "Administrator")

	def test_lists_the_sites_installation_with_its_entry(self):
		installation = make_installation(PLUGIN, version="2.1.0", hub_url="https://hub.example.com")

		row = listed(PLUGIN)

		self.assertEqual(row["version"], "2.1.0")
		self.assertEqual([row["source"], row["hub_url"]], ["Hub", "https://hub.example.com"])
		self.assertTrue(row["enabled"])
		self.assertEqual(row["entry_url"], f"/files/builder_plugins/{installation.name}/sum123/main.js")

	def test_a_page_reader_gets_the_list_without_reading_the_installation(self):
		"""The editor loads a plugin from this row alone. A page reader cannot read the document."""
		make_installation(PLUGIN)
		frappe.set_user(make_page_reader(self))

		self.assertFalse(frappe.has_permission("Builder Plugin", "read"))
		self.assertEqual(listed(PLUGIN)["name"], PLUGIN)


class TestEnableAndDisable(FrappeTestCase):
	def setUp(self):
		drop_installations(PLUGIN)
		self.addCleanup(frappe.set_user, "Administrator")

	def test_disabling_stops_its_state_calls(self):
		make_installation(PLUGIN)
		set_plugin_enabled(PLUGIN, False)

		with self.assertRaises(frappe.PermissionError):
			assert_plugin_access(PLUGIN)

	def test_enabling_turns_it_back_on(self):
		make_installation(PLUGIN, enabled=0)

		set_plugin_enabled(PLUGIN, True)

		self.assertTrue(listed(PLUGIN)["enabled"])

	def test_a_website_manager_can_manage(self):
		make_installation(PLUGIN)
		frappe.set_user(make_user())

		self.assertTrue(can_manage_plugins())
		set_plugin_enabled(PLUGIN, False)
		self.assertFalse(listed(PLUGIN)["enabled"])

	def test_refuses_a_user_who_cannot_manage(self):
		make_installation(PLUGIN)
		frappe.set_user(make_page_reader(self))

		self.assertFalse(can_manage_plugins())
		with self.assertRaises(frappe.PermissionError):
			set_plugin_enabled(PLUGIN, False)


class TestUninstall(FrappeTestCase):
	def setUp(self):
		drop_installations(PLUGIN)
		self.addCleanup(frappe.set_user, "Administrator")

	def test_removes_the_sites_installation(self):
		make_installation(PLUGIN)

		uninstall_plugin(PLUGIN)

		self.assertNotIn(PLUGIN, names(get_installations()))

	def test_refuses_a_user_who_cannot_manage(self):
		make_installation(PLUGIN)
		frappe.set_user(make_page_reader(self))

		with self.assertRaises(frappe.PermissionError):
			uninstall_plugin(PLUGIN)
