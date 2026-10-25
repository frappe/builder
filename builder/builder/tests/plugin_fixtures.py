# Copyright (c) 2026, Frappe Technologies Pvt Ltd and Contributors
# See license.txt

"""What every plugin test needs: the site's installation, its files, and users.

The setup lives here rather than in each of the files that need it.
"""

import pathlib
import shutil

import frappe
from frappe.utils import get_files_path

from builder.plugins.constants import ENTRY_FILE, PLUGINS_FOLDER

INSTALLATION_DOCTYPE = "Builder Plugin"
TEST_ROLE = "Plugin Tester"


def make_installation(plugin="acme/listed", entry=None, **values):
	"""The site's installation of one plugin, with files when an entry is given."""
	fields = {
		"label": plugin,
		"source": "Hub",
		"version": "1.0.0",
		"checksum": "0123456789ab",
		"enabled": 1,
		**values,
	}

	name = find_installation(plugin)
	if name:
		installation = frappe.get_doc(INSTALLATION_DOCTYPE, name).update(fields).save()
	else:
		installation = frappe.get_doc({"doctype": INSTALLATION_DOCTYPE, "plugin": plugin, **fields}).insert()

	if entry is not None:
		write_entry(installation, entry)
	return installation


def find_installation(plugin):
	return frappe.db.get_value(INSTALLATION_DOCTYPE, {"plugin": plugin}, "name")


def write_entry(installation, entry: str):
	"""The one file a release holds, plus an icon when the record names one."""
	files = {ENTRY_FILE: entry.encode()}
	if installation.icon:
		files[installation.icon] = b"<svg />"
	installation.write_plugin_files(files)


def drop_installations(plugin: str):
	"""The site's installation of one plugin, for a test that starts clean."""
	for name in frappe.get_all(INSTALLATION_DOCTYPE, filters={"plugin": plugin}, pluck="name"):
		frappe.delete_doc(INSTALLATION_DOCTYPE, name, force=True)
	remove_orphan_installs()


def remove_orphan_installs():
	"""Install directories with no record left.

	A test rolls the database back, so the after-commit cleanup never runs and the
	files would stay on the site. Removing what no record names keeps a run from
	leaving anything behind.
	"""
	root = pathlib.Path(get_files_path(PLUGINS_FOLDER))
	if not root.is_dir():
		return

	installed = set(frappe.get_all(INSTALLATION_DOCTYPE, pluck="name"))
	for path in root.iterdir():
		if path.is_dir() and path.name not in installed:
			shutil.rmtree(path, ignore_errors=True)


def make_role(name: str) -> str:
	"""Tests own their role. A fresh site ships no spare one to borrow."""
	if not frappe.db.exists("Role", name):
		frappe.get_doc({"doctype": "Role", "role_name": name, "desk_access": 1}).insert(
			ignore_permissions=True
		)
	return name


def make_user(email="plugin-tester@example.com", roles=("Website Manager",)):
	"""A second Builder user. Website Manager edits Builder Pages and manages plugins."""
	for role in roles:
		make_role(role)
	if not frappe.db.exists("User", email):
		frappe.get_doc(
			{
				"doctype": "User",
				"email": email,
				"first_name": "Plugin",
				"send_welcome_email": 0,
				"roles": [{"role": role} for role in roles],
			}
		).insert(ignore_permissions=True)
	return email


def make_page_reader(test_case, role=TEST_ROLE, email="plugin-reader@example.com"):
	"""A user who reads Builder Pages through `role` alone: no System Manager, no Website Manager."""
	make_role(role)
	permission = frappe.get_doc(
		{"doctype": "Custom DocPerm", "parent": "Builder Page", "role": role, "permlevel": 0, "read": 1}
	).insert(ignore_permissions=True)
	# Cleanups run last in, first out, so the cache clears after the row goes.
	test_case.addCleanup(frappe.clear_cache, doctype="Builder Page")
	test_case.addCleanup(
		frappe.delete_doc, "Custom DocPerm", permission.name, force=True, ignore_permissions=True
	)
	frappe.clear_cache(doctype="Builder Page")
	return make_user(email, roles=(role,))
