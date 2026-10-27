# Copyright (c) 2026, Frappe Technologies Pvt Ltd and Contributors
# See license.txt

import io
import json
import zipfile

import frappe
from frappe.tests.utils import FrappeTestCase

from builder.plugins.package import validate_package

NAME = "acme/chunked"
VERSION = "1.0.0"


def manifest(**values) -> bytes:
	fields = {
		"v": 1,
		"name": NAME,
		"label": "Chunked",
		"description": "Splits its build.",
		"version": VERSION,
		"entry": "main.js",
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


class TestPluginPackage(FrappeTestCase):
	def test_accepts_chunks_and_assets(self):
		package = validate_package(make_package(build(), folders=("chunks", "assets")), NAME, VERSION)

		self.assertEqual(
			sorted(package.files), ["assets/style.css", "chunks/panel.js", "main.js", "manifest.json"]
		)

	def test_refuses_a_sandboxed_package(self):
		"""Only a sandboxed package asks for permissions. It imports an SDK this Builder does not serve."""
		with self.assertRaisesRegex(frappe.ValidationError, "sandboxed"):
			validate_package(
				make_package(build(**{"manifest.json": manifest(permissions=[])})), NAME, VERSION
			)

	def test_refuses_a_path_that_climbs_out(self):
		with self.assertRaises(frappe.ValidationError):
			validate_package(make_package(build(**{"chunks/../../evil.js": b""})), NAME, VERSION)
