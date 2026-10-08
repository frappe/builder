# Copyright (c) 2026, Frappe Technologies Pvt Ltd and Contributors
# See license.txt

"""Shared setup for the extension tests: installations, files and users."""

import json
import pathlib
import shutil

import frappe
from frappe.utils import get_files_path

from builder.extensions.constants import ENTRY_FILE, EXTENSIONS_FOLDER, PERMISSIONS

INSTALLATION_DOCTYPE = "Builder Extension"
TEST_ROLE = "Extension Tester"


def make_installation(extension="acme/listed", permissions=None, granted=None, source=None, **values):
	"""Makes an installation of one extension. Adds files if `source` is given.

	By default, the manifest asks for all permissions and the site grants all of them."""
	requested = list(PERMISSIONS) if permissions is None else list(permissions)
	allowed = requested if granted is None else list(granted)
	fields = {
		"label": extension,
		"version": "1.0.0",
		"checksum": "sum123",
		"requested_permissions": json.dumps(requested),
		"granted_permissions": json.dumps(allowed),
		"enabled": 1,
		**values,
	}

	name = find_installation(extension)
	if name:
		installation = frappe.get_doc(INSTALLATION_DOCTYPE, name).update(fields).save()
	else:
		installation = frappe.get_doc(
			{"doctype": INSTALLATION_DOCTYPE, "extension": extension, **fields}
		).insert()

	if source is not None:
		write_source(installation, source)
	return installation


def find_installation(extension):
	return frappe.db.get_value(INSTALLATION_DOCTYPE, {"extension": extension}, "name")


def write_source(installation, source: str):
	"""Writes the entry file, and the icon if the record has one."""
	files = {ENTRY_FILE: source.encode()}
	if installation.icon:
		files[installation.icon] = b"<svg />"
	installation.write_extension_files(files)


def drop_installations(extension: str):
	"""Deletes the installation of one extension, so that a test starts clean."""
	for name in frappe.get_all(INSTALLATION_DOCTYPE, filters={"extension": extension}, pluck="name"):
		frappe.delete_doc(INSTALLATION_DOCTYPE, name, force=True)
	remove_orphan_installs()


def remove_orphan_installs():
	"""Deletes install folders that have no record.

	A test rolls back the database. So `on_trash` does not run and does not delete the files."""
	root = pathlib.Path(get_files_path(EXTENSIONS_FOLDER, is_private=True))
	if not root.is_dir():
		return

	installed = set(frappe.get_all(INSTALLATION_DOCTYPE, pluck="name"))
	for path in root.iterdir():
		if path.is_dir() and path.name not in installed:
			shutil.rmtree(path, ignore_errors=True)


def make_role(name: str) -> str:
	"""Makes a role for the tests. A new site has no spare role."""
	if not frappe.db.exists("Role", name):
		frappe.get_doc({"doctype": "Role", "role_name": name, "desk_access": 1}).insert(
			ignore_permissions=True
		)
	return name


def make_user(email="extension-tester@example.com", roles=("Website Manager",)):
	"""Makes a second Builder user. Website Manager gives read access to Builder Page.

	Give no roles to make a user that the checks refuse."""
	for role in roles:
		make_role(role)
	if not frappe.db.exists("User", email):
		frappe.get_doc(
			{
				"doctype": "User",
				"email": email,
				"first_name": "Extension",
				"send_welcome_email": 0,
				"roles": [{"role": role} for role in roles],
			}
		).insert(ignore_permissions=True)
	return email


def make_page_reader(test_case, role=TEST_ROLE, email="extension-reader@example.com"):
	"""Makes a user who reads Builder Pages only through `role`."""
	make_role(role)
	permission = frappe.get_doc(
		{"doctype": "Custom DocPerm", "parent": "Builder Page", "role": role, "permlevel": 0, "read": 1}
	).insert(ignore_permissions=True)
	# Cleanups run in reverse order. So the cache clears after the row is deleted.
	test_case.addCleanup(frappe.clear_cache, doctype="Builder Page")
	test_case.addCleanup(
		frappe.delete_doc, "Custom DocPerm", permission.name, force=True, ignore_permissions=True
	)
	frappe.clear_cache(doctype="Builder Page")
	return make_user(email, roles=(role,))
