# Copyright (c) 2026, Frappe Technologies Pvt Ltd and Contributors
# See license.txt

"""What every extension test needs: one user's installation, and its files.

An extension used to be one site record, so a test could make one in three lines.
It is now a record per user with its own copy of the entry, so the setup lives
here rather than in each of the seven files that need it.
"""

import json
import pathlib
import shutil

import frappe
from frappe.utils import get_files_path

from builder.extensions.constants import CAPABILITIES, ENTRY_FILE, EXTENSIONS_FOLDER

INSTALLATION_DOCTYPE = "Builder User Extension"


def make_installation(
	extension="acme/listed", user=None, capabilities=None, granted=None, source=None, **values
):
	"""This user's installation of one extension, with files when a source is given.

	`capabilities` is what the manifest asked for, and every one of them is granted
	unless `granted` narrows it. Both default to every capability, so a test that is
	not about the gate lists none.
	"""
	user = user or frappe.session.user
	requested = list(CAPABILITIES) if capabilities is None else list(capabilities)
	allowed = requested if granted is None else list(granted)
	fields = {
		"label": extension,
		"version": "1.0.0",
		"checksum": "sum123",
		"requested_capabilities": json.dumps(requested),
		"granted_capabilities": json.dumps(allowed),
		"enabled": 1,
		**values,
	}

	name = find_installation(extension, user)
	if name:
		installation = frappe.get_doc(INSTALLATION_DOCTYPE, name).update(fields).save()
	else:
		installation = frappe.get_doc(
			{"doctype": INSTALLATION_DOCTYPE, "user": user, "extension": extension, **fields}
		).insert()

	if source is not None:
		write_source(installation, source)
	return installation


def find_installation(extension, user=None):
	"""One user's installation of one extension."""
	return frappe.db.get_value(
		INSTALLATION_DOCTYPE,
		{"user": user or frappe.session.user, "extension": extension},
		"name",
	)


def write_source(installation, source: str):
	"""The one file an install holds, plus an icon when the record names one."""
	files = {ENTRY_FILE: source.encode()}
	if installation.icon:
		files[installation.icon] = b"<svg />"
	installation.write_extension_files(files)


def drop_installations(extension: str):
	"""Every user's installation of one extension, for a test that starts clean."""
	for name in frappe.get_all(INSTALLATION_DOCTYPE, filters={"extension": extension}, pluck="name"):
		frappe.delete_doc(INSTALLATION_DOCTYPE, name, force=True)
	remove_orphan_installs()


def remove_orphan_installs():
	"""Install directories with no record left.

	A test rolls the database back, so `on_trash` never runs and the files would
	stay on the site. Removing what no record names keeps a run from leaving
	anything behind.
	"""
	root = pathlib.Path(get_files_path(EXTENSIONS_FOLDER, is_private=True))
	if not root.is_dir():
		return

	installed = set(frappe.get_all(INSTALLATION_DOCTYPE, pluck="name"))
	for path in root.iterdir():
		if path.is_dir() and path.name not in installed:
			shutil.rmtree(path, ignore_errors=True)


def make_user(email="extension-tester@example.com", roles=("Website Manager",)):
	"""A second Builder user, to show that an installation is one person's.

	Website Manager gives read on Builder Page, the check the gate makes before it
	looks for an installation. Pass no roles for a user the gate turns away.
	"""
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
