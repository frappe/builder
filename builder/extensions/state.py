# Copyright (c) 2026, Frappe Technologies Pvt Ltd and contributors
# For license information, please see license.txt

"""Methods that keep the state of an extension for each user.
Each user and installation has one row with one JSON object. No permission is necessary.
Each method calls `assert_extension_access`. So the writes ignore the doctype permissions."""

import json

import frappe
from frappe import _

from builder.extensions.access import assert_extension_access
from builder.extensions.constants import MAX_STATE_BYTES

STATE_DOCTYPE = "Builder Extension State"


@frappe.whitelist()
def get_state(extension: str) -> dict:
	"""Returns all the state that this extension keeps for this user."""
	installation = assert_extension_access(extension)
	return read_values(read_row(installation))


@frappe.whitelist(methods=["POST"])
def set_state(extension: str, state: dict) -> None:
	"""Merges the changed keys into the state. It does not remove other keys.

	Many frames of an extension can write. The merge keeps the keys of each frame."""
	installation = assert_extension_access(extension)
	changes = get_changes(state)
	writes_before = frappe.db.transaction_writes
	try:
		merge_changes(extension, installation, changes)
	except (frappe.QueryDeadlockError, frappe.UniqueValidationError):
		# Two frames wrote the first row at the same time. The database stopped one write.
		# The row exists now, so a second merge is safe.
		# Do not retry if the rollback also removes an earlier write.
		if writes_before:
			raise
		frappe.db.rollback()
		frappe.clear_messages()
		merge_changes(extension, installation, changes)


@frappe.whitelist(methods=["POST"])
def unset_state(extension: str, key: str) -> None:
	"""Removes one key. A missing key is not an error."""
	installation = assert_extension_access(extension)
	row = read_row(installation, for_update=True)
	values = read_values(row)
	if key in values:
		del values[key]
		write_row(extension, installation, row, values)


def merge_changes(extension: str, installation: str, changes: dict) -> None:
	row = read_row(installation, for_update=True)
	values = read_values(row)
	values.update(changes)
	write_row(extension, installation, row, values)


def read_row(installation: str, for_update: bool = False):
	"""Returns the row of this user, or None before the first write.

	`for_update` locks the row. So two merges run one after the other."""
	return frappe.db.get_value(
		STATE_DOCTYPE,
		{"installation": installation, "user": frappe.session.user},
		["name", "state"],
		as_dict=True,
		for_update=for_update,
	)


def read_values(row) -> dict:
	return frappe.parse_json(row.state) if row and row.state else {}


def get_changes(state) -> dict:
	changes = frappe.parse_json(state)
	if not isinstance(changes, dict):
		frappe.throw(_('"state" must be an object.'))
	return changes


def write_row(extension: str, installation: str, row, values: dict) -> None:
	"""Writes the state. The size limit is for all the state, with the key names."""
	stored = json.dumps(values)
	if len(stored) > MAX_STATE_BYTES:
		frappe.throw(_('"{0}" state is larger than {1} kB.').format(extension, MAX_STATE_BYTES // 1000))

	if row:
		frappe.db.set_value(STATE_DOCTYPE, row.name, "state", stored)
		return

	frappe.get_doc(
		{
			"doctype": STATE_DOCTYPE,
			"installation": installation,
			"user": frappe.session.user,
			"state": stored,
		}
	).insert(ignore_permissions=True)
