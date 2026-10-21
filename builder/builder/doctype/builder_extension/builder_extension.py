# Copyright (c) 2026, Frappe Technologies Pvt Ltd and contributors
# For license information, please see license.txt

import shutil
from pathlib import Path

import frappe
from frappe import _
from frappe.model.document import Document

from builder.api import check_app_permission
from builder.builder.doctype.builder_extension.extension_package import NAME_PATTERN, ExtensionPackage

# under the site's public files, which nginx and the dev server already serve at /files
EXTENSIONS_FOLDER = "builder_extensions"


class BuilderExtension(Document):
	"""An extension that the editor loads into its own Vue app. Its code runs with the access of each editor user."""

	def before_insert(self):
		if self.source == "Package":
			self.extension_name = self.extension_name or self.get_package_contents().name

	def validate(self):
		if not NAME_PATTERN.match(self.extension_name or ""):
			frappe.throw(_("The extension name must use lowercase letters, numbers and hyphens."))
		if self.source == "Dev Server":
			self.use_dev_server()
		elif self.is_new() or self.has_value_changed("package"):
			self.install_package()

	# files go only after the commit, so a rolled back save or delete never points at missing files
	def on_update(self):
		if self.source == "Package":
			frappe.db.after_commit.add(self.remove_other_releases)

	def on_trash(self):
		folder = self.folder
		frappe.db.after_commit.add(lambda: shutil.rmtree(folder, ignore_errors=True))

	@property
	def folder(self) -> Path:
		return Path(frappe.get_site_path("public", "files", EXTENSIONS_FOLDER, self.extension_name))

	@property
	def base_url(self) -> str:
		return f"/files/{EXTENSIONS_FOLDER}/{self.extension_name}"

	def get_package_contents(self) -> ExtensionPackage:
		return ExtensionPackage(frappe.get_doc("File", {"file_url": self.package}).get_content())

	def use_dev_server(self):
		if not frappe.conf.developer_mode:
			frappe.throw(_("A dev server extension needs developer mode."))
		self.label = self.label or self.extension_name
		self.version = "dev"
		self.entry_url = self.dev_url
		self.style_url = None

	def install_package(self):
		package = self.get_package_contents()
		if package.name != self.extension_name:
			frappe.throw(_("This package is {0}, not {1}.").format(package.name, self.extension_name))

		# a new build gets a new folder, so a browser never serves a cached old file under a new release
		package.unpack(self.folder / package.checksum)

		release_url = f"{self.base_url}/{package.checksum}"
		self.label = package.manifest["label"]
		self.version = package.manifest["version"]
		self.entry_url = f"{release_url}/{package.manifest['entry']}"
		self.style_url = (
			f"{release_url}/{package.manifest['style']}" if package.manifest.get("style") else None
		)

	def remove_other_releases(self):
		installed = Path(self.entry_url).relative_to(self.base_url).parts[0]
		for release in self.folder.iterdir():
			if release.name != installed:
				shutil.rmtree(release, ignore_errors=True)


@frappe.whitelist()
def get_enabled_extensions() -> list[dict]:
	if not check_app_permission():
		return []
	extensions = frappe.get_all(
		"Builder Extension",
		filters={"enabled": 1, "entry_url": ["is", "set"]},
		fields=["name", "label", "source", "entry_url", "style_url"],
		order_by="creation asc",
	)
	return [row for row in extensions if row.source != "Dev Server" or frappe.conf.developer_mode]
