# Copyright (c) 2026, Frappe Technologies Pvt Ltd and contributors
# For license information, please see license.txt

"""What a user does with an extension they installed.

The editor and the Extensions panel read one list. The editor mounts the
enabled rows, and the panel shows every row, so a user can turn one back on.

Every method here finds the row through the session user. A caller names an
extension and never a person.
"""

from collections import Counter

import frappe
from frappe import _

from builder.extensions.access import (
	GRANT_DOCTYPE,
	INSTALLATION_DOCTYPE,
	find_own_installation,
)
from builder.extensions.constants import DEV_EXTENSION_VERSION
from builder.extensions.data import ACCESS_FIELDS, read_answers, upsert_grant
from builder.utils import has_page_read

RESOURCE_DOCTYPE = "Builder Extension Resource"
TOKEN_DOCTYPE = "Builder Token"

NOT_INSTALLED = "You have not installed this extension."


@frappe.whitelist()
@has_page_read(NOT_INSTALLED)
def get_user_installations() -> list[dict]:
	"""Every installation of this user, the disabled and development ones included.

	A disabled extension has to stay visible. Hiding it would leave no way to turn
	it back on but the bench. It sorts last, and the last edited sorts first in
	each group.

	A development installation is listed so the panel can open its record. The
	browser runs its own entry for it, and hides a record no dev server serves.
	"""
	rows = frappe.get_all(
		INSTALLATION_DOCTYPE,
		filters={"user": frappe.session.user},
		fields=["name", "enabled", "install_state"],
		order_by="modified desc",
	)
	# a stable sort, so each group keeps the modified order
	rows.sort(key=is_turned_off)
	return [describe_installation(row.name) for row in rows]


def is_turned_off(row: dict) -> bool:
	"""A pending or failed install is not enabled yet, but no user turned it off."""
	return not row.enabled and row.install_state in (None, "", "Ready")


def installation_doctype_grants(installation: str) -> list[dict]:
	"""Every doctype this user answered for, as the panel lists them."""
	return frappe.get_all(
		GRANT_DOCTYPE,
		filters={"installation": installation},
		fields=["document_type", *ACCESS_FIELDS.values()],
		order_by="document_type asc",
	)


@frappe.whitelist(methods=["POST"])
@has_page_read(NOT_INSTALLED)
def set_extension_grant(extension: str, doctype: str, answers: dict | None = None) -> list[dict]:
	"""Write the three answers for one doctype, and answer with every grant after it.

	`record_extension_grant` merges, because an extension asking for more must not
	drop what it already has. This writes exactly what it is given: the user
	narrows a grant here, and merging would never let them.

	The row stays when all three answers are "not asked", so the panel keeps
	listing the doctype. The extension asks again about each access, the way it
	does when no grant names the doctype. A denial stops the asking for that access.

	The gate is the user's own installation, not the extension's access. They most
	want an answer back after they disable the extension or turn `data.access`
	off, and the extension gate refuses both.
	"""
	installation = own_installation(extension)
	upsert_grant(installation, doctype, read_answers(answers))

	return installation_doctype_grants(installation)


@frappe.whitelist(methods=["POST"])
@has_page_read(NOT_INSTALLED)
def set_extension_enabled(extension: str, enabled: bool) -> None:
	"""Off stops this user's frames. It stops nobody else's."""
	installation = frappe.get_doc(INSTALLATION_DOCTYPE, own_installation(extension))
	installation.enabled = 1 if enabled else 0
	installation.save()


@frappe.whitelist(methods=["POST"])
@has_page_read(NOT_INSTALLED)
def set_granted_capabilities(extension: str, capabilities: list[str]) -> list[str]:
	"""Narrow or widen what this user allows.

	The record refuses a capability the manifest never asked for, so the rule has
	one owner and this method only writes what it is given.
	"""
	installation = frappe.get_doc(INSTALLATION_DOCTYPE, own_installation(extension))
	installation.granted_capabilities = frappe.as_json(capabilities)
	installation.save()
	return installation.capabilities


@frappe.whitelist()
@has_page_read(NOT_INSTALLED)
def get_uninstall_summary(extension: str) -> dict:
	"""What the site keeps when this user removes the extension.

	A doctype holds the site's data, a token styles every page, and a client script
	runs for every visitor, so uninstalling takes none of the three. Naming them
	here is what lets a user read that before they answer.
	"""
	own_installation(extension)
	made = Counter(frappe.get_all(RESOURCE_DOCTYPE, filters={"extension": extension}, pluck="resource_type"))
	return {
		"resources": [{"resource_type": kind, "count": made[kind]} for kind in sorted(made)],
		"tokens": frappe.db.count(TOKEN_DOCTYPE, {"extension": extension}),
		"other_users": frappe.db.count(
			INSTALLATION_DOCTYPE, {"extension": extension, "user": ["!=", frappe.session.user]}
		),
	}


@frappe.whitelist(methods=["POST"])
@has_page_read(NOT_INSTALLED)
def uninstall_extension(extension: str) -> None:
	"""This user's copy, their grants and their stored state, and nothing else.

	`on_trash` takes all three. What the extension made stays, and
	`get_uninstall_summary` names it before the user answers.
	"""
	frappe.delete_doc(INSTALLATION_DOCTYPE, own_installation(extension))


def describe_installation(installation: str) -> dict:
	"""What a row in the panel shows. The icon is derived, so this reads the document.

	`installation_id` names the document itself, not the extension. The panel
	reads it to open the same live document the editor already keeps.
	"""
	row = frappe.get_cached_doc(INSTALLATION_DOCTYPE, installation)
	return {
		"installation_id": row.name,
		"name": row.extension,
		"label": row.label,
		"description": row.description,
		"icon": row.icon_data_uri,
		"version": row.version,
		"source_url": row.source_url,
		"enabled": bool(row.enabled),
		"install_state": row.install_state,
		"install_error": row.install_error,
		"is_development": row.version == DEV_EXTENSION_VERSION,
	}


def own_installation(extension: str) -> str:
	"""This user's installation of this extension, or a refusal naming it."""
	installation = find_own_installation(extension)
	if not installation:
		frappe.throw(_('"{0}" is not installed for you.').format(extension), frappe.PermissionError)
	return installation
