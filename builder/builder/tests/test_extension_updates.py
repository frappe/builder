# Copyright (c) 2026, Frappe Technologies Pvt Ltd and Contributors
# See license.txt

from pathlib import Path
from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

from builder.builder.tests.extension_fixtures import drop_installations, make_installation, write_source
from builder.extensions.constants import ENTRY_FILE
from builder.extensions.hub import Release
from builder.extensions.package import ValidatedPackage
from builder.extensions.updates import get_update, run_hub_update, update_from_hub

EXTENSION = "acme/updating"
HUB = "https://hub.example.com"


def release(version: str, permissions: list[str]) -> Release:
	return Release(
		name=EXTENSION,
		version=version,
		protocol_version=1,
		manifest={"permissions": permissions},
		package_url=f"{HUB}/{version}.builderext",
		package_size=10,
		package_sha256="abc123def456",
		status="Published",
	)


def package(version: str, permissions: list[str]) -> ValidatedPackage:
	manifest = {"label": "Updating", "description": "An update test", "permissions": permissions}
	return ValidatedPackage(manifest=manifest, files={"main.js": f"// {version}".encode()})


class TestExtensionUpdates(FrappeTestCase):
	def setUp(self):
		drop_installations(EXTENSION)
		self.row = make_installation(
			EXTENSION,
			permissions=["data.access"],
			source_url=HUB,
			install_state="Ready",
			enabled=0,
		)

	def tearDown(self):
		drop_installations(EXTENSION)

	def run_update(self, version: str, permissions: list[str], granted: list[str]):
		with (
			patch("builder.extensions.updates.get_release", return_value=release(version, permissions)),
			patch("builder.extensions.updates.download_package", return_value=b"bytes"),
			patch("builder.extensions.updates.validate_package", return_value=package(version, permissions)),
			patch("builder.extensions.updates.frappe.publish_realtime") as publish,
		):
			run_hub_update(self.row.name, EXTENSION, version, HUB, "Administrator", granted)
		event, message = publish.call_args.args
		# its own event: an install listener reads any message as a finished install
		self.assertEqual(event, "builder_extension_update")
		return message

	def test_finds_a_newer_release_and_the_permissions_it_adds(self):
		with (
			patch(
				"builder.extensions.updates.hub_extension", return_value={"releases": [{"version": "1.1.0"}]}
			),
			patch(
				"builder.extensions.updates.get_release",
				return_value=release("1.1.0", ["data.access", "page.edit"]),
			),
		):
			update = get_update(EXTENSION)
		self.assertEqual(update["version"], "1.1.0")
		self.assertEqual(update["new_permissions"], ["page.edit"])

	def test_applies_the_release_and_keeps_the_extension_disabled(self):
		message = self.run_update("1.1.0", ["data.access", "page.edit"], granted=["data.access"])

		row = frappe.get_doc("Builder Extension", self.row.name)
		self.assertEqual(row.version, "1.1.0")
		self.assertEqual(row.enabled, 0)
		self.assertEqual(row.requested, ["data.access", "page.edit"])
		self.assertEqual(row.permissions, ["data.access"])
		self.assertIsNone(message["error"])

	def test_keeps_a_grant_revoked_while_the_job_waited(self):
		self.row.db_set("granted_permissions", "[]")
		self.run_update("1.1.0", ["data.access", "page.edit"], granted=["data.access", "page.edit"])
		# page.edit is new in this release, so its approval stands
		self.assertEqual(frappe.get_doc("Builder Extension", self.row.name).permissions, ["page.edit"])

	def test_a_failed_file_write_keeps_the_installed_files(self):
		write_source(self.row, "// 1.0.0")
		with (
			patch.object(Path, "write_bytes", side_effect=OSError("Disk full")),
			patch.object(frappe.db, "rollback"),
		):
			message = self.run_update("1.1.0", ["data.access"], granted=["data.access"])
		self.assertEqual(Path(self.row.install_path, ENTRY_FILE).read_text(), "// 1.0.0")
		self.assertIn("Disk full", message["error"])

	def test_a_failed_update_keeps_the_installed_release(self):
		with (
			patch(
				"builder.extensions.updates.get_release", side_effect=frappe.ValidationError("Hub is down")
			),
			patch("builder.extensions.updates.frappe.publish_realtime") as publish,
			# the job's rollback would also undo this test's setUp, which the job never wrote
			patch.object(frappe.db, "rollback"),
		):
			run_hub_update(self.row.name, EXTENSION, "1.1.0", HUB, "Administrator", ["data.access"])

		row = frappe.get_doc("Builder Extension", self.row.name)
		self.assertEqual([row.version, row.install_state], ["1.0.0", "Ready"])
		self.assertEqual(publish.call_args.args[1]["error"], "Hub is down")

	def test_a_directory_install_cannot_update(self):
		self.row.db_set("source_url", "")
		with self.assertRaises(frappe.ValidationError):
			update_from_hub(EXTENSION, "1.1.0", ["data.access"])
