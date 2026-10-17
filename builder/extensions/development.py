# Copyright (c) 2026, Frappe Technologies Pvt Ltd and contributors
# For license information, please see license.txt

"""How an extension served from a dev server gets a site installation.

The installation lets a dev extension pass the same server checks as an
installed one. Only an extension manager makes one, and only in developer mode.
"""

import json

import frappe
from frappe import _

from builder.extensions.access import (
	INSTALLATION_DOCTYPE,
	assert_extension_manager,
	find_installation,
)
from builder.extensions.constants import DEV_EXTENSION_VERSION


@frappe.whitelist(methods=["POST"])
def install_dev_extension(extension: str, permissions: list[str] | None = None) -> list[str]:
	"""Give a dev-server extension an installation, and answer with what it grants.

	The gate then needs no bypass: a development extension passes it the way an
	installed one does.

	The manifest names the permissions, so the record holds the list the gate
	reads and a manager narrows it the way they narrow an installed extension's. The
	record refuses one Builder does not have, and refuses granting outside what
	was asked for, so a caller cannot widen its own reach by asking.

	Loading again rewrites both lists. That is how a developer picks up a manifest
	they just edited, and how they undo a narrowing they were testing with.

	An extension the site already installed keeps that installation as it stands.
	Building one you also run is the ordinary case, and its release already
	answered for its own permissions.

	The installation is the site's, like any other, so only a manager makes one.
	"""
	assert_developer_mode()
	frappe.has_permission("Builder Page", ptype="read", throw=True)
	assert_extension_manager()

	asked = json.dumps(permissions or [])
	existing = find_installation(extension)
	if existing:
		return refresh_dev_permissions(existing, asked)

	installation = frappe.get_doc(
		{
			"doctype": INSTALLATION_DOCTYPE,
			"extension": extension,
			"label": extension,
			"version": DEV_EXTENSION_VERSION,
			"requested_permissions": asked,
			"granted_permissions": asked,
			"enabled": 1,
		}
	).insert()
	return installation.permissions


def refresh_dev_permissions(installation: str, asked: str) -> list[str]:
	"""A development installation follows its manifest. A real one is left alone."""
	document = frappe.get_cached_doc(INSTALLATION_DOCTYPE, installation)
	if document.version != DEV_EXTENSION_VERSION:
		return document.permissions

	document.requested_permissions = asked
	document.granted_permissions = asked
	document.save()
	return document.permissions


@frappe.whitelist(methods=["POST"])
def remove_dev_extension(extension: str) -> None:
	"""Remove a development installation.

	Quiet about an installation this method did not make. The name may belong to
	an extension the site really installed.
	"""
	assert_developer_mode()
	assert_extension_manager()

	installation = find_installation(extension)
	if not installation:
		return

	document = frappe.get_doc(INSTALLATION_DOCTYPE, installation)
	if document.version != DEV_EXTENSION_VERSION:
		return

	document.delete()


def assert_developer_mode() -> None:
	if not frappe.conf.get("developer_mode"):
		frappe.throw(_("Development extensions are unavailable outside developer mode."))
