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
from builder.extensions.access import assert_extension_access, find_installation
from builder.extensions.data import record_doctype_grant
from builder.extensions.installations import (
	get_installations,
	installation_doctype_grants,
	set_doctype_grant,
	set_extension_enabled,
	set_granted_capabilities,
	uninstall_extension,
)

EXTENSION = "acme/managed"


def names(installations: list[dict]) -> list[str]:
	return [installation["name"] for installation in installations]


def become_a_user_who_cannot_manage(test_case):
	set_extension_manager_role(test_case, None)
	frappe.set_user(make_user())


class TestInstallations(FrappeTestCase):
	"""The listing the Extensions panel reads, which the editor's own list cannot be."""

	def setUp(self):
		drop_installations(EXTENSION)
		self.addCleanup(frappe.set_user, "Administrator")

	def test_lists_the_sites_installation(self):
		make_installation(EXTENSION, version="2.1.0")

		listed = [row for row in get_installations() if row["name"] == EXTENSION]

		self.assertEqual(len(listed), 1)
		self.assertEqual(listed[0]["version"], "2.1.0")
		self.assertTrue(listed[0]["enabled"])

	def test_keeps_a_disabled_installation(self):
		"""Hiding it would leave no way to turn it back on but the bench."""
		make_installation(EXTENSION, enabled=0)

		listed = next(row for row in get_installations() if row["name"] == EXTENSION)
		self.assertFalse(listed["enabled"])

	def test_every_builder_user_sees_the_same_list(self):
		make_installation(EXTENSION)
		become_a_user_who_cannot_manage(self)

		self.assertIn(EXTENSION, names(get_installations()))


class TestEnableAndDisable(FrappeTestCase):
	def setUp(self):
		drop_installations(EXTENSION)
		self.addCleanup(frappe.set_user, "Administrator")

	def test_disabling_stops_the_editor_from_listing_it(self):
		make_installation(EXTENSION)

		set_extension_enabled(EXTENSION, False)

		listed = next(row for row in get_installations() if row["name"] == EXTENSION)
		self.assertFalse(listed["enabled"])

	def test_disabling_closes_the_gate(self):
		make_installation(EXTENSION)
		set_extension_enabled(EXTENSION, False)

		with self.assertRaises(frappe.PermissionError):
			assert_extension_access(EXTENSION, "page.read")

	def test_enabling_opens_it_again(self):
		make_installation(EXTENSION, enabled=0)

		set_extension_enabled(EXTENSION, True)

		listed = next(row for row in get_installations() if row["name"] == EXTENSION)
		self.assertTrue(listed["enabled"])

	def test_a_user_with_the_manager_role_can_switch_it(self):
		make_installation(EXTENSION)
		set_extension_manager_role(self, "Website Manager")
		frappe.set_user(make_user())

		set_extension_enabled(EXTENSION, False)

		self.assertFalse(frappe.db.get_value("Builder Extension", {"extension": EXTENSION}, "enabled"))

	def test_refuses_a_user_who_cannot_manage(self):
		make_installation(EXTENSION)
		become_a_user_who_cannot_manage(self)

		with self.assertRaises(frappe.PermissionError):
			set_extension_enabled(EXTENSION, False)


class TestGrantedCapabilities(FrappeTestCase):
	def setUp(self):
		drop_installations(EXTENSION)
		self.addCleanup(frappe.set_user, "Administrator")

	def test_revoking_narrows_what_the_gate_allows(self):
		make_installation(EXTENSION, capabilities=["page.read", "token.write"])

		set_granted_capabilities(EXTENSION, ["page.read"])

		assert_extension_access(EXTENSION, "page.read")
		with self.assertRaises(frappe.PermissionError):
			assert_extension_access(EXTENSION, "token.write")

	def test_granting_again_reopens_it(self):
		make_installation(EXTENSION, capabilities=["page.read", "token.write"], granted=["page.read"])

		set_granted_capabilities(EXTENSION, ["page.read", "token.write"])

		assert_extension_access(EXTENSION, "token.write")

	def test_refuses_a_capability_the_manifest_never_asked_for(self):
		make_installation(EXTENSION, capabilities=["page.read"])

		with self.assertRaises(frappe.ValidationError):
			set_granted_capabilities(EXTENSION, ["page.read", "schema.write"])

	def test_refuses_a_capability_builder_does_not_have(self):
		make_installation(EXTENSION)

		with self.assertRaises(frappe.ValidationError):
			set_granted_capabilities(EXTENSION, ["quantum.read"])

	def test_refuses_a_user_who_cannot_manage(self):
		make_installation(EXTENSION)
		become_a_user_who_cannot_manage(self)

		with self.assertRaises(frappe.PermissionError):
			set_granted_capabilities(EXTENSION, [])


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
		become_a_user_who_cannot_manage(self)

		with self.assertRaises(frappe.PermissionError):
			uninstall_extension(EXTENSION)

	def test_refuses_an_extension_the_site_has_not_installed(self):
		with self.assertRaises(frappe.PermissionError):
			uninstall_extension(EXTENSION)


def answers(read="not asked", write="not asked", delete="not asked") -> dict:
	return {"read": read, "write": write, "delete": delete}


class TestGrantAnswers(FrappeTestCase):
	"""Changing what a manager already answered for, one access at a time.

	The gate is the manager right, never the extension's access. A manager must
	reach an answer after disabling the extension or turning `data.access` off,
	which is when they most want it back.
	"""

	def setUp(self):
		drop_installations(EXTENSION)
		self.addCleanup(frappe.set_user, "Administrator")

	def grant(self, answers):
		make_installation(EXTENSION)
		record_doctype_grant(EXTENSION, "Contact", answers)

	def assertAnswers(self, row, read, write, delete):
		self.assertEqual((row["read"], row["write"], row["delete"]), (read, write, delete))

	def test_narrows_one_access_and_keeps_the_rest(self):
		self.grant({"read": "allowed", "write": "allowed", "delete": "allowed"})

		grants = set_doctype_grant(EXTENSION, "Contact", answers("allowed", "allowed"))

		self.assertAnswers(grants[0], "allowed", "allowed", "not asked")

	def test_denies_one_access_and_keeps_the_rest(self):
		self.grant({"read": "allowed", "write": "allowed"})

		grants = set_doctype_grant(EXTENSION, "Contact", answers("allowed", "denied"))

		self.assertAnswers(grants[0], "allowed", "denied", "not asked")

	def test_not_asked_is_the_way_back_from_a_denial(self):
		self.grant({"read": "denied"})
		installation = find_installation(EXTENSION)

		set_doctype_grant(EXTENSION, "Contact", answers())

		self.assertAnswers(
			installation_doctype_grants(installation)[0], "not asked", "not asked", "not asked"
		)

	def test_refuses_an_answer_it_does_not_know(self):
		self.grant({"read": "allowed"})

		with self.assertRaises(frappe.ValidationError):
			set_doctype_grant(EXTENSION, "Contact", answers(read="maybe"))

	def test_answers_only_the_access_it_names(self):
		self.grant({"read": "allowed", "write": "allowed"})

		grants = set_doctype_grant(EXTENSION, "Contact", {"write": "denied"})

		self.assertAnswers(grants[0], "allowed", "denied", "not asked")

	def test_refuses_an_extension_the_site_has_not_installed(self):
		with self.assertRaises(frappe.PermissionError):
			set_doctype_grant(EXTENSION, "Contact", answers())

	def test_refuses_a_user_who_cannot_manage(self):
		self.grant({"read": "allowed"})
		become_a_user_who_cannot_manage(self)

		with self.assertRaises(frappe.PermissionError):
			set_doctype_grant(EXTENSION, "Contact", answers())
