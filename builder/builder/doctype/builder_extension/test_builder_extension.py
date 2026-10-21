# Copyright (c) 2026, Frappe Technologies Pvt Ltd and Contributors
# See license.txt

from pathlib import Path
from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

from builder.builder.tests.extension_fixtures import drop_installations, make_installation, write_source

EXTENSION = "acme/released"


class TestBuilderExtension(FrappeTestCase):
	def setUp(self):
		drop_installations(EXTENSION)
		self.addCleanup(drop_installations, EXTENSION)

	def release(self, installation, checksum: str, source: str):
		installation.checksum = checksum
		write_source(installation, source)
		installation.save()
		frappe.db.after_commit.run()

	def test_each_release_has_its_own_folder_and_url(self):
		installation = make_installation(EXTENSION, checksum="first", source="// 1")
		first = installation.release_path

		self.release(installation, "second", "// 2")

		self.assertEqual((installation.release_path / "main.js").read_text(), "// 2")
		self.assertTrue(installation.entry_url.endswith("/second/main.js"))
		self.assertTrue(first.is_dir(), "an open tab still runs the previous release")

		self.release(installation, "third", "// 3")
		self.assertFalse(first.is_dir())

	def test_a_save_with_the_same_release_keeps_the_previous_one(self):
		installation = make_installation(EXTENSION, checksum="first", source="// 1")
		first = installation.release_path
		self.release(installation, "second", "// 2")

		installation.enabled = 0
		installation.save()
		frappe.db.after_commit.run()

		self.assertTrue(first.is_dir())

	def test_a_failed_rewrite_keeps_the_written_release(self):
		installation = make_installation(EXTENSION, source="// 1")

		with patch.object(Path, "write_bytes", side_effect=OSError("Disk full")):
			write_source(installation, "// 1")

		self.assertEqual((installation.release_path / "main.js").read_text(), "// 1")

	def test_a_failed_write_leaves_no_partial_release(self):
		installation = make_installation(EXTENSION, checksum="partial")

		with (
			patch.object(Path, "write_bytes", side_effect=OSError("Disk full")),
			self.assertRaises(OSError),
		):
			write_source(installation, "// 1")

		self.assertEqual(list(installation.install_path.iterdir()), [])

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
