# Copyright (c) 2026, Frappe Technologies Pvt Ltd and Contributors
# See license.txt

from unittest.mock import patch

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
	get_installations,
	get_uninstall_summary,
	set_extension_enabled,
	set_granted_permissions,
	uninstall_extension,
)

EXTENSION = "acme/managed"


def names(installations: list[dict]) -> list[str]:
	return [installation["name"] for installation in installations]


def become_a_user_who_cannot_manage(test_case):
	frappe.set_user(make_page_reader(test_case))


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


class TestEnableAndDisable(FrappeTestCase):
	def setUp(self):
		drop_installations(EXTENSION)
		self.addCleanup(frappe.set_user, "Administrator")

	def test_disabling_closes_the_gate(self):
		make_installation(EXTENSION)
		set_extension_enabled(EXTENSION, False)

		with self.assertRaises(frappe.PermissionError):
			assert_extension_access(EXTENSION, "page.edit")

	def test_enabling_opens_it_again(self):
		make_installation(EXTENSION, enabled=0)

		set_extension_enabled(EXTENSION, True)

		listed = next(row for row in get_installations() if row["name"] == EXTENSION)
		self.assertTrue(listed["enabled"])

	def test_a_website_manager_can_switch_it(self):
		make_installation(EXTENSION)
		frappe.set_user(make_user())

		set_extension_enabled(EXTENSION, False)

		self.assertFalse(frappe.db.get_value("Builder Extension", {"extension": EXTENSION}, "enabled"))

	def test_refuses_a_user_who_cannot_manage(self):
		make_installation(EXTENSION)
		become_a_user_who_cannot_manage(self)

		with self.assertRaises(frappe.PermissionError):
			set_extension_enabled(EXTENSION, False)


class TestGrantedPermissions(FrappeTestCase):
	def setUp(self):
		drop_installations(EXTENSION)
		self.addCleanup(frappe.set_user, "Administrator")

	def test_revoking_narrows_what_the_gate_allows(self):
		make_installation(EXTENSION, permissions=["page.edit", "data.access"])

		set_granted_permissions(EXTENSION, ["page.edit"])

		assert_extension_access(EXTENSION, "page.edit")
		with self.assertRaises(frappe.PermissionError):
			assert_extension_access(EXTENSION, "data.access")

	def test_refuses_a_permission_the_manifest_never_asked_for(self):
		make_installation(EXTENSION, permissions=["page.edit"])

		with self.assertRaises(frappe.ValidationError):
			set_granted_permissions(EXTENSION, ["page.edit", "schema.write"])

	def test_refuses_a_user_who_cannot_manage(self):
		make_installation(EXTENSION)
		become_a_user_who_cannot_manage(self)

		with self.assertRaises(frappe.PermissionError):
			set_granted_permissions(EXTENSION, [])


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


class TestListedInstallation(FrappeTestCase):
	"""What one row of the list carries for the editor to mount."""

	def listed(self, name):
		return next((row for row in get_installations() if row["name"] == name), None)

	def test_a_page_reader_gets_the_grants_without_reading_the_installation(self):
		"""The editor builds an extension from this row alone. A page reader cannot read the document."""
		make_installation("acme/light", permissions=["page.edit"])
		become_a_user_who_cannot_manage(self)
		self.addCleanup(frappe.set_user, "Administrator")

		self.assertFalse(frappe.has_permission("Builder Extension", "read"))
		self.assertEqual(self.listed("acme/light")["permissions"], ["page.edit"])

	def test_an_install_whose_job_is_gone_reads_as_failed(self):
		"""A crashed worker cannot mark its row. So the panel offers a retry, not a spinner."""
		make_installation("acme/light", install_state="Installing", enabled=0)

		with patch("builder.extensions.installations.is_job_enqueued", return_value=False):
			self.assertEqual(self.listed("acme/light")["install_state"], "Failed")


class TestExtensionIcon(FrappeTestCase):
	def test_refuses_a_path_that_climbs_out_of_the_install_folder(self):
		with self.assertRaises(frappe.ValidationError):
			make_installation("acme/climber", icon="../../secrets.svg")


class TestUninstallSummary(FrappeTestCase):
	def setUp(self):
		drop_installations(EXTENSION)
		frappe.db.delete("Builder Extension Resource", {"extension": EXTENSION})

	def record(self, doctype, created):
		frappe.get_doc(
			{
				"doctype": "Builder Extension Resource",
				"extension": EXTENSION,
				"resource_type": "DocType",
				"resource_name": doctype,
				"resource_created": created,
			}
		).insert()

	def test_names_what_the_site_keeps(self):
		make_installation(EXTENSION)
		self.record("Contact", frappe.db.get_value("DocType", "Contact", "creation"))

		summary = get_uninstall_summary(EXTENSION)

		self.assertEqual(summary["resources"], [{"resource_type": "DocType", "count": 1}])
