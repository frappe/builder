# Copyright (c) 2026, Frappe Technologies Pvt Ltd and Contributors
# See license.txt

import json
import shutil
import tempfile
from pathlib import Path
from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

from builder.builder.tests.plugin_fixtures import (
	INSTALLATION_DOCTYPE,
	drop_installations,
	make_installation,
)
from builder.plugins.app_plugins import sync_app_plugins
from builder.plugins.constants import APP_PLUGINS_FINGERPRINT_KEY, ENTRY_FILE
from builder.plugins.hub import assert_installable
from builder.plugins.installations import get_installations, uninstall_plugin

PLUGIN = "acme/bundled"
APP = "builder"


class TestAppPlugin(FrappeTestCase):
	def setUp(self):
		drop_installations(PLUGIN)
		self.addCleanup(drop_installations, PLUGIN)
		frappe.cache.delete_value(APP_PLUGINS_FINGERPRINT_KEY)
		self.module = Path(tempfile.mkdtemp())
		self.addCleanup(shutil.rmtree, self.module, ignore_errors=True)
		self.build = self.module / "public" / "builder_plugins" / "plugin"
		self.build.mkdir(parents=True)
		(self.module / "plugin").mkdir()
		(self.module / "plugin" / "manifest.json").write_text(json.dumps(self.get_manifest("1.0.0")))
		self.write_build("1.0.0")
		self.set_plugin_folders(["plugin"])
		module = patch("builder.plugins.app_plugins.get_app_folder", return_value=self.module)
		module.start()
		self.addCleanup(module.stop)

	def set_plugin_folders(self, folders: list[str], app: str = APP):
		plugin_folders = patch(
			"builder.plugins.app_plugins.get_plugin_folders",
			side_effect=lambda installed_app: folders if installed_app == app else [],
		)
		plugin_folders.start()
		self.addCleanup(plugin_folders.stop)

	def get_manifest(self, version: str) -> dict:
		return {
			"v": 1,
			"name": PLUGIN,
			"label": "Bundled",
			"description": "Comes with an app",
			"version": version,
			"entry": ENTRY_FILE,
		}

	def write_build(self, version: str):
		(self.build / "manifest.json").write_text(json.dumps(self.get_manifest(version)))
		(self.build / ENTRY_FILE).write_text(f"// {version}")

	def installed(self):
		return frappe.get_doc(INSTALLATION_DOCTYPE, {"plugin": PLUGIN})

	def test_lists_an_app_plugin_disabled_from_its_build(self):
		(self.module / "plugin" / "DESCRIPTION.md").write_text("# For users")

		(listed,) = [row for row in get_installations() if row["name"] == PLUGIN]

		self.assertEqual([listed["source_app"], listed["enabled"], listed["version"]], [APP, False, "1.0.0"])
		entry = f"/assets/builder/builder_plugins/plugin/main.js?v={self.installed().checksum}"
		self.assertEqual(listed["entry_url"], entry)
		self.assertEqual(self.installed().readme, "# For users")

	def test_applies_a_new_build_and_keeps_enabled(self):
		sync_app_plugins()
		frappe.db.set_value(INSTALLATION_DOCTYPE, self.installed().name, "enabled", 1)

		self.write_build("1.1.0")
		sync_app_plugins()

		self.assertEqual([self.installed().version, self.installed().enabled], ["1.1.0", 1])

	def test_applies_a_new_entry_with_the_same_manifest(self):
		sync_app_plugins()
		checksum = self.installed().checksum

		(self.build / ENTRY_FILE).write_text("// a changed entry")
		sync_app_plugins()

		self.assertNotEqual(self.installed().checksum, checksum)

	def test_shows_a_plugin_without_a_build_as_failed(self):
		shutil.rmtree(self.build)

		sync_app_plugins()

		row = self.installed()
		self.assertEqual(row.install_state, "Failed")
		self.assertIn("bench build --app builder", row.install_error)

	def test_lists_without_a_plugin_whose_manifest_is_invalid(self):
		(self.module / "plugin" / "manifest.json").write_text("{")

		self.assertNotIn(PLUGIN, [row["name"] for row in get_installations()])

	def test_the_hub_cannot_take_a_failed_app_plugin(self):
		shutil.rmtree(self.build)
		sync_app_plugins()

		with self.assertRaisesRegex(frappe.ValidationError, "already installed from builder"):
			assert_installable(PLUGIN)

	def test_drops_an_orphan_row(self):
		sync_app_plugins()

		self.set_plugin_folders([])
		sync_app_plugins()

		self.assertFalse(frappe.db.exists(INSTALLATION_DOCTYPE, {"plugin": PLUGIN}))

	def test_another_app_gets_a_new_disabled_row_for_the_plugin(self):
		sync_app_plugins()
		frappe.db.set_value(INSTALLATION_DOCTYPE, self.installed().name, "enabled", 1)

		self.set_plugin_folders(["plugin"], app="frappe")
		sync_app_plugins()

		self.assertEqual([self.installed().source_app, self.installed().enabled], ["frappe", 0])

	def test_leaves_a_plugin_that_another_source_has(self):
		make_installation(PLUGIN, source="Hub", hub_url="https://hub.example.com")

		sync_app_plugins()

		self.assertEqual(self.installed().source, "Hub")

	def test_takes_over_a_development_row_disabled(self):
		make_installation(PLUGIN, source="Development", version="0.0.0-dev", enabled=1)

		sync_app_plugins()

		row = self.installed()
		self.assertEqual([row.source, row.version, row.enabled], ["App", "1.0.0", 0])

	def test_a_manager_cannot_uninstall_an_app_plugin(self):
		sync_app_plugins()

		with self.assertRaisesRegex(frappe.ValidationError, "comes with builder"):
			uninstall_plugin(PLUGIN)
