# Copyright (c) 2026, Frappe Technologies Pvt Ltd and contributors
# For license information, please see license.txt

"""The extensions installed on this site: what the editor reads, and what an
extension manager changes.

The editor and the Extensions panel read one list. The editor mounts the
enabled rows, and the panel shows every row, so a manager can turn one back on.

Every method that changes an installation checks for an extension manager
first, so the user gets a clear refusal before Frappe's own check runs.
"""

from collections import Counter

import frappe
from frappe import _

from builder.extensions.access import (
	INSTALLATION_DOCTYPE,
	assert_extension_manager,
	find_installation,
	is_extension_manager,
)
from builder.extensions.constants import DEV_EXTENSION_VERSION
from builder.utils import has_page_read

RESOURCE_DOCTYPE = "Builder Extension Resource"
TOKEN_DOCTYPE = "Builder Token"

NO_BUILDER_ACCESS = "You need access to Builder to use extensions."


@frappe.whitelist()
@has_page_read(NO_BUILDER_ACCESS)
def get_installations() -> list[dict]:
	"""Every installation on this site, the disabled and development ones included.

	A development installation is listed so the panel can open its record. The
	browser runs its own entry for it, and hides a record no dev server serves.
	"""
	rows = frappe.get_all(
		INSTALLATION_DOCTYPE,
		fields=["name", "enabled", "install_state"],
		order_by="modified desc",
	)
	# a stable sort, so each group keeps the modified order
	rows.sort(key=is_turned_off)
	return [describe_installation(row.name) for row in rows]


def is_turned_off(row: dict) -> bool:
	"""A pending or failed install is not enabled yet, but no manager turned it off."""
	return not row.enabled and row.install_state in (None, "", "Ready")


@frappe.whitelist()
@has_page_read(NO_BUILDER_ACCESS)
def can_manage_extensions() -> bool:
	"""Lets the panel hide what the server would refuse."""
	return is_extension_manager()


@frappe.whitelist(methods=["POST"])
@has_page_read(NO_BUILDER_ACCESS)
def set_extension_enabled(extension: str, enabled: bool) -> None:
	"""Off stops this extension for every user."""
	assert_extension_manager()
	installation = frappe.get_doc(INSTALLATION_DOCTYPE, get_installation(extension))
	installation.enabled = 1 if enabled else 0
	installation.save()


@frappe.whitelist(methods=["POST"])
@has_page_read(NO_BUILDER_ACCESS)
def set_granted_permissions(extension: str, permissions: list[str]) -> list[str]:
	"""Narrow or widen what the site allows.

	The record refuses a permission the manifest never asked for, so the rule has
	one owner and this method only writes what it is given.
	"""
	assert_extension_manager()
	installation = frappe.get_doc(INSTALLATION_DOCTYPE, get_installation(extension))
	installation.granted_permissions = frappe.as_json(permissions)
	installation.save()
	return installation.permissions


@frappe.whitelist()
@has_page_read(NO_BUILDER_ACCESS)
def get_uninstall_summary(extension: str) -> dict:
	"""What the site keeps when a manager removes the extension.

	A doctype holds the site's data, a token styles every page, and a client script
	runs for every visitor, so uninstalling takes none of the three. Naming them
	here is what lets a manager read that before they answer.
	"""
	get_installation(extension)
	made = Counter(frappe.get_all(RESOURCE_DOCTYPE, filters={"extension": extension}, pluck="resource_type"))
	return {
		"resources": [{"resource_type": kind, "count": made[kind]} for kind in sorted(made)],
		"tokens": frappe.db.count(TOKEN_DOCTYPE, {"extension": extension}),
	}


@frappe.whitelist(methods=["POST"])
@has_page_read(NO_BUILDER_ACCESS)
def uninstall_extension(extension: str) -> None:
	"""The site's copy and every user's stored state. `on_trash` takes both."""
	assert_extension_manager()
	frappe.delete_doc(INSTALLATION_DOCTYPE, get_installation(extension))


def describe_installation(installation: str) -> dict:
	"""What a row in the panel shows, and all that the editor needs to mount it.

	The icon is derived, so this reads the document. The row carries the grants,
	so a page reader with no read access to the installation still runs it.
	"""
	row = frappe.get_cached_doc(INSTALLATION_DOCTYPE, installation)
	return {
		"installation_id": row.name,
		"name": row.extension,
		"label": row.label,
		"description": row.description,
		"icon": row.icon_data_uri,
		"version": row.version,
		"entry_url": row.entry_url,
		"source_url": row.source_url,
		"enabled": bool(row.enabled),
		"permissions": row.permissions,
		"install_state": row.install_state,
		"install_error": row.install_error,
		"is_development": row.version == DEV_EXTENSION_VERSION,
	}


def get_installation(extension: str) -> str:
	"""The site's installation of this extension, or a refusal naming it."""
	installation = find_installation(extension)
	if not installation:
		frappe.throw(_('"{0}" is not installed on this site.').format(extension), frappe.PermissionError)
	return installation
