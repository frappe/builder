# Copyright (c) 2026, Frappe Technologies Pvt Ltd and contributors
# For license information, please see license.txt

"""Methods that list and change the extensions installed on the site.

The editor mounts the enabled rows. The Extensions panel shows all rows."""

import frappe
from frappe import _

from builder.extensions.access import (
	INSTALLATION_DOCTYPE,
	assert_extension_manager,
	find_installation,
)
from builder.extensions.constants import DEV_EXTENSION_VERSION
from builder.utils import has_page_read

NO_BUILDER_ACCESS = "You need access to Builder to use extensions."


@frappe.whitelist()
@has_page_read(NO_BUILDER_ACCESS)
def get_installations() -> list[dict]:
	"""Returns all installations on the site, with the disabled and dev installations."""
	rows = frappe.get_all(
		INSTALLATION_DOCTYPE,
		fields=["name", "enabled", "install_state"],
		order_by="modified desc",
	)
	# The sort is stable. So each group keeps the order by date.
	rows.sort(key=is_turned_off)
	return [describe_installation(row.name) for row in rows]


def is_turned_off(row: dict) -> bool:
	"""Returns True if a manager disabled the extension. A pending or failed install is not disabled."""
	return not row.enabled and row.install_state in (None, "", "Ready")


@frappe.whitelist(methods=["POST"])
@has_page_read(NO_BUILDER_ACCESS)
def set_extension_enabled(extension: str, enabled: bool) -> None:
	"""Enables or disables the extension for all users."""
	assert_extension_manager()
	installation = frappe.get_doc(INSTALLATION_DOCTYPE, get_installation(extension))
	installation.enabled = 1 if enabled else 0
	installation.save()


@frappe.whitelist(methods=["POST"])
@has_page_read(NO_BUILDER_ACCESS)
def set_granted_permissions(extension: str, permissions: list[str]) -> list[str]:
	"""Sets the granted permissions. The record refuses a permission that the manifest does not ask for."""
	assert_extension_manager()
	installation = frappe.get_doc(INSTALLATION_DOCTYPE, get_installation(extension))
	installation.granted_permissions = frappe.as_json(permissions)
	installation.save()
	return installation.permissions


@frappe.whitelist(methods=["POST"])
@has_page_read(NO_BUILDER_ACCESS)
def uninstall_extension(extension: str) -> None:
	"""Deletes the installation. `on_trash` deletes the files and the state of all users."""
	assert_extension_manager()
	frappe.delete_doc(INSTALLATION_DOCTYPE, get_installation(extension))


def describe_installation(installation: str) -> dict:
	"""Returns the data for one row of the panel. The editor also uses it to mount the extension.

	The row has the permissions. So a user without read access to the installation can run it."""
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
	"""Returns the installation of this extension. Stops the call if there is no installation."""
	installation = find_installation(extension)
	if not installation:
		frappe.throw(_('"{0}" is not installed on this site.').format(extension), frappe.PermissionError)
	return installation
