# Copyright (c) 2026, Frappe Technologies Pvt Ltd and contributors
# For license information, please see license.txt

"""How an extension served from a dev server gets a site installation.

The browser loads the entry from the dev server. The installation gives the
extension a record, so the panel can list it and its state calls find it. Only
an extension manager makes one, and only in developer mode.
"""

import frappe
from frappe import _

from builder.extensions.access import (
	INSTALLATION_DOCTYPE,
	assert_extension_manager,
	find_installation,
)
from builder.extensions.constants import DEV_EXTENSION_VERSION


@frappe.whitelist(methods=["POST"])
def install_dev_extension(extension: str) -> None:
	"""Give a dev-server extension an installation.

	An enabled installation of the same extension is refused. The editor would
	load both copies, and a plugin cannot leave the app. A disabled installation
	keeps its record as it stands, so an author can build a new release of an
	extension the site has installed.
	"""
	assert_developer_mode()
	frappe.has_permission("Builder Page", ptype="read", throw=True)
	assert_extension_manager()

	installation = find_installation(extension)
	if not installation:
		create_dev_installation(extension)
		return
	enabled, version = frappe.db.get_value(INSTALLATION_DOCTYPE, installation, ["enabled", "version"])
	if enabled and version != DEV_EXTENSION_VERSION:
		frappe.throw(
			_('"{0}" is installed on this site. Disable it to load its dev server.').format(extension)
		)


def create_dev_installation(extension: str) -> None:
	frappe.get_doc(
		{
			"doctype": INSTALLATION_DOCTYPE,
			"extension": extension,
			"label": extension,
			"version": DEV_EXTENSION_VERSION,
			"enabled": 1,
		}
	).insert()


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
