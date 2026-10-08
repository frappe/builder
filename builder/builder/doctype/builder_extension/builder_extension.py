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

from builder.extensions.constants import (
	ASSET_ROUTE,
	ASSET_TYPES,
	ENTRY_FILE,
	EXTENSION_NAME_PATTERN,
	EXTENSIONS_FOLDER,
	ICON_PATTERN,
	MAX_README_BYTES,
	PERMISSIONS,
	VERSION_PATTERN,
)

STATE_DOCTYPE = "Builder Extension State"


class BuilderExtension(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		checksum: DF.Data | None
		description: DF.SmallText | None
		enabled: DF.Check
		extension: DF.Data
		granted_permissions: DF.SmallText | None
		icon: DF.Data | None
		install_error: DF.SmallText | None
		install_state: DF.Literal["Installing", "Ready", "Failed"]
		installed_on: DF.Datetime | None
		label: DF.Data | None
		readme: DF.LongText | None
		requested_permissions: DF.SmallText | None
		source_url: DF.Data | None
		version: DF.Data
	# end: auto-generated types

	def autoname(self):
		# The name is also the install folder. A UUID has no slash.
		if not self.name:
			self.name = str(uuid.uuid4())

	def before_insert(self):
		self.installed_on = now()

	def validate(self):
		self.validate_identity()
		self.validate_icon()
		self.validate_permissions()
		self.validate_readme()

	def on_trash(self):
		self.delete_extension_state()
		# A failed delete rolls back the rows, but not the files.
		frappe.db.after_commit.add(self.delete_extension_files)

	@property
	def install_path(self) -> str:
		"""Returns the install folder. It is private, so only Builder reads it."""
		return get_files_path(f"{EXTENSIONS_FOLDER}/{self.name}", is_private=True)

	@property
	def permissions(self) -> list[str]:
		"""Returns the granted permissions. All checks use this list."""
		return self.permission_list("granted_permissions")

	@property
	def requested(self) -> list[str]:
		"""Returns the permissions that the manifest asks for."""
		return self.permission_list("requested_permissions")

	@property
	def entry_url(self) -> str | None:
		"""Returns the URL of the entry. A new build gets a new checksum and a new URL."""
		if not self.checksum:
			return None
		return f"/{ASSET_ROUTE}/{self.name}/{self.checksum}/{ENTRY_FILE}"

	def get_asset_path(self, relative_path: str) -> Path | None:
		"""Returns an installed file that a frame can load. Returns None for a path outside the install."""
		root = Path(self.install_path).resolve()
		file = (root / relative_path).resolve()
		if file.is_relative_to(root) and file.suffix in ASSET_TYPES and file.is_file():
			return file
		return None

	@property
	def icon_data_uri(self) -> str | None:
		"""Returns the icon as a data URI, or None if there is no icon."""
		if not self.icon:
			return None
		icon = Path(self.install_path) / self.icon
		if not icon.is_file():
			return None
		return f"data:image/svg+xml;base64,{base64.b64encode(icon.read_bytes()).decode()}"

	def validate_identity(self):
		if not EXTENSION_NAME_PATTERN.match(self.extension or ""):
			frappe.throw(_("Extension must read as publisher/name, in lowercase."))
		if not VERSION_PATTERN.match(self.version or ""):
			frappe.throw(_("Version must hold only letters, digits, dots, plus signs and hyphens."))

	def validate_icon(self):
		if self.icon and not ICON_PATTERN.match(self.icon):
			frappe.throw(_("Icon must name one SVG file in the install root, such as icon.svg."))

	def validate_permissions(self):
		outside = sorted(set(self.permissions) - set(self.requested))
		if outside:
			frappe.throw(
				_('"{0}" never asked for {1}, so it cannot be granted.').format(
					self.extension, ", ".join(outside)
				)
			)

	def permission_list(self, field: str) -> list[str]:
		"""Returns one permission list. Stops if the list has an unknown permission."""
		# Without this, text that is not JSON shows a traceback to the user.
		try:
			keys = frappe.parse_json(self.get(field) or "[]")
		except ValueError:
			keys = None

		label = self.meta.get_label(field)
		if not isinstance(keys, list):
			frappe.throw(_("{0} must be a JSON list.").format(label))

		unknown = sorted(set(keys) - set(PERMISSIONS))
		if unknown:
			frappe.throw(_("Unknown permissions in {0}: {1}").format(label, ", ".join(unknown)))
		return keys

	def validate_readme(self):
		if self.readme and len(self.readme.encode()) > MAX_README_BYTES:
			frappe.throw(_("A README may hold {0} bytes at most.").format(MAX_README_BYTES))

	def write_extension_files(self, files: dict[str, bytes]):
		"""Replaces the install folder with these files. The keys are paths in the folder."""
		root = Path(self.install_path)
		shutil.rmtree(root, ignore_errors=True)
		for relative_path, content in files.items():
			target = root / relative_path
			target.parent.mkdir(parents=True, exist_ok=True)
			target.write_bytes(content)

	def delete_extension_files(self):
		shutil.rmtree(self.install_path, ignore_errors=True)

	def delete_extension_state(self):
		"""Deletes the state rows of all users. A state row links to the installation and stops its delete."""
		frappe.db.delete(STATE_DOCTYPE, {"installation": self.name})
