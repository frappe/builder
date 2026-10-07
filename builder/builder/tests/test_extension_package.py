# Copyright (c) 2026, Frappe Technologies Pvt Ltd and Contributors
# See license.txt

import io
import json
import zipfile

import frappe
from frappe.tests.utils import FrappeTestCase

from builder.extensions.package import validate_package

NAME = "acme/chunked"
VERSION = "1.0.0"
ICON = b'<svg xmlns="http://www.w3.org/2000/svg"><path d="M0 0h1v1z"/></svg>'


def manifest(**values) -> bytes:
	fields = {
		"v": 1,
		"name": NAME,
		"label": "Chunked",
		"description": "Splits its build.",
		"version": VERSION,
		"entry": "main.js",
		"permissions": [],
		**values,
	}
	return json.dumps(fields).encode()


def make_package(files: dict[str, bytes], folders: tuple[str, ...] = ()) -> bytes:
	buffer = io.BytesIO()
	with zipfile.ZipFile(buffer, "w") as archive:
		for folder in folders:
			archive.writestr(f"{folder}/", b"")
		for name, data in files.items():
			archive.writestr(name, data)
	return buffer.getvalue()


def build(**extra: bytes) -> dict[str, bytes]:
	files = {"manifest.json": manifest(), "main.js": b'import "./chunks/panel.js";'}
	files["chunks/panel.js"] = b'const css = new URL("../assets/style.css", import.meta.url);'
	files["assets/style.css"] = b".a{}"
	return {**files, **extra}


class TestExtensionPackage(FrappeTestCase):
	def test_accepts_chunks_and_assets(self):
		package = validate_package(make_package(build(), folders=("chunks", "assets")), NAME, VERSION)

		self.assertEqual(
			sorted(package.files), ["assets/style.css", "chunks/panel.js", "main.js", "manifest.json"]
		)

	def test_accepts_an_icon_at_the_root(self):
		files = build(**{"manifest.json": manifest(icon="icon.svg"), "icon.svg": ICON})

		self.assertIn("icon.svg", validate_package(make_package(files), NAME, VERSION).files)

	def test_refuses_a_file_outside_the_build_folders(self):
		with self.assertRaises(frappe.ValidationError):
			validate_package(make_package(build(**{"extra/notes.js": b""})), NAME, VERSION)

	def test_refuses_a_type_the_route_does_not_serve(self):
		with self.assertRaises(frappe.ValidationError):
			validate_package(make_package(build(**{"assets/page.html": b"<script></script>"})), NAME, VERSION)

	def test_refuses_an_import_of_a_missing_file(self):
		files = build(**{"main.js": b'import "./chunks/gone.js";'})

		with self.assertRaises(frappe.ValidationError):
			validate_package(make_package(files), NAME, VERSION)

	def test_checks_every_svg_not_only_the_icon(self):
		unsafe = b'<svg xmlns="http://www.w3.org/2000/svg"><script>alert(1)</script></svg>'

		with self.assertRaises(frappe.ValidationError):
			validate_package(make_package(build(**{"assets/logo.svg": unsafe})), NAME, VERSION)

	def test_refuses_a_path_that_climbs_out(self):
		with self.assertRaises(frappe.ValidationError):
			validate_package(make_package(build(**{"chunks/../../evil.js": b""})), NAME, VERSION)
