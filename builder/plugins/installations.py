# Copyright (c) 2026, Frappe Technologies Pvt Ltd and contributors
# For license information, please see license.txt

"""The plugins installed on this site: what the editor reads, and what an
plugin manager changes.

The editor and the Plugins panel read one list. The editor loads the enabled
rows, and the panel shows every row, so a manager can turn one back on.

Every method that changes an installation checks for a plugin manager
first, so the user gets a clear refusal before Frappe's own check runs.
"""

import frappe
from frappe import _
from frappe.utils.background_jobs import is_job_enqueued

from builder.plugins.access import (
	INSTALLATION_DOCTYPE,
	assert_plugin_manager,
	find_installation,
	is_plugin_manager,
)
from builder.plugins.constants import DEV_PLUGIN_VERSION
from builder.utils import has_page_read

NO_BUILDER_ACCESS = "You need access to Builder to use plugins."


@frappe.whitelist()
@has_page_read(NO_BUILDER_ACCESS)
def get_installations() -> list[dict]:
	"""Every installation on this site, the disabled and development ones included.

	A development installation is listed so the panel can open its record. The
	browser loads its entry from the dev server, and hides a record no dev server serves.
	"""
	rows = frappe.get_all(
		INSTALLATION_DOCTYPE,
		fields=["name", "enabled", "install_state"],
		order_by="modified desc",
	)
	# a stable sort, so each group keeps the modified order
	rows.sort(key=is_turned_off)
	return [describe_installation(row.name) | {"install_state": get_install_state(row)} for row in rows]


def get_install_state(row: dict) -> str | None:
	"""A crashed worker cannot mark its row. So an `Installing` row with no job reads as `Failed`."""
	if row.install_state == "Installing" and not is_job_enqueued(install_job_id(row.name)):
		return "Failed"
	return row.install_state


def install_job_id(installation: str) -> str:
	return f"builder_plugin_install_{installation}"


def is_turned_off(row: dict) -> bool:
	"""A pending or failed install is not enabled yet, but no manager turned it off."""
	return not row.enabled and row.install_state in (None, "", "Ready")


@frappe.whitelist()
@has_page_read(NO_BUILDER_ACCESS)
def can_manage_plugins() -> bool:
	"""Lets the panel hide what the server would refuse."""
	return is_plugin_manager()


@frappe.whitelist(methods=["POST"])
@has_page_read(NO_BUILDER_ACCESS)
def set_plugin_enabled(plugin: str, enabled: bool) -> None:
	"""Off stops this plugin for every user, from their next editor load."""
	assert_plugin_manager()
	installation = frappe.get_doc(INSTALLATION_DOCTYPE, get_installation(plugin))
	installation.enabled = 1 if enabled else 0
	installation.save()


@frappe.whitelist()
@has_page_read(NO_BUILDER_ACCESS)
def get_installation_details(plugin: str) -> dict:
	"""What the details pane shows beyond the list row. A page reader may not read the installation itself.

	`is_updating` lets the pane recover when the realtime message of an update job never came.
	"""
	row = frappe.get_cached_doc(INSTALLATION_DOCTYPE, get_installation(plugin))
	return {
		"installed_on": row.installed_on,
		"readme": row.readme,
		"is_updating": is_job_enqueued(install_job_id(row.name)),
	}


@frappe.whitelist(methods=["POST"])
@has_page_read(NO_BUILDER_ACCESS)
def uninstall_plugin(plugin: str) -> None:
	"""The site's copy and every user's stored state. `on_trash` takes both.

	The doctypes a plugin made hold the site's data, so they stay.
	"""
	assert_plugin_manager()
	frappe.delete_doc(INSTALLATION_DOCTYPE, get_installation(plugin))


def describe_installation(installation: str) -> dict:
	"""What a row in the panel shows, and all that the editor needs to load it.

	The icon is derived, so this reads the document.
	"""
	row = frappe.get_cached_doc(INSTALLATION_DOCTYPE, installation)
	return {
		"installation_id": row.name,
		"name": row.plugin,
		"label": row.label,
		"description": row.description,
		"icon": row.icon_data_uri,
		"version": row.version,
		"entry_url": row.entry_url,
		"source": row.source,
		"hub_url": row.hub_url,
		"enabled": bool(row.enabled),
		"install_state": row.install_state,
		"install_error": row.install_error,
		"is_development": row.version == DEV_PLUGIN_VERSION,
	}


def get_installation(plugin: str) -> str:
	"""The site's installation of this plugin, or a refusal naming it."""
	installation = find_installation(plugin)
	if not installation:
		frappe.throw(_('"{0}" is not installed on this site.').format(plugin), frappe.PermissionError)
	return installation
