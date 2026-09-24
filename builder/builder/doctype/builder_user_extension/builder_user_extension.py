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
	CAPABILITIES,
	ENTRY_FILE,
	EXTENSION_NAME_PATTERN,
	EXTENSIONS_FOLDER,
	ICON_PATTERN,
	MAX_README_BYTES,
	MAX_SOURCE_BYTES,
	VERSION_PATTERN,
)

GRANT_DOCTYPE = "Builder Extension DocType Grant"
STATE_DOCTYPE = "Builder Extension State"


class BuilderUserExtension(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		checksum: DF.Data | None
		description: DF.SmallText | None
		enabled: DF.Check
		extension: DF.Data
		granted_capabilities: DF.SmallText | None
		icon: DF.Data | None
		install_error: DF.SmallText | None
		install_state: DF.Literal["Installing", "Ready", "Failed"]
		installed_on: DF.Datetime | None
		label: DF.Data | None
		readme: DF.LongText | None
		requested_capabilities: DF.SmallText | None
		source_url: DF.Data | None
		user: DF.Link
		version: DF.Data
	# end: auto-generated types

	def autoname(self):
		# a uuid, and (user, extension) is looked up by field, the way Builder Token
		# looks up (extension, key). The name is also the install directory, so it
		# must hold no separator
		if not self.name:
			self.name = str(uuid.uuid4())

	def before_insert(self):
		self.installed_on = now()

	def validate(self):
		self.validate_identity()
		self.validate_icon()
		self.validate_capabilities()
		self.validate_readme()

	def on_trash(self):
		self.delete_extension_state()
		self.delete_doctype_grants()
		self.delete_extension_files()

	@property
	def install_path(self) -> str:
		"""This user's own copy. Private, so nothing but Builder reads it."""
		return get_files_path(f"{EXTENSIONS_FOLDER}/{self.name}", is_private=True)

	@property
	def capabilities(self) -> list[str]:
		"""What this user allowed. Every gate reads this list and no other."""
		return self.capability_list("granted_capabilities")

	@property
	def requested(self) -> list[str]:
		"""What the manifest asked for. A grant cannot reach outside it."""
		return self.capability_list("requested_capabilities")

	@property
	def source(self) -> str:
		"""The built entry, which the editor reads and posts into a frame.

		A frame sends no session, so no route can check who is asking. The editor
		reads it under its own session instead.
		"""
		entry = Path(self.install_path) / ENTRY_FILE
		if not entry.is_file():
			frappe.throw(_('"{0}" has no installed {1}.').format(self.extension, ENTRY_FILE))

		size = entry.stat().st_size
		if size > MAX_SOURCE_BYTES:
			frappe.throw(
				_('"{0}" is {1} bytes, and {2} is the most one extension may hold.').format(
					self.extension, size, MAX_SOURCE_BYTES
				)
			)
		return entry.read_text()

	@property
	def icon_data_uri(self) -> str | None:
		"""None when the package ships no icon. The editor draws its own glyph then.

		A data URI, not a URL, because no public route serves one user's files.
		"""
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

	def validate_capabilities(self):
		outside = sorted(set(self.capabilities) - set(self.requested))
		if outside:
			frappe.throw(
				_('"{0}" never asked for {1}, so it cannot be granted.').format(
					self.extension, ", ".join(outside)
				)
			)

	def capability_list(self, field: str) -> list[str]:
		"""One of the two lists, parsed and checked against what Builder has."""
		# parse_json raises on text that is not JSON, which would reach the user as a
		# traceback instead of the message below
		try:
			keys = frappe.parse_json(self.get(field) or "[]")
		except ValueError:
			keys = None

		label = self.meta.get_label(field)
		if not isinstance(keys, list):
			frappe.throw(_("{0} must be a JSON list.").format(label))

		unknown = sorted(set(keys) - set(CAPABILITIES))
		if unknown:
			frappe.throw(_("Unknown capabilities in {0}: {1}").format(label, ", ".join(unknown)))
		return keys

	def validate_readme(self):
		if self.readme and len(self.readme.encode()) > MAX_README_BYTES:
			frappe.throw(_("A README may hold {0} bytes at most.").format(MAX_README_BYTES))

	def write_extension_files(self, files: dict[str, bytes]):
		"""Replace this user's copy with the files a frame loads.

		Keyed by path under the install root, so `main.js` lands where `source`
		reads it. Replaces the whole directory, so a rebuild leaves nothing of the
		last one behind.
		"""
		root = Path(self.install_path)
		shutil.rmtree(root, ignore_errors=True)
		for relative_path, content in files.items():
			target = root / relative_path
			target.parent.mkdir(parents=True, exist_ok=True)
			target.write_bytes(content)

	def delete_extension_files(self):
		"""This user's copy alone. Another user's copy is another directory."""
		shutil.rmtree(self.install_path, ignore_errors=True)

	def delete_extension_state(self):
		"""A state row Links to this record, so Frappe refuses the delete while one stands."""
		for state in frappe.get_all(STATE_DOCTYPE, filters={"installation": self.name}, pluck="name"):
			frappe.delete_doc(STATE_DOCTYPE, state, ignore_permissions=True)

	def delete_doctype_grants(self):
		"""What this user allowed this copy, and nobody else's answer.

		Nothing the extension made goes with it. A doctype, a token and a client
		script all serve the site, so all three outlive one user leaving.
		"""
		for grant in frappe.get_all(GRANT_DOCTYPE, filters={"installation": self.name}, pluck="name"):
			frappe.delete_doc(GRANT_DOCTYPE, grant, ignore_permissions=True)


TABLE = "tabBuilder User Extension"
UNIQUE_INDEX = "unique_user_extension"
SOURCE_SCOPED_INDEX = "unique_user_source_extension"


def on_doctype_update():
	"""One installation per user and extension.

	`publisher/name` is the whole identity. A second install of one name, from any
	source, is refused, so `source_url` stays a plain record of where the files
	came from and never scopes a lookup.
	"""
	if frappe.db.has_index(TABLE, SOURCE_SCOPED_INDEX):
		frappe.db.sql_ddl(f"alter table `{TABLE}` drop index `{SOURCE_SCOPED_INDEX}`")

	frappe.db.add_unique("Builder User Extension", ["user", "extension"], constraint_name=UNIQUE_INDEX)
