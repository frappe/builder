# Copyright (c) 2026, Frappe Technologies Pvt Ltd and Contributors
# See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase

from builder.builder.tests.extension_fixtures import (
	drop_installations,
	make_installation,
	make_user,
)
from builder.extensions.access import INSTALLATION_DOCTYPE, assert_extension_access, find_own_installation
from builder.extensions.data import record_extension_grant
from builder.extensions.installations import (
	get_uninstall_summary,
	get_user_installations,
	installation_grants,
	set_extension_enabled,
	set_extension_grant,
	set_granted_capabilities,
	uninstall_extension,
)
from builder.extensions.registry import get_enabled_extensions
from builder.extensions.resources import record_resource

EXTENSION = "acme/managed"


def names(installations: list[dict]) -> list[str]:
	return [installation["name"] for installation in installations]


class TestUserInstallations(FrappeTestCase):
	"""The listing the Extensions panel reads, which the editor's own list cannot be."""

	def setUp(self):
		drop_installations(EXTENSION)
		self.addCleanup(frappe.set_user, "Administrator")

	def test_lists_this_users_installation(self):
		make_installation(EXTENSION, version="2.1.0")

		listed = [row for row in get_user_installations() if row["name"] == EXTENSION]

		self.assertEqual(len(listed), 1)
		self.assertEqual(listed[0]["version"], "2.1.0")
		self.assertTrue(listed[0]["enabled"])

	def test_keeps_a_disabled_installation_the_editor_drops(self):
		"""Hiding it would leave no way to turn it back on but the bench."""
		make_installation(EXTENSION, enabled=0)

		self.assertIn(EXTENSION, names(get_user_installations()))
		self.assertNotIn(EXTENSION, names(get_enabled_extensions()))

	def test_leaves_out_a_development_installation(self):
		make_installation(EXTENSION, version="0.0.0-dev")

		self.assertNotIn(EXTENSION, names(get_user_installations()))

	def test_leaves_out_another_users_installation(self):
		make_installation(EXTENSION, user=make_user())

		self.assertNotIn(EXTENSION, names(get_user_installations()))


class TestInstallationDetails(FrappeTestCase):
	"""What a row never shows now sits on the document itself, for the client to read
	directly: the panel keys it off `installation_id` instead of a details call."""

	def setUp(self):
		drop_installations(EXTENSION)
		self.addCleanup(frappe.set_user, "Administrator")

	def test_names_the_document_a_client_reads_the_rest_from(self):
		installation = make_installation(EXTENSION)

		listed = [row for row in get_user_installations() if row["name"] == EXTENSION][0]

		self.assertEqual(listed["installation_id"], installation.name)

	def test_the_document_answers_with_what_a_row_never_shows(self):
		installation = make_installation(
			EXTENSION,
			capabilities=["page.read", "token.write"],
			granted=["page.read"],
			readme="# Managed\n\nIt does one thing.",
		)

		document = frappe.get_doc(INSTALLATION_DOCTYPE, installation.name)

		self.assertEqual(document.requested, ["page.read", "token.write"])
		self.assertEqual(document.capabilities, ["page.read"])
		self.assertIn("It does one thing", document.readme)
		self.assertIsNotNone(document.installed_on)


class TestEnableAndDisable(FrappeTestCase):
	def setUp(self):
		drop_installations(EXTENSION)
		self.addCleanup(frappe.set_user, "Administrator")

	def test_disabling_stops_the_editor_from_listing_it(self):
		make_installation(EXTENSION)

		set_extension_enabled(EXTENSION, False)

		self.assertNotIn(EXTENSION, names(get_enabled_extensions()))
		listed = [row for row in get_user_installations() if row["name"] == EXTENSION][0]
		self.assertFalse(listed["enabled"])

	def test_disabling_closes_the_gate(self):
		make_installation(EXTENSION)
		set_extension_enabled(EXTENSION, False)

		with self.assertRaises(frappe.PermissionError):
			assert_extension_access(EXTENSION, "page.read")

	def test_enabling_opens_it_again(self):
		make_installation(EXTENSION, enabled=0)

		set_extension_enabled(EXTENSION, True)

		self.assertIn(EXTENSION, names(get_enabled_extensions()))


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


class TestUninstall(FrappeTestCase):
	def setUp(self):
		drop_installations(EXTENSION)
		self.addCleanup(frappe.set_user, "Administrator")

	def test_summary_names_what_the_site_keeps(self):
		make_installation(EXTENSION)
		record_resource(EXTENSION, "DocType", "Acme Order")
		make_installation(EXTENSION, user=make_user())

		summary = get_uninstall_summary(EXTENSION)

		self.assertEqual(summary["resources"], [{"resource_type": "DocType", "count": 1}])
		self.assertEqual(summary["other_users"], 1)

	def test_removes_this_users_installation_and_leaves_what_it_made(self):
		make_installation(EXTENSION)
		record_resource(EXTENSION, "DocType", "Acme Order")

		uninstall_extension(EXTENSION)

		self.assertNotIn(EXTENSION, names(get_user_installations()))
		self.assertTrue(frappe.db.exists("Builder Extension Resource", {"extension": EXTENSION}))

	def test_leaves_another_users_installation_standing(self):
		other = make_user()
		make_installation(EXTENSION, user=other)
		make_installation(EXTENSION)

		uninstall_extension(EXTENSION)

		self.assertTrue(frappe.db.exists("Builder User Extension", {"extension": EXTENSION, "user": other}))

	def test_refuses_an_extension_this_user_has_not_installed(self):
		with self.assertRaises(frappe.PermissionError):
			uninstall_extension(EXTENSION)


class TestGrantAnswers(FrappeTestCase):
	"""Narrowing what a user already answered for, one action at a time.

	The gate is the user's own installation, never the extension's access. They
	must reach an answer after disabling the extension or turning `data.access`
	off, which is when they most want it back.
	"""

	def setUp(self):
		drop_installations(EXTENSION)
		self.addCleanup(frappe.set_user, "Administrator")

	def grant(self, **values):
		make_installation(EXTENSION)
		record_extension_grant(EXTENSION, "Contact", **values)

	def test_narrows_one_action_and_keeps_the_rest(self):
		self.grant(access=["read", "write", "delete"])

		grants = set_extension_grant(EXTENSION, "Contact", ["read", "write"])

		self.assertTrue(grants[0]["can_read"])
		self.assertTrue(grants[0]["can_write"])
		self.assertFalse(grants[0]["can_delete"])

	def test_writes_exactly_what_it_is_given_where_recording_merges(self):
		"""`record_extension_grant` never removes. This is what lets a user take back."""
		self.grant(access=["read", "write"])

		grants = set_extension_grant(EXTENSION, "Contact", ["delete"])

		self.assertFalse(grants[0]["can_read"])
		self.assertFalse(grants[0]["can_write"])
		self.assertTrue(grants[0]["can_delete"])

	def test_widens_an_answer_the_user_wants_to_widen(self):
		self.grant(access=["read"])

		grants = set_extension_grant(EXTENSION, "Contact", ["read", "write"])

		self.assertTrue(grants[0]["can_write"])

	def test_allowing_nothing_drops_the_answer_so_it_asks_again(self):
		self.grant(access=["read"])

		self.assertEqual(set_extension_grant(EXTENSION, "Contact", []), [])

	def test_denying_stores_the_refusal_and_clears_the_access(self):
		self.grant(access=["read", "write"])

		grants = set_extension_grant(EXTENSION, "Contact", denied=True)

		self.assertTrue(grants[0]["denied"])
		self.assertFalse(grants[0]["can_read"])
		self.assertFalse(grants[0]["can_write"])

	def test_asking_again_is_the_way_back_from_a_denial(self):
		self.grant(denied=True)
		installation = find_own_installation(EXTENSION)

		set_extension_grant(EXTENSION, "Contact", [])

		self.assertEqual(installation_grants(installation), [])

	def test_refuses_an_access_name_it_does_not_know(self):
		self.grant(access=["read"])

		with self.assertRaises(frappe.ValidationError):
			set_extension_grant(EXTENSION, "Contact", ["publish"])

	def test_answers_a_disabled_extension_the_user_can_still_manage(self):
		self.grant(access=["read"])
		set_extension_enabled(EXTENSION, False)

		self.assertEqual(set_extension_grant(EXTENSION, "Contact", []), [])

	def test_answers_after_the_user_took_data_access_away(self):
		self.grant(access=["read"])
		set_granted_capabilities(EXTENSION, ["block.read"])

		self.assertEqual(set_extension_grant(EXTENSION, "Contact", []), [])

	def test_refuses_an_extension_this_user_has_not_installed(self):
		with self.assertRaises(frappe.PermissionError):
			set_extension_grant(EXTENSION, "Contact", [])
