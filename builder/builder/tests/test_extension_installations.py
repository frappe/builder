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
	installation_doctype_grants,
	set_extension_enabled,
	set_extension_grant,
	set_granted_capabilities,
	uninstall_extension,
)
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

	def test_keeps_a_disabled_installation(self):
		"""Hiding it would leave no way to turn it back on but the bench."""
		make_installation(EXTENSION, enabled=0)

		listed = [row for row in get_user_installations() if row["name"] == EXTENSION][0]
		self.assertFalse(listed["enabled"])

	def test_marks_a_development_installation(self):
		"""The panel opens its record by id, so the list cannot leave it out."""
		installation = make_installation(EXTENSION, version="0.0.0-dev")

		listed = [row for row in get_user_installations() if row["name"] == EXTENSION][0]
		self.assertEqual(listed["installation_id"], installation.name)
		self.assertTrue(listed["is_development"])

	def test_does_not_mark_an_installed_release(self):
		make_installation(EXTENSION, version="1.0.0")

		listed = [row for row in get_user_installations() if row["name"] == EXTENSION][0]
		self.assertFalse(listed["is_development"])

	def test_leaves_out_another_users_installation(self):
		make_installation(EXTENSION, user=make_user())

		self.assertNotIn(EXTENSION, names(get_user_installations()))

	def test_lists_enabled_first_and_the_last_edited_first_in_each_group(self):
		"""A pending install is not enabled yet, but it is not one the user turned off.

		The disabled row is the last edited, so only the grouping can put it last.
		"""
		disabled, pending, older, newer = (
			f"{EXTENSION}-{suffix}" for suffix in ("off", "pending", "old", "new")
		)
		ordered = [newer, older, pending, disabled]
		for extension in ordered:
			drop_installations(extension)
			self.addCleanup(drop_installations, extension)

		edited = {
			disabled: ("2026-04-01", {"enabled": 0}),
			pending: ("2026-01-01", {"enabled": 0, "install_state": "Installing"}),
			older: ("2026-02-01", {}),
			newer: ("2026-03-01", {}),
		}
		for extension, (modified, values) in edited.items():
			installation = make_installation(extension, **values)
			frappe.db.set_value(
				INSTALLATION_DOCTYPE, installation.name, "modified", modified, update_modified=False
			)

		self.assertEqual([name for name in names(get_user_installations()) if name in edited], ordered)


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

		listed = [row for row in get_user_installations() if row["name"] == EXTENSION][0]
		self.assertTrue(listed["enabled"])


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


def answers(read="not asked", write="not asked", delete="not asked") -> dict:
	return {"read": read, "write": write, "delete": delete}


class TestGrantAnswers(FrappeTestCase):
	"""Changing what a user already answered for, one access at a time.

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

	def assertAnswers(self, row, read, write, delete):
		self.assertEqual(
			(row["read_access"], row["write_access"], row["delete_access"]), (read, write, delete)
		)

	def test_narrows_one_access_and_keeps_the_rest(self):
		self.grant(access=["read", "write", "delete"])

		grants = set_extension_grant(EXTENSION, "Contact", answers("allowed", "allowed"))

		self.assertAnswers(grants[0], "allowed", "allowed", "not asked")

	def test_denies_one_access_and_keeps_the_rest(self):
		self.grant(access=["read", "write"])

		grants = set_extension_grant(EXTENSION, "Contact", answers("allowed", "denied"))

		self.assertAnswers(grants[0], "allowed", "denied", "not asked")

	def test_writes_exactly_what_it_is_given_where_recording_merges(self):
		"""`record_extension_grant` never removes. This is what lets a user take back."""
		self.grant(access=["read", "write"])

		grants = set_extension_grant(EXTENSION, "Contact", answers(delete="allowed"))

		self.assertAnswers(grants[0], "not asked", "not asked", "allowed")

	def test_widens_an_answer_the_user_wants_to_widen(self):
		self.grant(access=["read"])

		grants = set_extension_grant(EXTENSION, "Contact", answers("allowed", "allowed"))

		self.assertEqual(grants[0]["write_access"], "allowed")

	def test_three_not_asked_answers_keep_the_row_so_the_panel_lists_it(self):
		self.grant(access=["read"])

		grants = set_extension_grant(EXTENSION, "Contact", answers())

		self.assertEqual(len(grants), 1)
		self.assertAnswers(grants[0], "not asked", "not asked", "not asked")

	def test_not_asked_is_the_way_back_from_a_denial(self):
		self.grant(access=["read"], denied=True)
		installation = find_own_installation(EXTENSION)

		set_extension_grant(EXTENSION, "Contact", answers())

		self.assertAnswers(
			installation_doctype_grants(installation)[0], "not asked", "not asked", "not asked"
		)

	def test_refuses_an_answer_it_does_not_know(self):
		self.grant(access=["read"])

		with self.assertRaises(frappe.ValidationError):
			set_extension_grant(EXTENSION, "Contact", answers(read="maybe"))

	def test_refuses_answers_that_leave_an_access_out(self):
		self.grant(access=["read"])

		with self.assertRaises(frappe.ValidationError):
			set_extension_grant(EXTENSION, "Contact", {"read": "allowed"})

	def test_answers_a_disabled_extension_the_user_can_still_manage(self):
		self.grant(access=["read"])
		set_extension_enabled(EXTENSION, False)

		self.assertEqual(set_extension_grant(EXTENSION, "Contact", answers())[0]["read_access"], "not asked")

	def test_answers_after_the_user_took_data_access_away(self):
		self.grant(access=["read"])
		set_granted_capabilities(EXTENSION, ["block.read"])

		self.assertEqual(set_extension_grant(EXTENSION, "Contact", answers())[0]["read_access"], "not asked")

	def test_refuses_an_extension_this_user_has_not_installed(self):
		with self.assertRaises(frappe.PermissionError):
			set_extension_grant(EXTENSION, "Contact", answers())
