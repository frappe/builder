# Copyright (c) 2026, Frappe Technologies Pvt Ltd and contributors
# For license information, please see license.txt

"""Permission checks before an extension performs an action.

An extension is installed for the whole site. It acts as the user who is using
the editor, and never as more. Four checks run before a call reaches site data,
and they live here together so no method can be written with one forgotten:

1. Somebody is signed in.
2. That person can use Builder.
3. The site installed this extension and left it on.
4. The installation grants the capability the method needs.

Frappe's own permission runs last, for the user who is calling. Nothing here
widens it. The user comes from `frappe.session.user`, and a caller cannot name
one.

Changing an installation is a separate right. A System Manager has it, and so
does the role that Builder Settings names.
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


def assert_extension_access(extension: str, capability: str | None = None) -> str:
	"""Refuse unless this user may do this. Answers with the installation name."""
	if frappe.session.user == "Guest":
		frappe.throw(_("Sign in to use extensions."), frappe.PermissionError)

	frappe.has_permission("Builder Page", ptype="read", throw=True)

	installation = find_installation(extension, enabled_only=True)
	if not installation:
		frappe.throw(_('"{0}" is not installed on this site.').format(extension), frappe.PermissionError)

	assert_capability(installation, extension, capability)

	return installation


def assert_capability(installation: str, extension: str, capability: str | None) -> None:
	"""What an extension manager allowed, checked where the writing happens.

	The browser bridge checks this before it sends the call, to give an extension a
	clear error. That check protects nothing: a frame cannot reach these methods,
	but the editor page can.
	"""
	if not capability:
		return

	granted = frappe.get_cached_doc(INSTALLATION_DOCTYPE, installation).capabilities
	if capability not in granted:
		frappe.throw(_('"{0}" was not granted {1}.').format(extension, capability), frappe.PermissionError)


def is_extension_manager(user: str | None = None) -> bool:
	"""A System Manager, a Website Manager, or a user with the role Builder Settings names."""
	additional_role = frappe.db.get_single_value(
		"Builder Settings", "additional_extension_manager_role", cache=False
	)
	return bool({"System Manager", "Website Manager", additional_role} & set(frappe.get_roles(user)))


def assert_extension_manager() -> None:
	if not is_extension_manager():
		frappe.throw(
			_(
				"Only an extension manager can change extensions. Builder Settings can name an additional role."
			),
			frappe.PermissionError,
		)
