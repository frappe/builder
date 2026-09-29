# Copyright (c) 2026, Frappe Technologies Pvt Ltd and contributors
# For license information, please see license.txt

"""Storage an extension owns outright.

No capability gates this. The extension's own drawer is not a write to the page,
so a read-only page does not close it.

One row per user and installation, holding the whole store as one JSON object.
The extension is installed for the whole site, but what it stores is one user's.
The store used to be `localStorage`, which is per browser, so two people sharing
a machine shared every extension's state. Here it follows the user between
machines.

A development extension still uses the browser. Its installation goes on every
`pagehide`, so a row here would not survive the reload an author needs.

These methods are the only way in. Each opens with `assert_extension_access`,
so the writes skip the doctype permission, which only a System Manager holds.
"""

import json

import frappe
from frappe import _

from builder.extensions.access import assert_extension_access
from builder.extensions.constants import MAX_STATE_BYTES

STATE_DOCTYPE = "Builder Extension State"


@frappe.whitelist()
def get_state(extension: str) -> dict:
	"""Everything this extension stored for this user."""
	installation = assert_extension_access(extension)
	return read_values(read_row(installation))


@frappe.whitelist(methods=["POST"])
def set_state(extension: str, state: dict) -> None:
	"""Only the keys that change, merged at the top level.

	`set` never removes what a call leaves unmentioned. An extension has up to
	five frames, and merging stops a panel saving its query from erasing what the
	entry stored.
	"""
	installation = assert_extension_access(extension)
	changes = read_changes(state)
	try:
		merge_changes(extension, installation, changes)
	except (frappe.QueryDeadlockError, frappe.UniqueValidationError):
		# Two frames made this user's first write at once, so neither had a row to
		# lock. The database ends one transaction: MariaDB with a deadlock, Postgres
		# with a duplicate. This request wrote nothing else, and the other frame's
		# row exists now, so merging again is safe.
		frappe.db.rollback()
		frappe.clear_messages()
		merge_changes(extension, installation, changes)


@frappe.whitelist(methods=["POST"])
def unset_state(extension: str, key: str) -> None:
	"""Drop one key.

	Quiet about a key that is not there. An extension clearing what it has already
	cleared is not an error.
	"""
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
	"""This user's row, or None before the first write.

	`for_update` locks the row until the request commits. Two frames that merge at
	the same time then run one after the other, and neither loses the other's keys.
	"""
	return frappe.db.get_value(
		STATE_DOCTYPE,
		{"installation": installation, "user": frappe.session.user},
		["name", "state"],
		as_dict=True,
		for_update=for_update,
	)


def read_values(row) -> dict:
	return frappe.parse_json(row.state) if row and row.state else {}


def read_changes(state) -> dict:
	changes = frappe.parse_json(state)
	if not isinstance(changes, dict):
		frappe.throw(_('"state" must be an object.'))
	return changes


def write_row(extension: str, installation: str, row, values: dict) -> None:
	"""The cap is on the whole store, key names included, not on one key."""
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
