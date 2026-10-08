# Copyright (c) 2026, Frappe Technologies Pvt Ltd and contributors
# For license information, please see license.txt

"""Methods that add and remove the installation of an extension from a dev server.

With this installation, the server checks a dev extension like an installed extension."""

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
	"""Adds an installation for a dev extension. Returns the granted permissions.
	Each load copies the manifest permissions again. An installed extension with
	the same name keeps its installation."""
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
	"""Copies the manifest permissions to a dev installation. Does not change other installations."""
	document = frappe.get_cached_doc(INSTALLATION_DOCTYPE, installation)
	if document.version != DEV_EXTENSION_VERSION:
		return document.permissions

	document.requested_permissions = asked
	document.granted_permissions = asked
	document.save()
	return document.permissions


@frappe.whitelist(methods=["POST"])
def remove_dev_extension(extension: str) -> None:
	"""Removes a dev installation. Does nothing for an installed extension with the same name."""
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
