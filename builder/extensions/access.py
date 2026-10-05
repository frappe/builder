# Copyright (c) 2026, Frappe Technologies Pvt Ltd and contributors
# For license information, please see license.txt

"""Who can do what with extensions.

An extension acts as the user who uses the editor, and never as more.
`assert_extension_access` runs four checks before a call gets site data. They
live here together so no method can be written with one forgotten:

1. Somebody is signed in.
2. That person can use Builder.
3. The site installed this extension and left it on.
4. The installation grants the permission the method needs.

Frappe's own permission check runs last, for the user who calls. Nothing here
widens it. The user comes from `frappe.session.user`, and a caller cannot name
one.

Changing an installation is a different right: write access to the Builder
Extension doctype. Its role permissions decide who has it.
"""

import frappe
from frappe import _

INSTALLATION_DOCTYPE = "Builder Extension"


def find_installation(extension: str, enabled_only: bool = False) -> str | None:
	"""The site's installation of this extension, or None.

	`publisher/name` is the whole identity: a site holds one installation of it at
	most, whatever source the files came from. The gate sets `enabled_only`.
	Managing an installation must reach a disabled one, because turning it back on
	is the point.
	"""
	filters = {"extension": extension}
	if enabled_only:
		filters["enabled"] = 1
	return frappe.db.get_value(INSTALLATION_DOCTYPE, filters, "name")


def assert_extension_access(extension: str, permission: str | None = None) -> str:
	"""Refuse unless this user may do this. Answers with the installation name."""
	if frappe.session.user == "Guest":
		frappe.throw(_("Sign in to use extensions."), frappe.PermissionError)

	frappe.has_permission("Builder Page", ptype="read", throw=True)

	installation = find_installation(extension, enabled_only=True)
	if not installation:
		frappe.throw(_('"{0}" is not installed on this site.').format(extension), frappe.PermissionError)

	assert_permission(installation, extension, permission)

	return installation


def assert_permission(installation: str, extension: str, permission: str | None) -> None:
	"""What an extension manager allowed, checked where the writing happens.

	The browser bridge checks this before it sends the call, to give an extension a
	clear error. That check protects nothing: a frame cannot reach these methods,
	but the editor page can.
	"""
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
			_(
				"Only a System Manager or a Website Manager can change extensions."
			),
			frappe.PermissionError,
		)
