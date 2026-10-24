# Copyright (c) 2026, Frappe Technologies Pvt Ltd and contributors
# For license information, please see license.txt

"""How a plugin served from a dev server gets a site installation.

The browser loads the entry from the dev server. The installation gives the
plugin a record, so the panel can list it and its state calls find it. Only
a plugin manager makes one, and only in developer mode.
"""

import frappe
from frappe import _

from builder.plugins.access import (
	INSTALLATION_DOCTYPE,
	assert_plugin_manager,
	find_installation,
)
from builder.plugins.constants import DEV_PLUGIN_VERSION


@frappe.whitelist(methods=["POST"])
def install_dev_plugin(plugin: str) -> None:
	"""Give a dev-server plugin an installation.

	An enabled installation of the same plugin is refused. The editor would
	load both copies, and a Vue plugin cannot leave the app. A disabled installation
	keeps its record as it stands, so an author can build a new release of an
	plugin the site has installed.
	"""
	assert_developer_mode()
	frappe.has_permission("Builder Page", ptype="read", throw=True)
	assert_plugin_manager()

	installation = find_installation(plugin)
	if not installation:
		create_dev_installation(plugin)
		return
	enabled, version = frappe.db.get_value(INSTALLATION_DOCTYPE, installation, ["enabled", "version"])
	if enabled and version != DEV_PLUGIN_VERSION:
		frappe.throw(_('"{0}" is installed on this site. Disable it to load its dev server.').format(plugin))


def create_dev_installation(plugin: str) -> None:
	frappe.get_doc(
		{
			"doctype": INSTALLATION_DOCTYPE,
			"plugin": plugin,
			"source": "Development",
			"label": plugin,
			"version": DEV_PLUGIN_VERSION,
			"enabled": 1,
		}
	).insert()


@frappe.whitelist(methods=["POST"])
def remove_dev_plugin(plugin: str) -> None:
	"""Remove a development installation.

	Quiet about an installation this method did not make. The name may belong to
	a plugin the site really installed.
	"""
	assert_developer_mode()
	assert_plugin_manager()

	installation = find_installation(plugin)
	if not installation:
		return

	document = frappe.get_doc(INSTALLATION_DOCTYPE, installation)
	if document.version != DEV_PLUGIN_VERSION:
		return

	document.delete()


def assert_developer_mode() -> None:
	if not frappe.conf.get("developer_mode"):
		frappe.throw(_("Development plugins are unavailable outside developer mode."))
