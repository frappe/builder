# Copyright (c) 2026, Frappe Technologies Pvt Ltd and Contributors
# See license.txt

from pathlib import Path
from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

from builder.builder.tests.plugin_fixtures import drop_installations, make_installation
from builder.plugins.constants import ENTRY_FILE, PROTOCOL_VERSION
from builder.plugins.hub import Release
from builder.plugins.package import ValidatedPackage
from builder.plugins.updates import get_update, run_hub_update

PLUGIN = "acme/updating"
HUB = "https://hub.example.com"


def release(version: str) -> Release:
	return Release(
		name=PLUGIN,
		version=version,
		protocol_version=PROTOCOL_VERSION,
		manifest={},
		package_url=f"{HUB}/{version}.builderplugin",
		package_size=10,
		package_sha256=f"{version.replace('.', '')}abcdef0123456",
		status="Published",
	)


def package(version: str) -> ValidatedPackage:
	manifest = {"label": "Updating", "description": "An update test", "version": version}
	return ValidatedPackage(manifest=manifest, files={"main.js": f"// {version}".encode()})


class TestPluginUpdates(FrappeTestCase):
	def setUp(self):
		drop_installations(PLUGIN)
		self.row = make_installation(PLUGIN, hub_url=HUB, install_state="Ready", enabled=0)

	def tearDown(self):
		drop_installations(PLUGIN)

	def run_update(self, version: str):
		with (
			patch("builder.plugins.updates.get_release", return_value=release(version)),
			patch("builder.plugins.updates.download_package", return_value=b"bytes"),
			patch("builder.plugins.updates.validate_package", return_value=package(version)),
			patch("builder.plugins.updates.frappe.publish_realtime") as publish,
		):
			run_hub_update(self.row.name, PLUGIN, version, HUB, "Administrator")
		event, message = publish.call_args.args
		# its own event: an install listener reads any message as a finished install
		self.assertEqual(event, "builder_plugin_update")
		return message

	def test_finds_a_newer_release(self):
		with patch("builder.plugins.updates.hub_plugin", return_value={"releases": [{"version": "1.1.0"}]}):
			self.assertEqual(get_update(PLUGIN), {"version": "1.1.0"})

	def test_refuses_an_plugin_that_did_not_come_from_a_hub(self):
		make_installation(PLUGIN, source="Development")

		with self.assertRaises(frappe.ValidationError):
			get_update(PLUGIN)

	def test_applies_the_release_to_a_new_folder_and_keeps_the_plugin_disabled(self):
		message = self.run_update("1.1.0")

		row = frappe.get_doc("Builder Plugin", self.row.name)
		self.assertEqual([row.version, row.enabled], ["1.1.0", 0])
		self.assertEqual(Path(row.release_path, ENTRY_FILE).read_text(), "// 1.1.0")
		self.assertNotEqual(row.entry_url, self.row.entry_url)
		self.assertIsNone(message["error"])

	def test_a_failed_update_keeps_the_installed_release(self):
		with (
			patch("builder.plugins.updates.get_release", side_effect=frappe.ValidationError("Hub is down")),
			patch("builder.plugins.updates.frappe.publish_realtime") as publish,
			# the job's rollback would also undo this test's setUp, which the job never wrote
			patch.object(frappe.db, "rollback"),
		):
			run_hub_update(self.row.name, PLUGIN, "1.1.0", HUB, "Administrator")

		row = frappe.get_doc("Builder Plugin", self.row.name)
		self.assertEqual([row.version, row.install_state], ["1.0.0", "Ready"])
		self.assertEqual(publish.call_args.args[1]["error"], "Hub is down")
