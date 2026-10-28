# Copyright (c) 2026, Frappe Technologies Pvt Ltd and Contributors
# See license.txt

import shutil
import subprocess
import unittest
from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

from builder.builder.tests.plugin_fixtures import drop_installations, make_installation, make_user
from builder.plugins import drafts
from builder.plugins.installations import get_installations

PLUGIN = "bob/word-count"
CODE = "export default { install() {} }"


def listed(name):
	return next((row for row in get_installations() if row["name"] == name), None)


def save(code=CODE, icon=None):
	return drafts.save_draft("word-count", "Word count", "Counts the words.", code, icon)


class TestPluginDrafts(FrappeTestCase):
	"""Bob writes drafts that only their owner runs, until the owner shares one."""

	def setUp(self):
		drop_installations(PLUGIN)
		self.addCleanup(drop_installations, PLUGIN)
		self.addCleanup(frappe.set_user, "Administrator")
		frappe.set_user("Administrator")
		self.teammate = make_user("plugin-teammate@example.com")

	def test_a_draft_runs_only_for_its_owner(self):
		installation = save(icon="whole-word")

		self.assertEqual([installation.source, installation.version], ["Bob", drafts.FIRST_VERSION])
		self.assertIsNone(installation.checksum)
		self.assertTrue(installation.icon_data_uri.startswith("data:image/svg+xml"))
		row = listed(PLUGIN)
		self.assertTrue(row["has_draft"])
		self.assertFalse(row["is_shared"])
		self.assertTrue(row["entry_url"].endswith(f"/{installation.draft_checksum}/main.js"))

		frappe.set_user(self.teammate)
		self.assertIsNone(listed(PLUGIN))

	def test_each_save_is_a_new_version_and_release(self):
		first = save()
		second = save(CODE + "\n// 2")

		self.assertEqual(second.version, "0.1.1")
		self.assertNotEqual(first.draft_checksum, second.draft_checksum)
		self.assertIn("// 2", drafts.read_code(second, "Administrator"))

	def test_sharing_gives_the_draft_to_everyone(self):
		draft_checksum = save().draft_checksum

		drafts.share_draft(PLUGIN)

		frappe.set_user(self.teammate)
		row = listed(PLUGIN)
		self.assertTrue(row["is_shared"])
		self.assertFalse(row["has_draft"])
		self.assertTrue(row["entry_url"].endswith(f"/{draft_checksum}/main.js"))

	def test_a_draft_of_a_shared_plugin_leaves_teammates_on_the_shared_release(self):
		shared = save().draft_checksum
		drafts.share_draft(PLUGIN)
		changed = save(CODE + "\n// changed")

		self.assertTrue(listed(PLUGIN)["entry_url"].endswith(f"/{changed.draft_checksum}/main.js"))
		frappe.set_user(self.teammate)
		self.assertTrue(listed(PLUGIN)["entry_url"].endswith(f"/{shared}/main.js"))
		self.assertNotIn("// changed", drafts.get_plugin_code(PLUGIN))

	def test_discarding_goes_back_to_the_shared_release(self):
		shared = save().draft_checksum
		drafts.share_draft(PLUGIN)
		save(CODE + "\n// changed")

		drafts.discard_draft(PLUGIN)
		frappe.db.after_commit.run()

		installation = frappe.get_doc("Builder Plugin", {"plugin": PLUGIN})
		self.assertEqual([installation.checksum, installation.draft_checksum], [shared, None])
		self.assertTrue(installation.release_path.is_dir(), "the shared release must outlive its pruning")

	def test_discarding_a_plugin_that_was_never_shared_removes_it(self):
		save()

		drafts.discard_draft(PLUGIN)

		self.assertIsNone(listed(PLUGIN))

	def test_only_the_owner_shares_or_discards_a_draft(self):
		save()

		frappe.set_user(self.teammate)
		for action in (drafts.share_draft, drafts.discard_draft):
			with self.subTest(action=action.__name__), self.assertRaises(frappe.PermissionError):
				action(PLUGIN)

	def test_a_page_editor_who_cannot_manage_plugins_cannot_save_one(self):
		frappe.set_user(make_user("plugin-editor@example.com", roles=("Blogger",)))

		with self.assertRaises(frappe.PermissionError):
			save()

	def test_bob_does_not_change_a_plugin_from_elsewhere(self):
		make_installation(PLUGIN, source="Hub")

		with self.assertRaises(frappe.ValidationError):
			save()

	def test_a_name_is_one_lowercase_slug(self):
		with self.assertRaises(frappe.ValidationError):
			drafts.save_draft("../escape", "Escape", "No.", CODE)

	@unittest.skipUnless(shutil.which("node"), "needs node")
	def test_a_syntax_error_names_its_line(self):
		self.assertIsNone(drafts.syntax_error(CODE))

		error = drafts.syntax_error("export default { install() { const x = ; } }")

		self.assertTrue(error.startswith("main.js:1"))
		self.assertIn("SyntaxError", error)
		self.assertNotIn(" at ", error)

	def test_a_load_report_reaches_only_its_own_user(self):
		drafts.report_load("token-1", {"registered": []})

		self.assertEqual(drafts.get_load_report("Administrator", "token-1"), {"registered": []})
		self.assertIsNone(drafts.get_load_report(self.teammate, "token-1"))
		with self.assertRaises(frappe.ValidationError):
			drafts.report_load("token-2", {"error": "x" * (drafts.MAX_REPORT_BYTES + 1)})

	def test_nothing_to_read_or_share(self):
		installation = make_installation(PLUGIN, source="Bob", checksum=None)

		self.assertIsNone(drafts.read_code(installation, "Administrator"))
		self.assertIsNone(drafts.get_plugin_code("bob/not-installed"))
		with self.assertRaises(frappe.ValidationError):
			installation.share_draft()

	def test_pruning_after_a_delete_leaves_nothing_to_do(self):
		installation = save()
		installation.delete()

		installation.delete_old_releases()

	def test_a_syntax_check_that_hangs_is_skipped(self):
		with patch.object(drafts.subprocess, "run", side_effect=subprocess.TimeoutExpired("node", 10)):
			self.assertIsNone(drafts.syntax_error(CODE))
