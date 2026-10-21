# Copyright (c) 2026, Frappe Technologies Pvt Ltd and Contributors
# See license.txt

import io
import json
import shutil
import zipfile
from pathlib import Path
from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

from builder.builder.doctype.builder_extension.builder_extension import get_enabled_extensions

MANIFEST = {"name": "acme-seo", "label": "SEO", "version": "1.0.0", "entry": "main.js", "style": "style.css"}


def make_package(manifest: dict | None = None, files: dict | None = None) -> str:
	buffer = io.BytesIO()
	with zipfile.ZipFile(buffer, "w") as archive:
		archive.writestr("manifest.json", json.dumps(manifest or MANIFEST))
		for path, content in (files or {"main.js": "export default {}", "style.css": ""}).items():
			archive.writestr(path, content)
	file = frappe.get_doc(
		{"doctype": "File", "file_name": "package.zip", "content": buffer.getvalue(), "is_private": 0}
	).insert()
	return file.file_url


def install(package: str, **fields):
	return frappe.get_doc({"doctype": "Builder Extension", "package": package, **fields}).insert()


def site_path(url: str) -> Path:
	return Path(frappe.get_site_path("public", url.lstrip("/")))


class TestBuilderExtension(FrappeTestCase):
	def tearDown(self):
		for name in frappe.get_all("Builder Extension", filters={"name": ["like", "acme-%"]}, pluck="name"):
			frappe.delete_doc("Builder Extension", name)
		frappe.db.after_commit.run()
		# a rolled back install leaves its unpacked files with no record to remove them
		for folder in Path(frappe.get_site_path("public", "files", "builder_extensions")).glob("acme-*"):
			shutil.rmtree(folder)

	def test_installs_a_package_from_its_manifest(self):
		extension = install(make_package())

		self.assertEqual((extension.name, extension.label, extension.version), ("acme-seo", "SEO", "1.0.0"))
		self.assertRegex(extension.entry_url, r"^/files/builder_extensions/acme-seo/[0-9a-f]{16}/main\.js$")
		self.assertTrue(site_path(extension.entry_url).exists())
		self.assertTrue(site_path(extension.style_url).exists())

	def test_a_new_package_replaces_the_old_release(self):
		extension = install(make_package())
		old_entry = extension.entry_url

		extension.package = make_package(
			{**MANIFEST, "version": "1.1.0"}, {"main.js": "export default { v: 2 }", "style.css": ""}
		)
		extension.save()
		frappe.db.after_commit.run()

		self.assertEqual(extension.version, "1.1.0")
		self.assertNotEqual(extension.entry_url, old_entry)
		self.assertTrue(site_path(extension.entry_url).exists())
		self.assertFalse(site_path(old_entry).exists())

	def test_refuses_a_package_of_another_extension(self):
		extension = install(make_package())
		extension.package = make_package({**MANIFEST, "name": "acme-other"})

		self.assertRaises(frappe.ValidationError, extension.save)

	def test_refuses_unsafe_packages(self):
		cases = [
			({**MANIFEST, "name": "Acme SEO"}, None),
			({**MANIFEST, "entry": "missing.js"}, None),
			(MANIFEST, {"main.js": "", "style.css": "", "../escape.js": ""}),
			(MANIFEST, {"main.js": "", "style.css": "", "server.py": ""}),
		]
		for manifest, files in cases:
			with self.subTest(manifest=manifest, files=files):
				self.assertRaises(frappe.ValidationError, install, make_package(manifest, files))

	def test_deleting_removes_the_files_after_the_commit(self):
		extension = install(make_package())
		entry = site_path(extension.entry_url)

		extension.delete()
		self.assertTrue(entry.exists())

		frappe.db.after_commit.run()
		self.assertFalse(entry.exists())

	def test_a_rolled_back_delete_keeps_the_files(self):
		extension = install(make_package())
		entry = site_path(extension.entry_url)

		extension.delete()
		frappe.db.rollback()

		self.assertTrue(entry.exists())

	def test_lists_only_enabled_extensions(self):
		install(make_package())
		install(make_package({**MANIFEST, "name": "acme-off"}), enabled=0)

		self.assertEqual([row.name for row in get_enabled_extensions()], ["acme-seo"])

	def test_a_dev_server_needs_developer_mode(self):
		fields = {
			"extension_name": "acme-dev",
			"source": "Dev Server",
			"dev_url": "http://localhost:5174/src/main.ts",
		}

		with patch.dict(frappe.conf, {"developer_mode": 0}):
			self.assertRaises(frappe.ValidationError, install, None, **fields)

		with patch.dict(frappe.conf, {"developer_mode": 1}):
			extension = install(None, **fields)
			self.assertEqual(extension.entry_url, "http://localhost:5174/src/main.ts")
			self.assertEqual([row.name for row in get_enabled_extensions()], ["acme-dev"])

		with patch.dict(frappe.conf, {"developer_mode": 0}):
			self.assertEqual(get_enabled_extensions(), [])
