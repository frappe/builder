# Copyright (c) 2026, Frappe Technologies Pvt Ltd and Contributors
# See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase

from builder.builder.tests.extension_fixtures import drop_installations, make_installation, write_source

EXTENSION = "acme/released"


class TestBuilderExtension(FrappeTestCase):
	def setUp(self):
		drop_installations(EXTENSION)
		self.addCleanup(drop_installations, EXTENSION)

	def test_each_release_has_its_own_folder_and_url(self):
		installation = make_installation(EXTENSION, checksum="first", source="// 1")
		first = installation.release_path

		installation.checksum = "second"
		write_source(installation, "// 2")
		installation.save()

		self.assertTrue(first.is_dir(), "the old release stays until the commit")
		frappe.db.after_commit.run()
		self.assertFalse(first.is_dir())
		self.assertEqual((installation.release_path / "main.js").read_text(), "// 2")
		self.assertTrue(installation.entry_url.endswith("/second/main.js"))

	def test_a_rolled_back_delete_keeps_the_files(self):
		installation = make_installation(EXTENSION, source="// 1")

		installation.delete()
		frappe.db.rollback()

		self.assertTrue(installation.release_path.is_dir())

	def test_a_delete_removes_the_files_after_the_commit(self):
		installation = make_installation(EXTENSION, source="// 1")

		installation.delete()
		frappe.db.after_commit.run()

		self.assertFalse(installation.install_path.exists())
