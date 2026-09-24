# Copyright (c) 2026, Frappe Technologies Pvt Ltd and contributors
# See license.txt

from pathlib import Path

import frappe
from frappe.tests.utils import FrappeTestCase

from builder.builder.tests.extension_fixtures import (
	INSTALLATION_DOCTYPE,
	drop_installations,
	make_installation,
	make_user,
)

EXTENSION = "acme/record"


class TestBuilderUserExtension(FrappeTestCase):
	"""The one extension record. There is no site-wide one."""

	def setUp(self):
		# a grant Links to the installation, so dropping the copy takes the grant
		drop_installations(EXTENSION)

	def test_the_files_are_private_and_named_by_the_record(self):
		installation = make_installation(EXTENSION)

		self.assertIn("/private/files/extensions/", installation.install_path)
		self.assertTrue(installation.install_path.endswith(installation.name))

	def test_one_installation_per_user_and_extension(self):
		make_installation(EXTENSION)

		second = frappe.get_doc(
			{
				"doctype": INSTALLATION_DOCTYPE,
				"user": frappe.session.user,
				"extension": EXTENSION,
				"version": "2.0.0",
			}
		)
		self.assertRaises(Exception, second.insert)

	def test_a_second_install_of_one_name_is_refused_whatever_the_source(self):
		"""`publisher/name` is the whole identity, so a second source is not a second install."""
		make_installation(EXTENSION, source_url="https://hub.example")

		second = frappe.get_doc(
			{
				"doctype": INSTALLATION_DOCTYPE,
				"user": frappe.session.user,
				"extension": EXTENSION,
				"version": "2.0.0",
				"source_url": "https://other.example",
			}
		)
		self.assertRaises(Exception, second.insert)

	def test_two_users_hold_the_same_extension_separately(self):
		mine = make_installation(EXTENSION)
		theirs = make_installation(EXTENSION, user=make_user(), version="2.0.0")

		self.assertNotEqual(mine.name, theirs.name)
		self.assertNotEqual(mine.install_path, theirs.install_path)

	def test_refuses_a_name_that_is_not_publisher_slash_name(self):
		for name in ("icons", "Acme/Icons", "acme/icons/extra", ""):
			with self.assertRaises(frappe.ValidationError, msg=name):
				make_installation(name)

	def test_refuses_a_version_that_could_be_a_path(self):
		with self.assertRaises(frappe.ValidationError):
			make_installation(EXTENSION, version="../1.0.0")

	def test_refuses_a_capability_this_builder_does_not_have(self):
		with self.assertRaises(frappe.ValidationError):
			make_installation(EXTENSION, capabilities=["quantum.read"])

	def test_refuses_a_grant_the_manifest_never_asked_for(self):
		"""The user can only ever answer a question the extension asked."""
		with self.assertRaises(frappe.ValidationError):
			make_installation(EXTENSION, capabilities=["page.read"], granted=["page.read", "schema.write"])

	def test_reads_the_entry_it_installed(self):
		installation = make_installation(EXTENSION, source="export const ok = true;")

		self.assertEqual(installation.source, "export const ok = true;")

	def test_uninstall_takes_this_users_files(self):
		installation = make_installation(EXTENSION, source="export default {};")
		install_path = Path(installation.install_path)
		self.assertTrue(install_path.is_dir())

		installation.delete()

		self.assertFalse(install_path.exists())

	def test_uninstall_takes_this_users_state_and_grants(self):
		installation = make_installation(EXTENSION)
		frappe.get_doc(
			{
				"doctype": "Builder Extension State",
				"installation": installation.name,
				"key": "theme",
				"value": '"dark"',
			}
		).insert()
		frappe.get_doc(
			{
				"doctype": "Builder Extension DocType Grant",
				"installation": installation.name,
				"document_type": "Contact",
				"read": "allowed",
			}
		).insert()

		installation.delete()

		self.assertFalse(frappe.db.exists("Builder Extension State", {"installation": installation.name}))
		self.assertFalse(
			frappe.db.exists("Builder Extension DocType Grant", {"installation": installation.name})
		)

	def test_uninstall_leaves_another_users_grants_alone(self):
		installation = make_installation(EXTENSION)
		theirs = make_installation(EXTENSION, user=make_user())
		frappe.get_doc(
			{
				"doctype": "Builder Extension DocType Grant",
				"installation": theirs.name,
				"document_type": "Contact",
				"read": "allowed",
			}
		).insert()

		installation.delete()

		self.assertTrue(frappe.db.exists("Builder Extension DocType Grant", {"installation": theirs.name}))
