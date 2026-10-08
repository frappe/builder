# Copyright (c) 2026, Frappe Technologies Pvt Ltd and contributors
# See license.txt

from pathlib import Path
from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

from builder.builder.tests.extension_fixtures import (
	INSTALLATION_DOCTYPE,
	drop_installations,
	make_installation,
	make_user,
	remove_orphan_installs,
)

EXTENSION = "acme/record"
INSTALLATION_MODULE = "builder.builder.doctype.builder_extension.builder_extension"


class TestBuilderExtension(FrappeTestCase):
	"""Tests the installation record of an extension."""

	def setUp(self):
		drop_installations(EXTENSION)

	def test_the_files_are_private_and_named_by_the_record(self):
		installation = make_installation(EXTENSION)

		self.assertIn("/private/files/extensions/", installation.install_path)
		self.assertTrue(installation.install_path.endswith(installation.name))

	def test_one_installation_per_extension(self):
		make_installation(EXTENSION)

		second = frappe.get_doc(
			{
				"doctype": INSTALLATION_DOCTYPE,
				"extension": EXTENSION,
				"version": "2.0.0",
			}
		)
		self.assertRaises(Exception, second.insert)

	def test_a_second_install_of_one_name_is_refused_whatever_the_source(self):
		"""`publisher/name` identifies the extension. A second source does not make a second install."""
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
		"""A manager can grant only the permissions that the extension asks for."""
		with self.assertRaises(frappe.ValidationError):
			make_installation(EXTENSION, permissions=["page.edit"], granted=["page.edit", "schema.write"])

	def test_writes_the_files_it_installs(self):
		installation = make_installation(EXTENSION)
		installation.write_extension_files({"main.js": b"export const ok = true;", "chunks/a.js": b""})

		root = Path(installation.install_path)
		self.assertEqual((root / "main.js").read_text(), "export const ok = true;")
		self.assertTrue((root / "chunks" / "a.js").is_file())

	def test_finds_the_entry_it_installed(self):
		installation = make_installation(EXTENSION, source="export const ok = true;")

		self.assertEqual(installation.get_asset_path("main.js").read_text(), "export const ok = true;")

	def test_uninstall_takes_the_files(self):
		installation = make_installation(EXTENSION, source="export default {};")
		install_path = Path(installation.install_path)
		self.assertTrue(install_path.is_dir())

		installation.delete()
		self.assertTrue(install_path.is_dir(), "files must wait for the commit")

		frappe.db.after_commit.run()
		self.assertFalse(install_path.exists())

	def test_uninstall_takes_every_users_state(self):
		installation = make_installation(EXTENSION)
		for user in ("Administrator", make_user()):
			frappe.get_doc(
				{
					"doctype": "Builder Extension State",
					"installation": installation.name,
					"user": user,
					"state": '{"theme": "dark"}',
				}
			).insert()

		installation.delete()

		self.assertFalse(frappe.db.exists("Builder Extension State", {"installation": installation.name}))


class TestInstalledFiles(FrappeTestCase):
	def setUp(self):
		drop_installations(EXTENSION)

	def test_finds_a_chunk_in_a_folder(self):
		installation = make_installation(EXTENSION)
		installation.write_extension_files({"main.js": b"", "chunks/panel.js": b"export {};"})

		self.assertEqual(installation.get_asset_path("chunks/panel.js").read_bytes(), b"export {};")

	def test_finds_no_file_that_was_never_installed(self):
		self.assertIsNone(make_installation(EXTENSION).get_asset_path("main.js"))

	def test_finds_no_file_outside_the_install(self):
		installation = make_installation(EXTENSION, source="export default {};")
		sibling = make_installation("acme/sibling", source="export const secret = 1;")
		self.addCleanup(drop_installations, "acme/sibling")

		self.assertIsNone(installation.get_asset_path(f"../{sibling.name}/main.js"))

	def test_finds_no_file_of_a_type_a_frame_does_not_load(self):
		installation = make_installation(EXTENSION)
		installation.write_extension_files({"main.js": b"", "page.html": b"<script></script>"})

		self.assertIsNone(installation.get_asset_path("page.html"))

	def test_draws_the_icon_as_a_data_uri(self):
		installation = make_installation(EXTENSION, source="export default {};", icon="icon.svg")

		self.assertTrue(installation.icon_data_uri.startswith("data:image/svg+xml;base64,"))

	def test_has_no_icon_when_the_package_ships_none(self):
		self.assertIsNone(make_installation(EXTENSION).icon_data_uri)

	def test_has_no_icon_when_the_named_file_is_missing(self):
		installation = make_installation(EXTENSION, source="export default {};", icon="icon.svg")
		(Path(installation.install_path) / "icon.svg").unlink()

		self.assertIsNone(installation.icon_data_uri)

	def test_removes_install_directories_no_record_names(self):
		orphan = Path(make_installation(EXTENSION, source="x").install_path).parent / "orphan"
		orphan.mkdir()

		remove_orphan_installs()

		self.assertFalse(orphan.exists())


class TestInstallationValidation(FrappeTestCase):
	def setUp(self):
		drop_installations(EXTENSION)

	def test_refuses_an_icon_that_is_not_one_svg_in_the_root(self):
		for icon in ("../icon.svg", "icon.png", "dir/icon.svg"):
			with self.assertRaises(frappe.ValidationError, msg=icon):
				make_installation(EXTENSION, icon=icon)

	def test_refuses_a_permission_list_that_is_not_a_json_list(self):
		for text in ("not json", '{"page.edit": 1}'):
			with self.assertRaises(frappe.ValidationError, msg=text):
				make_installation(EXTENSION, requested_permissions=text)

	def test_refuses_a_readme_over_the_size_limit(self):
		with patch(f"{INSTALLATION_MODULE}.MAX_README_BYTES", 3):
			with self.assertRaises(frappe.ValidationError):
				make_installation(EXTENSION, readme="four")
