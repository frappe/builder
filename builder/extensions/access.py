# Copyright (c) 2026, Frappe Technologies Pvt Ltd and contributors
# For license information, please see license.txt

"""Who can do what with extensions.

An extension runs in the editor with the access of the user who opens it, so
Frappe's own permission checks apply to everything it does. These checks only
cover Builder's own extension records.

Changing an installation is a different right: write access to the Builder
Extension doctype. A System Manager and a Website Manager have it. An installed
extension runs with the access of every editor user, and a Website Manager can
already add scripts to the site's pages through Builder Client Script.
"""

import frappe
from frappe import _

INSTALLATION_DOCTYPE = "Builder Extension"


def find_installation(extension: str, enabled_only: bool = False) -> str | None:
	"""The site's installation of this extension, or None.

	`publisher/name` is the whole identity: a site holds one installation of it at
	most. Managing an installation must reach a disabled one, because turning it
	back on is the point.
	"""
	filters = {"extension": extension}
	if enabled_only:
		filters["enabled"] = 1
	return frappe.db.get_value(INSTALLATION_DOCTYPE, filters, "name")


def assert_extension_access(extension: str) -> str:
	"""Refuse unless this user uses Builder and the site runs this extension. Answers with the installation name."""
	if frappe.session.user == "Guest":
		frappe.throw(_("Sign in to use extensions."), frappe.PermissionError)

	frappe.has_permission("Builder Page", ptype="read", throw=True)

	installation = find_installation(extension, enabled_only=True)
	if not installation:
		frappe.throw(_('"{0}" is not installed on this site.').format(extension), frappe.PermissionError)
	return installation


def is_extension_manager(user: str | None = None) -> bool:
	return frappe.has_permission(INSTALLATION_DOCTYPE, ptype="write", user=user)


def assert_extension_manager() -> None:
	if not is_extension_manager():
		frappe.throw(_("Only a System Manager or a Website Manager can change extensions."), frappe.PermissionError)
