# Copyright (c) 2026, Frappe Technologies Pvt Ltd and Contributors
# See license.txt

from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import set_request

from builder.builder.tests.extension_fixtures import (
	drop_installations,
	make_installation,
	make_page_reader,
	make_user,
)
from builder.extensions.access import assert_extension_access
from builder.extensions.installations import (
	get_extension_source,
	get_installations,
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
		make_installation(EXTENSION, permissions=["page.read", "token.write"])

		set_granted_permissions(EXTENSION, ["page.read"])

		assert_extension_access(EXTENSION, "page.read")
		with self.assertRaises(frappe.PermissionError):
			assert_extension_access(EXTENSION, "token.write")

	def test_granting_again_reopens_it(self):
		make_installation(EXTENSION, permissions=["page.read", "token.write"], granted=["page.read"])

		set_granted_permissions(EXTENSION, ["page.read", "token.write"])

		assert_extension_access(EXTENSION, "token.write")

	def test_refuses_a_permission_the_manifest_never_asked_for(self):
		make_installation(EXTENSION, permissions=["page.read"])

		with self.assertRaises(frappe.ValidationError):
			set_granted_permissions(EXTENSION, ["page.read", "schema.write"])

	def test_refuses_a_permission_builder_does_not_have(self):
		make_installation(EXTENSION)

		with self.assertRaises(frappe.ValidationError):
			set_granted_permissions(EXTENSION, ["quantum.read"])

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

	def test_refuses_an_extension_the_site_has_not_installed(self):
		with self.assertRaises(frappe.PermissionError):
			uninstall_extension(EXTENSION)


class TestListedInstallation(FrappeTestCase):
	"""What one row of the list carries for the editor to mount."""

	def listed(self, name):
		return next((row for row in get_installations() if row["name"] == name), None)

	def test_carries_no_source(self):
		"""One call per extension reads that, so a list of five carries no bundles."""
		make_installation("acme/light", source="export default {};")

		self.assertNotIn("source", self.listed("acme/light"))


class TestExtensionIcon(FrappeTestCase):
	def test_refuses_a_path_that_climbs_out_of_the_install_folder(self):
		with self.assertRaises(frappe.ValidationError):
			make_installation("acme/climber", icon="../../secrets.svg")


class TestGetExtensionSource(FrappeTestCase):
	def fetch(self, extension, etag=None):
		"""Calls the endpoint the way the editor does, and reads the streamed body."""
		set_request(method="GET", headers={"If-None-Match": etag} if etag else {})
		response = get_extension_source(extension)
		self.addCleanup(response.close)
		return response

	def body(self, response):
		return b"".join(response.response).decode()

	def test_streams_the_entry_the_site_installed(self):
		make_installation("acme/coded", source="export const answer = 42;")

		response = self.fetch("acme/coded")

		self.assertEqual(self.body(response), "export const answer = 42;")
		self.assertEqual(response.mimetype, "text/javascript")
		self.assertEqual(response.headers["ETag"], '"sum123"')

	def test_answers_an_unchanged_build_with_not_modified(self):
		make_installation("acme/cached", source="export default {};")

		self.assertEqual(self.fetch("acme/cached", etag='"sum123"').status_code, 304)

	def test_streams_again_after_a_rebuild(self):
		make_installation("acme/rebuilt", source="export default {};", checksum="sum456")

		self.assertEqual(self.fetch("acme/rebuilt", etag='"sum123"').status_code, 200)

	def test_refuses_an_extension_the_site_has_not_installed(self):
		drop_installations("acme/absent")

		with self.assertRaises(frappe.PermissionError):
			self.fetch("acme/absent")

	def test_every_builder_user_reads_the_sites_entry(self):
		make_installation("acme/shared", source="export const shared = 1;")
		frappe.set_user(make_user())
		self.addCleanup(frappe.set_user, "Administrator")

		self.assertEqual(self.body(self.fetch("acme/shared")), "export const shared = 1;")

	def test_refuses_an_installation_that_is_switched_off(self):
		make_installation("acme/paused", enabled=0, source="export default {};")

		with self.assertRaises(frappe.PermissionError):
			self.fetch("acme/paused")

	def test_refuses_an_entry_larger_than_the_cap(self):
		"""The frame parses the whole module, so the cap still bounds what it holds."""
		make_installation("acme/heavy", source="x" * 200)

		module = "builder.builder.doctype.builder_extension.builder_extension"
		with patch(f"{module}.MAX_SOURCE_BYTES", 100):
			with self.assertRaises(frappe.ValidationError):
				self.fetch("acme/heavy")
