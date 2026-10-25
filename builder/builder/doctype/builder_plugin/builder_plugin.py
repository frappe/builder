# Copyright (c) 2026, Frappe Technologies Pvt Ltd and contributors
# For license information, please see license.txt

import base64
import shutil
import uuid
from pathlib import Path

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import get_files_path, now

from builder.plugins.constants import (
	CHECKSUM_PATTERN,
	ENTRY_FILE,
	ICON_PATTERN,
	MAX_README_BYTES,
	PLUGIN_NAME_PATTERN,
	PLUGINS_FOLDER,
	VERSION_PATTERN,
)

STATE_DOCTYPE = "Builder Plugin State"
KEPT_PREVIOUS_RELEASES = 1


class BuilderPlugin(Document):
	"""One plugin that the editor loads into its own Vue app. Its code runs with the access of each editor user."""

	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		checksum: DF.Data | None
		description: DF.SmallText | None
		enabled: DF.Check
		plugin: DF.Data
		hub_url: DF.Data | None
		icon: DF.Data | None
		install_error: DF.SmallText | None
		install_state: DF.Literal["Installing", "Ready", "Failed"]
		installed_on: DF.Datetime | None
		label: DF.Data | None
		readme: DF.LongText | None
		source: DF.Literal["Hub", "App", "Development"]
		version: DF.Data
	# end: auto-generated types

	def autoname(self):
		# a uuid, and the plugin is looked up by field. The name is also the
		# install directory, so it must hold no separator
		if not self.name:
			self.name = str(uuid.uuid4())

	def before_insert(self):
		self.installed_on = now()

	def validate(self):
		self.validate_identity()
		self.validate_checksum()
		self.validate_icon()
		self.validate_readme()

	def on_update(self):
		# after the commit, so a rolled back update still finds the release it runs
		frappe.db.after_commit.add(self.delete_old_releases)

	def on_trash(self):
		self.delete_plugin_state()
		# the rows roll back with a failed delete, and files would not
		frappe.db.after_commit.add(self.delete_plugin_files)

	@property
	def install_path(self) -> Path:
		"""Every release of this installation, one folder per checksum."""
		return Path(get_files_path(PLUGINS_FOLDER, self.name))

	@property
	def release_path(self) -> Path | None:
		return self.install_path / self.checksum if self.checksum else None

	@property
	def entry_url(self) -> str | None:
		"""Where the editor imports the entry. The checksum names the build, so a new release gets a new URL."""
		if not self.checksum:
			return None
		return f"/files/{PLUGINS_FOLDER}/{self.name}/{self.checksum}/{ENTRY_FILE}"

	@property
	def icon_data_uri(self) -> str | None:
		"""None when the package ships no icon. The editor draws its own glyph then.

		A data URI, so the panel draws it with no request of its own.
		"""
		if not self.icon or not self.release_path:
			return None
		icon = self.release_path / self.icon
		if not icon.is_file():
			return None
		return f"data:image/svg+xml;base64,{base64.b64encode(icon.read_bytes()).decode()}"

	def validate_identity(self):
		if not PLUGIN_NAME_PATTERN.fullmatch(self.plugin or ""):
			frappe.throw(_("Plugin must read as publisher/name, in lowercase."))
		if not VERSION_PATTERN.fullmatch(self.version or ""):
			frappe.throw(_("Version must hold only letters, digits, dots, plus signs and hyphens."))

	def validate_checksum(self):
		if self.checksum and not CHECKSUM_PATTERN.fullmatch(self.checksum):
			frappe.throw(_("Checksum must be 12 lowercase hex digits."))

	def validate_icon(self):
		if self.icon and not ICON_PATTERN.fullmatch(self.icon):
			frappe.throw(_("Icon must name one SVG file in the install root, such as icon.svg."))

	def validate_readme(self):
		if self.readme and len(self.readme.encode()) > MAX_README_BYTES:
			frappe.throw(_("A README may hold {0} bytes at most.").format(MAX_README_BYTES))

	def write_plugin_files(self, files: dict[str, bytes]):
		"""Write one release to its own folder, keyed by path under the release root.

		The files go to a staging folder that moves into place in one rename. So a
		release folder is always whole, and the checksum names its package, so an
		existing one is reused.
		"""
		release = self.release_path
		if release.is_dir():
			return
		staging = self.install_path / f".staging-{uuid.uuid4().hex}"
		try:
			for relative_path, content in files.items():
				target = staging / relative_path
				target.parent.mkdir(parents=True, exist_ok=True)
				target.write_bytes(content)
			staging.rename(release)
		finally:
			shutil.rmtree(staging, ignore_errors=True)

	@property
	def previous_releases(self) -> list[Path]:
		"""Newest first. A staging folder is not a release yet."""
		if not self.install_path.is_dir():
			return []
		releases = [
			release
			for release in self.install_path.iterdir()
			if release.name != self.checksum and not release.name.startswith(".")
		]
		return sorted(releases, key=lambda release: release.stat().st_mtime, reverse=True)

	def delete_old_releases(self):
		# an open editor tab may still run the previous release and load its chunks lazily
		for release in self.previous_releases[KEPT_PREVIOUS_RELEASES:]:
			shutil.rmtree(release, ignore_errors=True)

	def delete_plugin_files(self):
		shutil.rmtree(self.install_path, ignore_errors=True)

	def delete_plugin_state(self):
		"""A state row Links to this record, so Frappe refuses the delete while one stands.

		One query for every user's row. A state row has no hooks, files or versions to clear.
		"""
		frappe.db.delete(STATE_DOCTYPE, {"installation": self.name})
