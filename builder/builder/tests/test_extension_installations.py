# Copyright (c) 2026, Frappe Technologies Pvt Ltd and Contributors
# See license.txt


import frappe
from frappe.tests.utils import FrappeTestCase

from builder.builder.tests.extension_fixtures import (
	drop_installations,
	make_installation,
	make_page_reader,
	make_user,
)
from builder.extensions.access import assert_extension_access
from builder.extensions.installations import (
	can_manage_extensions,
	get_installations,
	set_extension_enabled,
	uninstall_extension,
)

EXTENSION = "acme/managed"


def names(installations: list[dict]) -> list[str]:
	return [installation["name"] for installation in installations]


def listed(name):
	return next((row for row in get_installations() if row["name"] == name), None)


class TestInstallations(FrappeTestCase):
	"""The listing the Extensions panel and the editor read."""

	def setUp(self):
		drop_installations(EXTENSION)
		self.addCleanup(frappe.set_user, "Administrator")

	def test_lists_the_sites_installation_with_its_entry(self):
		installation = make_installation(EXTENSION, version="2.1.0")

		row = listed(EXTENSION)

		self.assertEqual(row["version"], "2.1.0")
		self.assertTrue(row["enabled"])
		self.assertEqual(row["entry_url"], f"/files/builder_extensions/{installation.name}/sum123/main.js")

	def test_a_page_reader_gets_the_list_without_reading_the_installation(self):
		"""The editor loads an extension from this row alone. A page reader cannot read the document."""
		make_installation(EXTENSION)
		frappe.set_user(make_page_reader(self))

		self.assertFalse(frappe.has_permission("Builder Extension", "read"))
		self.assertEqual(listed(EXTENSION)["name"], EXTENSION)


class TestEnableAndDisable(FrappeTestCase):
	def setUp(self):
		drop_installations(EXTENSION)
		self.addCleanup(frappe.set_user, "Administrator")

	def test_disabling_stops_its_state_calls(self):
		make_installation(EXTENSION)
		set_extension_enabled(EXTENSION, False)

		with self.assertRaises(frappe.PermissionError):
			assert_extension_access(EXTENSION)

	def test_enabling_turns_it_back_on(self):
		make_installation(EXTENSION, enabled=0)

		set_extension_enabled(EXTENSION, True)

		self.assertTrue(listed(EXTENSION)["enabled"])

	def test_a_website_manager_can_manage(self):
		make_installation(EXTENSION)
		frappe.set_user(make_user())

		self.assertTrue(can_manage_extensions())
		set_extension_enabled(EXTENSION, False)
		self.assertFalse(listed(EXTENSION)["enabled"])

	def test_refuses_a_user_who_cannot_manage(self):
		make_installation(EXTENSION)
		frappe.set_user(make_page_reader(self))

		self.assertFalse(can_manage_extensions())
		with self.assertRaises(frappe.PermissionError):
			set_extension_enabled(EXTENSION, False)


class TestUninstall(FrappeTestCase):
	def setUp(self):
		drop_installations(EXTENSION)
		self.addCleanup(frappe.set_user, "Administrator")

	def test_removes_the_sites_installation(self):
		make_installation(EXTENSION)

		uninstall_extension(EXTENSION)

		self.assertNotIn(EXTENSION, names(get_installations()))

	def test_refuses_a_user_who_cannot_manage(self):
		make_installation(EXTENSION)
		frappe.set_user(make_page_reader(self))

		with self.assertRaises(frappe.PermissionError):
			uninstall_extension(EXTENSION)
