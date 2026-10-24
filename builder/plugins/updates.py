# Copyright (c) 2026, Frappe Technologies Pvt Ltd and contributors
# For license information, please see license.txt

"""Updates of a Hub install: find a newer release, and replace the site's copy with it.

The installed release keeps running until the new package is downloaded and
checked. Only then do the record and the files change, in one job.
"""

import frappe
from frappe import _
from frappe.utils.background_jobs import is_job_enqueued

from builder.plugins.access import INSTALLATION_DOCTYPE, assert_plugin_manager
from builder.plugins.constants import DEV_PLUGIN_VERSION
from builder.plugins.hub import (
	INSTALL_JOB_TIMEOUT,
	apply_release,
	download_package,
	get_release,
	hub_plugin,
	latest_version,
)
from builder.plugins.installations import (
	NO_BUILDER_ACCESS,
	describe_installation,
	get_installation,
	install_job_id,
)
from builder.plugins.package import validate_package
from builder.utils import has_page_read


@frappe.whitelist()
@has_page_read(NO_BUILDER_ACCESS)
def get_update(plugin: str) -> dict | None:
	"""The newest release when it is not the installed one.

	The Hub lists releases newest first, so any other version is the update.
	"""
	assert_plugin_manager()
	row = get_updatable(plugin)
	version = latest_version(hub_plugin(row.hub_url, plugin), plugin)
	if version == row.version:
		return None
	return {"version": version}


@frappe.whitelist(methods=["POST"])
@has_page_read(NO_BUILDER_ACCESS)
def update_from_hub(plugin: str, version: str) -> dict:
	"""Start an update, and answer with the panel row, which still runs the installed release."""
	assert_plugin_manager()
	row = get_updatable(plugin)
	if is_job_enqueued(install_job_id(row.name)):
		frappe.throw(_('"{0}" is already updating.').format(plugin))

	frappe.enqueue(
		run_hub_update,
		queue="default",
		timeout=INSTALL_JOB_TIMEOUT,
		enqueue_after_commit=True,
		job_id=install_job_id(row.name),
		installation=row.name,
		name=plugin,
		version=version,
		hub_url=row.hub_url,
		user=frappe.session.user,
	)
	return describe_installation(row.name)


def run_hub_update(installation: str, name: str, version: str, hub_url: str, user: str) -> None:
	"""Download, check and apply one release. A failure keeps the installed release.

	Either way the row stays Ready, so the editor never stops running the plugin.
	The message carries the reason for a failure. The editor loads the new release
	on its next load.
	"""
	error = None
	try:
		release = get_release(hub_url, name, version)
		package = validate_package(download_package(release), name, release.version)
		doc = frappe.get_doc(INSTALLATION_DOCTYPE, installation)
		apply_release(doc, hub_url, release, package)
	except Exception as failure:
		frappe.db.rollback()
		frappe.log_error(title="Hub plugin update failed")
		error = str(failure) or _("The update failed.")

	# the worker commits when the job returns, and the message goes after that commit.
	# Its own event: an install listener reads a Ready state as a new install
	frappe.publish_realtime(
		"builder_plugin_update",
		{"plugin": name, "error": error},
		user=user,
		after_commit=True,
	)


def get_updatable(plugin: str):
	"""A ready Hub install. An app or dev install has no Hub release to update to."""
	row = frappe.get_doc(INSTALLATION_DOCTYPE, get_installation(plugin))
	if row.install_state != "Ready" or row.source != "Hub" or row.version == DEV_PLUGIN_VERSION:
		frappe.throw(_('"{0}" did not come from a Builder Hub, so it cannot update.').format(plugin))
	return row
