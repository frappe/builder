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
	is_extension_manager,
)

EXTENSION = "acme/gated"


class TestAssertExtensionAccess(FrappeTestCase):
	"""The one gate every protected extension method opens with."""

	def setUp(self):
		drop_installations(EXTENSION)
		self.addCleanup(frappe.set_user, "Administrator")

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
		"""Builder access is the second gate, checked before any installation."""
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


class TestExtensionManager(FrappeTestCase):
	"""Who may change the site's extensions."""

	def setUp(self):
		self.addCleanup(frappe.set_user, "Administrator")
		self.outsider = make_user("extension-outsider@example.com", roles=())

	def test_a_website_manager_is_one(self):
		self.assertTrue(is_extension_manager(make_user()))

	def test_a_user_without_either_role_is_not(self):
		self.assertFalse(is_extension_manager(self.outsider))
