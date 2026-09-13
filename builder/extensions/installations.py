# Copyright (c) 2026, Frappe Technologies Pvt Ltd and contributors
# For license information, please see license.txt

"""What a user does with an extension they installed.

`registry.py` is what the editor loads, so it lists only what mounts a frame.
This is what the Extensions panel manages, so it lists a disabled installation
too, and it answers with the version, the source and the README a row never
shows.

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
from builder.extensions.data import ACCESS_FIELDS, forget_grant, read_access, upsert_grant
from builder.utils import has_page_read

RESOURCE_DOCTYPE = "Builder Extension Resource"
TOKEN_DOCTYPE = "Builder Token"

NOT_INSTALLED = "You have not installed this extension."


@frappe.whitelist()
@has_page_read(NOT_INSTALLED)
def get_user_installations() -> list[dict]:
	"""Every installation of this user, the disabled ones included.

	A disabled extension has to stay visible. Hiding it would leave no way to turn
	it back on but the bench.
	"""
	names = frappe.get_all(
		INSTALLATION_DOCTYPE,
		filters={"user": frappe.session.user, "version": ["!=", DEV_EXTENSION_VERSION]},
		pluck="name",
		order_by="label asc",
	)
	return [describe_installation(name) for name in names]


def installation_grants(installation: str) -> list[dict]:
	"""Every doctype this user answered for, as the panel lists them."""
	return frappe.get_all(
		GRANT_DOCTYPE,
		filters={"installation": installation},
		fields=["document_type", "can_read", "can_write", "can_delete", "denied"],
		order_by="document_type asc",
	)


@frappe.whitelist(methods=["POST"])
@has_page_read(NOT_INSTALLED)
def set_extension_grant(
	extension: str, doctype: str, access: list[str] | None = None, denied: bool = False
) -> list[dict]:
	"""Write what stands for one doctype, and answer with every grant after it.

	`record_extension_grant` merges, because an extension asking for more must not
	drop what it already has. This writes exactly what it is given: the user
	narrows a grant here, and merging would never let them.

	Allowing nothing while denying nothing is not an answer, so it is dropped
	rather than stored. An extension asks again when no grant names it, which is
	what an empty one would mean. A denial is stored, because it stops the asking.

	The gate is the user's own installation, not the extension's access. They most
	want an answer back after they disable the extension or turn `data.access`
	off, and the extension gate refuses both.
	"""
	installation = own_installation(extension)
	allowed = set() if denied else read_access(access)

	if not allowed and not denied:
		forget_grant(installation, doctype)
	else:
		written = {field: int(name in allowed) for name, field in ACCESS_FIELDS.items()}
		upsert_grant(installation, doctype, {**written, "denied": int(denied)})

	return installation_grants(installation)


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
	}


def own_installation(extension: str) -> str:
	"""This user's installation of this extension, or a refusal naming it."""
	installation = find_own_installation(extension)
	if not installation:
		frappe.throw(_('"{0}" is not installed for you.').format(extension), frappe.PermissionError)
	return installation
