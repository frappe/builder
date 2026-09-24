# Copyright (c) 2026, Frappe Technologies Pvt Ltd and Contributors
# See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase

from builder.builder.tests.extension_fixtures import (
	drop_installations,
	make_installation,
	make_user,
	set_extension_manager_role,
)
from builder.extensions.access import (
	assert_extension_access,
	assert_extension_manager,
	is_extension_manager,
	owns_state,
	state_conditions,
)

EXTENSION = "acme/gated"


class TestAssertExtensionAccess(FrappeTestCase):
	"""The one gate every protected extension method opens with."""

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

	def test_refuses_a_capability_that_was_not_granted(self):
		make_installation(EXTENSION, capabilities=["page.read"])

		with self.assertRaises(frappe.PermissionError):
			assert_extension_access(EXTENSION, "data.access")

	def test_needs_no_capability_when_the_method_asks_for_none(self):
		make_installation(EXTENSION, capabilities=[])

		self.assertIsNotNone(assert_extension_access(EXTENSION))

	def test_applies_frappes_own_permission_last(self):
		"""The capability says the extension may try. Frappe says whether this user may."""
		make_installation(EXTENSION)
		frappe.set_user(make_user())

		with self.assertRaises(frappe.PermissionError):
			assert_extension_access(EXTENSION, writes="DocType")


class TestExtensionManager(FrappeTestCase):
	"""Who may change the site's extensions. Builder Settings names the role."""

	def setUp(self):
		self.addCleanup(frappe.set_user, "Administrator")

	def test_a_system_manager_always_is_one(self):
		set_extension_manager_role(self, None)

		self.assertTrue(is_extension_manager("Administrator"))

	def test_a_user_with_the_named_role_is_one(self):
		set_extension_manager_role(self, "Website Manager")

		self.assertTrue(is_extension_manager(make_user()))

	def test_a_user_without_the_named_role_is_not(self):
		set_extension_manager_role(self, None)

		self.assertFalse(is_extension_manager(make_user()))

	def test_refuses_a_user_who_is_not_one(self):
		set_extension_manager_role(self, None)
		frappe.set_user(make_user())

		with self.assertRaises(frappe.PermissionError):
			assert_extension_manager()


class TestStateRowScoping(FrappeTestCase):
	"""What Desk, a report and a get_all see of stored state. `state.py` enforces this too."""

	def test_a_system_manager_sees_every_row(self):
		self.assertEqual(state_conditions("Administrator"), "")

	def test_another_user_sees_only_their_own(self):
		theirs = make_user()

		self.assertIn(frappe.db.escape(theirs), state_conditions(theirs))

	def test_a_user_owns_only_their_own_row(self):
		theirs = make_user()
		row = frappe._dict(user=theirs)

		self.assertTrue(owns_state(row, user=theirs))
		self.assertTrue(owns_state(row, user="Administrator"))
		self.assertFalse(owns_state(row, user="Guest"))
