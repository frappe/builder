# Copyright (c) 2026, Frappe Technologies Pvt Ltd and Contributors
# See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase

from builder.builder.tests.plugin_fixtures import drop_installations, make_installation, write_entry

PLUGIN = "acme/released"


class TestBuilderPlugin(FrappeTestCase):
	def setUp(self):
		drop_installations(PLUGIN)
		self.addCleanup(drop_installations, PLUGIN)

	def release(self, installation, checksum: str, entry: str):
		installation.checksum = checksum
		write_entry(installation, entry)
		installation.save()
		frappe.db.after_commit.run()

	def test_each_release_has_its_own_folder_and_url(self):
		installation = make_installation(PLUGIN, checksum="00000000000a", entry="// 1")
		first = installation.release_path

		self.release(installation, "00000000000b", "// 2")

		self.assertEqual((installation.release_path / "main.js").read_text(), "// 2")
		self.assertTrue(installation.entry_url.endswith("/00000000000b/main.js"))
		self.assertTrue(first.is_dir(), "an open tab still runs the previous release")

		self.release(installation, "00000000000c", "// 3")
		self.assertFalse(first.is_dir())

	def test_a_checksum_must_not_leave_the_install_folder(self):
		installation = make_installation(PLUGIN)
		for checksum in ("../..", "0123456789ab\n"):
			installation.checksum = checksum
			with self.subTest(checksum=checksum), self.assertRaises(frappe.ValidationError):
				installation.save()

	def test_a_delete_removes_the_files_after_the_commit(self):
		installation = make_installation(PLUGIN, entry="// 1")

		installation.delete()
		frappe.db.after_commit.run()

		self.assertFalse(installation.install_path.exists())
