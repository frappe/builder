# Copyright (c) 2026, Frappe Technologies Pvt Ltd and Contributors
# See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase

from builder.builder.tests.extension_fixtures import (
	drop_installations,
	make_installation,
	make_user,
)
from builder.extensions.access import (
	assert_extension_access,
	assert_extension_manager,
	is_extension_manager,
)

EXTENSION = "acme/gated"


class TestAssertExtensionAccess(FrappeTestCase):
	"""Tests the checks that each protected extension method runs first."""

	def setUp(self):
		drop_installations(EXTENSION)
		self.addCleanup(frappe.set_user, "Administrator")

	def test_answers_with_the_installation_name(self):
		installation = make_installation(EXTENSION)

		self.assertEqual(assert_extension_access(EXTENSION, "data.access"), installation.name)

	def test_every_builder_user_reaches_the_sites_installation(self):
		installation = make_installation(EXTENSION)
		frappe.set_user(make_user())

		self.assertEqual(assert_extension_access(EXTENSION), installation.name)

	def test_refuses_a_guest(self):
		make_installation(EXTENSION)
		frappe.set_user("Guest")

		with self.assertRaises(frappe.PermissionError):
			assert_extension_access(EXTENSION)

	def test_refuses_a_user_who_cannot_read_a_builder_page(self):
		"""The checks look at Builder access before the installation."""
		make_installation(EXTENSION)
		frappe.set_user(make_user("extension-outsider@example.com", roles=()))

		with self.assertRaises(frappe.PermissionError):
			assert_extension_access(EXTENSION)

	def test_refuses_an_extension_the_site_has_not_installed(self):
		with self.assertRaises(frappe.PermissionError):
			assert_extension_access(EXTENSION)

	def test_refuses_an_installation_that_is_switched_off(self):
		make_installation(EXTENSION, enabled=0)

		with self.assertRaises(frappe.PermissionError):
			assert_extension_access(EXTENSION)

	def test_refuses_a_permission_that_was_not_granted(self):
		make_installation(EXTENSION, permissions=["page.edit"])

		with self.assertRaises(frappe.PermissionError):
			assert_extension_access(EXTENSION, "data.access")

	def test_needs_no_permission_when_the_method_asks_for_none(self):
		make_installation(EXTENSION, permissions=[])

		self.assertIsNotNone(assert_extension_access(EXTENSION))


class TestExtensionManager(FrappeTestCase):
	"""Tests who can change the extensions of the site."""

	def setUp(self):
		self.addCleanup(frappe.set_user, "Administrator")
		self.outsider = make_user("extension-outsider@example.com", roles=())

	def test_a_system_manager_is_one(self):
		self.assertTrue(is_extension_manager("Administrator"))

	def test_a_website_manager_is_one(self):
		self.assertTrue(is_extension_manager(make_user()))

	def test_a_user_without_either_role_is_not(self):
		self.assertFalse(is_extension_manager(self.outsider))

	def test_refuses_a_user_who_is_not_one(self):
		frappe.set_user(self.outsider)

		with self.assertRaises(frappe.PermissionError):
			assert_extension_manager()
