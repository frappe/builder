# Copyright (c) 2026, Frappe Technologies Pvt Ltd and contributors
# For license information, please see license.txt

"""Turn one site-wide extension record into one installation per user.

The old record held the identity, the files, the switch and the capabilities for
everybody. They go to the user who installed the extension, with their own copy
of the files.

Nobody else gets an installation, and every grant goes. A site grant recorded one
person's answer, and giving it to every user would grant access nobody agreed to.
Every user is asked again the first time an extension wants a doctype.

What the extension made stays. A doctype, a token and a client script all outlive
this change, under rows that now name the extension.
"""

import json
import shutil
from pathlib import Path

import frappe
from frappe.utils import get_files_path

OLD_DOCTYPE = "Builder Extension"
INSTALLATION_DOCTYPE = "Builder User Extension"
DEV_VERSION = "0.0.0-dev"

# What a single-file build leaves behind. Anything else means the extension was
# split into chunks, which no frame can import now that the code travels in the
# handshake.
EXPECTED_FILES = {"main.js", "manifest.json"}


def execute():
	if not frappe.db.table_exists(OLD_DOCTYPE):
		return

	for old in read_old_extensions():
		rename_owned_rows(old)
		if old.enabled and old.version != DEV_VERSION:
			install_for_owner(old)

	# every grant was site-wide, and one person's answer is not everybody's
	frappe.db.delete("Builder Extension DocType Grant")
	frappe.delete_doc("DocType", OLD_DOCTYPE, ignore_missing=True, force=True)


def read_old_extensions() -> list[frappe._dict]:
	"""Raw SQL, because the doctype is gone and only its table is left."""
	return frappe.db.sql(
		f"""select name, extension_name, owner, enabled, version, label,
		           description, icon, checksum, capabilities, creation
		    from `tab{OLD_DOCTYPE}`""",
		as_dict=True,
	)


def rename_owned_rows(old: frappe._dict) -> None:
	"""What the extension made now names the extension, not the record's slug."""
	for doctype in ("Builder Token", "Builder Extension Resource"):
		frappe.db.set_value(
			doctype, {"extension": old.name}, "extension", old.extension_name, update_modified=False
		)


def install_for_owner(old: frappe._dict) -> None:
	if not frappe.db.exists("User", old.owner):
		frappe.log_error(
			title="Builder extension not migrated",
			message=f"{old.extension_name} was installed by {old.owner}, who no longer exists.",
		)
		return

	installation = frappe.get_doc(
		{
			"doctype": INSTALLATION_DOCTYPE,
			"user": old.owner,
			"extension": old.extension_name,
			"label": old.label,
			"description": old.description,
			"icon": old.icon,
			"version": old.version,
			"checksum": old.checksum,
			# The site record held one list, which was both the ask and the grant
			"requested_capabilities": old.capabilities or json.dumps([]),
			"granted_capabilities": old.capabilities or json.dumps([]),
			"enabled": 1,
		}
	).insert(ignore_permissions=True)
	frappe.db.set_value(
		INSTALLATION_DOCTYPE, installation.name, "installed_on", old.creation, update_modified=False
	)

	move_files(old, installation)


def move_files(old: frappe._dict, installation) -> None:
	source = Path(get_files_path(f"extensions/{old.name}@{old.version}", is_private=True))
	if not source.is_dir():
		return

	shutil.move(str(source), installation.install_path)
	if not is_single_file(Path(installation.install_path), old.icon):
		disable_split_install(old, installation)


def is_single_file(install: Path, icon: str | None) -> bool:
	expected = EXPECTED_FILES | ({icon} if icon else set())
	return {path.name for path in install.rglob("*") if path.is_file()} <= expected


def disable_split_install(old: frappe._dict, installation) -> None:
	"""A split build cannot run, so it is turned off rather than left to fail.

	Chunks used to load from an asset route by URL. The entry now travels in the
	handshake, so a relative import inside it resolves against nothing. Rebuild
	with the current SDK and install again.
	"""
	frappe.db.set_value(INSTALLATION_DOCTYPE, installation.name, "enabled", 0)
	frappe.log_error(
		title="Builder extension needs a rebuild",
		message=(
			f"{old.extension_name} was installed as more than one file, so it is turned off. "
			"Build it with the current extension SDK and install it again."
		),
	)
