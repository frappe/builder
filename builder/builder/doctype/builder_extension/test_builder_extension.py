# Copyright (c) 2026, Frappe Technologies Pvt Ltd and contributors
# See license.txt

from pathlib import Path

import frappe
from frappe.tests.utils import FrappeTestCase

from builder.builder.tests.extension_fixtures import (
	INSTALLATION_DOCTYPE,
	drop_installations,
	make_installation,
)

EXTENSION = "acme/record"


class TestBuilderExtension(FrappeTestCase):
	"""The site's one record of an extension."""

	def setUp(self):
		drop_installations(EXTENSION)

	def test_the_files_are_private_and_named_by_the_record(self):
		installation = make_installation(EXTENSION)

		self.assertIn("/private/files/extensions/", installation.install_path)
		self.assertTrue(installation.install_path.endswith(installation.name))

	def test_a_second_install_of_one_name_is_refused_whatever_the_source(self):
		"""`publisher/name` is the whole identity, so a second source is not a second install."""
		make_installation(EXTENSION, source_url="https://hub.example")

		second = frappe.get_doc(
			{
				"doctype": INSTALLATION_DOCTYPE,
				"extension": EXTENSION,
				"version": "2.0.0",
				"source_url": "https://other.example",
			}
		)
		self.assertRaises(Exception, second.insert)

	def test_refuses_a_name_that_is_not_publisher_slash_name(self):
		for name in ("icons", "Acme/Icons", "acme/icons/extra", ""):
			with self.assertRaises(frappe.ValidationError, msg=name):
				make_installation(name)

	def test_refuses_a_version_that_could_be_a_path(self):
		with self.assertRaises(frappe.ValidationError):
			make_installation(EXTENSION, version="../1.0.0")

	def test_refuses_a_permission_this_builder_does_not_have(self):
		with self.assertRaises(frappe.ValidationError):
			make_installation(EXTENSION, permissions=["quantum.read"])

	def test_refuses_a_grant_the_manifest_never_asked_for(self):
		"""A manager can only ever answer a question the extension asked."""
		with self.assertRaises(frappe.ValidationError):
			make_installation(EXTENSION, permissions=["page.edit"], granted=["page.edit", "schema.write"])

	def test_writes_the_files_it_installs(self):
		installation = make_installation(EXTENSION)
		installation.write_extension_files({"main.js": b"export const ok = true;", "chunks/a.js": b""})

		root = Path(installation.install_path)
		self.assertEqual((root / "main.js").read_text(), "export const ok = true;")
		self.assertTrue((root / "chunks" / "a.js").is_file())

	def test_uninstall_takes_the_files(self):
		installation = make_installation(EXTENSION, source="export default {};")
		install_path = Path(installation.install_path)
		self.assertTrue(install_path.is_dir())

		installation.delete()
		self.assertTrue(install_path.is_dir(), "files must wait for the commit")

		frappe.db.after_commit.run()
		self.assertFalse(install_path.exists())


class TestInstalledFiles(FrappeTestCase):
	def setUp(self):
		drop_installations(EXTENSION)

	def test_finds_no_file_outside_the_install(self):
		installation = make_installation(EXTENSION, source="export default {};")
		sibling = make_installation("acme/sibling", source="export const secret = 1;")
		self.addCleanup(drop_installations, "acme/sibling")

		self.assertIsNone(installation.get_asset_path(f"../{sibling.name}/main.js"))
