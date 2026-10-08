# Copyright (c) 2026, Frappe Technologies Pvt Ltd and contributors
# For license information, please see license.txt

"""Checks who can use extensions and what each extension can do.

An extension acts as the editor user. It never gets more access than that user."""

import frappe
from frappe import _

INSTALLATION_DOCTYPE = "Builder Extension"


def find_installation(extension: str, enabled_only: bool = False) -> str | None:
	"""Returns the installation of this extension on the site, or None.

	A site has one installation for each `publisher/name` at most."""
	filters = {"extension": extension}
	if enabled_only:
		filters["enabled"] = 1
	return frappe.db.get_value(INSTALLATION_DOCTYPE, filters, "name")


def assert_extension_access(extension: str, permission: str | None = None) -> str:
	"""Stops the call if the user or the extension has no access. Returns the installation name."""
	if frappe.session.user == "Guest":
		frappe.throw(_("Sign in to use extensions."), frappe.PermissionError)

	frappe.has_permission("Builder Page", ptype="read", throw=True)

	installation = find_installation(extension, enabled_only=True)
	if not installation:
		frappe.throw(_('"{0}" is not installed on this site.').format(extension), frappe.PermissionError)

	assert_permission(installation, extension, permission)

	return installation


def assert_permission(installation: str, extension: str, permission: str | None) -> None:
	"""Stops the call if the installation does not grant this permission.

	The browser bridge does the same check only to show a clear error."""
	if not permission:
		return

	granted = frappe.get_cached_doc(INSTALLATION_DOCTYPE, installation).permissions
	if permission not in granted:
		frappe.throw(_('"{0}" was not granted {1}.').format(extension, permission), frappe.PermissionError)


def is_extension_manager(user: str | None = None) -> bool:
	return frappe.has_permission(INSTALLATION_DOCTYPE, ptype="write", user=user)


def assert_extension_manager() -> None:
	if not is_extension_manager():
		frappe.throw(
			_("Only a System Manager or a Website Manager can change extensions."),
			frappe.PermissionError,
		)
