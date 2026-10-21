# Copyright (c) 2026, Frappe Technologies Pvt Ltd and contributors
# For license information, please see license.txt

import hashlib
import io
import json
import re
import zipfile
from pathlib import Path, PurePosixPath

import frappe
from frappe import _

NAME_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
MAX_PACKAGE_BYTES = 20 * 1024 * 1024
MAX_UNPACKED_BYTES = 50 * 1024 * 1024
MAX_FILES = 500
# the editor imports the entry as a module, and the files it loads are static assets
ALLOWED_SUFFIXES = {
	".js",
	".mjs",
	".css",
	".json",
	".map",
	".svg",
	".png",
	".jpg",
	".jpeg",
	".webp",
	".gif",
	".woff",
	".woff2",
	".ttf",
	".txt",
}


class ExtensionPackage:
	"""A built extension: `manifest.json`, the entry module it names, and the files that module loads.

	The code is trusted, so the checks here protect the server's disk, not the editor.
	"""

	def __init__(self, content: bytes):
		if len(content) > MAX_PACKAGE_BYTES:
			frappe.throw(_("The package is larger than {0} MB.").format(MAX_PACKAGE_BYTES // 1024 // 1024))
		try:
			self.archive = zipfile.ZipFile(io.BytesIO(content))
		except zipfile.BadZipFile:
			frappe.throw(_("The package must be a zip file."))
		self.checksum = hashlib.sha256(content).hexdigest()[:16]
		self.files = self.get_files()
		self.manifest = self.get_manifest()

	@property
	def name(self) -> str:
		return self.manifest["name"]

	def get_files(self) -> dict[str, zipfile.ZipInfo]:
		files = {info.filename: info for info in self.archive.infolist() if not info.is_dir()}
		if len(files) > MAX_FILES:
			frappe.throw(_("The package has more than {0} files.").format(MAX_FILES))
		if sum(info.file_size for info in files.values()) > MAX_UNPACKED_BYTES:
			frappe.throw(
				_("The unpacked package is larger than {0} MB.").format(MAX_UNPACKED_BYTES // 1024 // 1024)
			)
		for path in files:
			assert_safe_path(path)
		return files

	def get_manifest(self) -> dict:
		if "manifest.json" not in self.files:
			frappe.throw(_("The package has no manifest.json at its root."))
		try:
			manifest = json.loads(self.archive.read("manifest.json"))
		except ValueError:
			frappe.throw(_("manifest.json is not valid JSON."))
		if not isinstance(manifest, dict):
			frappe.throw(_("manifest.json must be a JSON object."))
		self.validate_manifest(manifest)
		return manifest

	def validate_manifest(self, manifest: dict) -> None:
		if not NAME_PATTERN.match(str(manifest.get("name", ""))):
			frappe.throw(_("The manifest name must use lowercase letters, numbers and hyphens."))
		for field in ("label", "version", "entry"):
			if not isinstance(manifest.get(field), str) or not manifest[field]:
				frappe.throw(_("The manifest needs a {0}.").format(field))
		for field in ("entry", "style"):
			if manifest.get(field) and manifest[field] not in self.files:
				frappe.throw(
					_("The manifest names {0}, which is not in the package.").format(manifest[field])
				)

	def unpack(self, folder: Path) -> None:
		for path, info in self.files.items():
			target = folder / path
			target.parent.mkdir(parents=True, exist_ok=True)
			target.write_bytes(self.archive.read(info))


def assert_safe_path(path: str) -> None:
	parts = PurePosixPath(path).parts
	if "\\" in path or path.startswith("/") or ".." in parts or not parts:
		frappe.throw(_("The package has a file outside its root: {0}").format(path))
	if PurePosixPath(path).suffix.lower() not in ALLOWED_SUFFIXES:
		frappe.throw(_("The package has a file of a type that an extension cannot serve: {0}").format(path))
