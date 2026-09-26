# Copyright (c) 2026, Frappe Technologies Pvt Ltd and contributors
# For license information, please see license.txt

"""Storage an extension owns outright.

No capability gates this. The extension's own drawer is not a write to the page,
so a read-only page does not close it.

One row per user and key, on the site. The extension is installed for the whole
site, but what it stores is one user's. The store used to be `localStorage`, which
is per browser, so two people sharing a machine shared every extension's state.
Here it follows the user between machines.

A development extension still uses the browser. Its installation goes on every
`pagehide`, so a row here would not survive the reload an author needs.
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
	return {key: frappe.parse_json(row.state_value or "null") for key, row in read_rows(installation).items()}


@frappe.whitelist(methods=["POST"])
def set_state(extension: str, state: dict) -> None:
	"""A patch, merged at the top level.

	`set` never removes what a call leaves unmentioned. An extension has up to
	five frames, and merging stops a panel saving its query from erasing what the
	entry stored. One row per key, so two writing different keys never race.
	"""
	installation = assert_extension_access(extension)
	patch = read_patch(state)
	rows = read_rows(installation)
	assert_room_for(extension, rows, patch)

	for key, value in patch.items():
		write_row(installation, rows.get(key), key, value)


@frappe.whitelist(methods=["POST"])
def unset_state(extension: str, key: str) -> None:
	"""Drop one key.

	Quiet about a key that is not there. An extension clearing what it has already
	cleared is not an error.
	"""
	installation = assert_extension_access(extension)
	row = read_rows(installation).get(key)
	if row:
		frappe.delete_doc(STATE_DOCTYPE, row.name)


def read_rows(installation: str) -> dict:
	"""Every key this user stored, by key.

	One query, not one per key. A store is capped under a megabyte, so reading it
	whole costs less than the round trips.
	"""
	rows = frappe.get_all(
		STATE_DOCTYPE,
		filters={"installation": installation, "user": frappe.session.user},
		fields=["name", "state_key", "state_value"],
	)
	return {row.state_key: row for row in rows}


def read_patch(state) -> dict:
	patch = frappe.parse_json(state)
	if not isinstance(patch, dict):
		frappe.throw(_('"state" must be an object.'))
	return patch


def assert_room_for(extension: str, rows: dict, patch: dict) -> None:
	"""The cap is on the whole store, not one key, and counts key names too.

	A per-key cap would let an extension write a thousand small keys. A cap on
	values alone would let it hide most of its data in long key names.
	"""
	kept = sum(len(key) + len(row.state_value or "") for key, row in rows.items() if key not in patch)
	incoming = sum(len(key) + len(json.dumps(value)) for key, value in patch.items())
	if kept + incoming <= MAX_STATE_BYTES:
		return

	frappe.throw(_('"{0}" state is larger than {1} kB.').format(extension, MAX_STATE_BYTES // 1000))


def write_row(installation: str, row, key: str, value) -> None:
	stored = json.dumps(value)
	if row:
		frappe.db.set_value(STATE_DOCTYPE, row.name, "state_value", stored)
		return

	frappe.get_doc(
		{
			"doctype": STATE_DOCTYPE,
			"installation": installation,
			"user": frappe.session.user,
			"state_key": key,
			"state_value": stored,
		}
	).insert()
