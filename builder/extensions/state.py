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

These methods are the only way in. Each opens with `assert_extension_access`,
so the writes skip the doctype permission and the document, which only a System
Manager reaches directly.
"""

import json
import uuid

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
	"""Only the keys that change, merged at the top level.

	`set` never removes what a call leaves unmentioned. An extension has up to
	five frames, and merging stops a panel saving its query from erasing what the
	entry stored. One row per key, so two writing different keys never race.
	"""
	installation = assert_extension_access(extension)
	changes = read_changes(state)
	rows = read_rows(installation)
	assert_room_for(extension, rows, changes)
	write_rows(installation, changes)


@frappe.whitelist(methods=["POST"])
def unset_state(extension: str, key: str) -> None:
	"""Drop one key.

	Quiet about a key that is not there. An extension clearing what it has already
	cleared is not an error.
	"""
	installation = assert_extension_access(extension)
	row = read_rows(installation).get(key)
	if row:
		frappe.delete_doc(STATE_DOCTYPE, row.name, ignore_permissions=True)


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


def read_changes(state) -> dict:
	changes = frappe.parse_json(state)
	if not isinstance(changes, dict):
		frappe.throw(_('"state" must be an object.'))
	return changes


def assert_room_for(extension: str, rows: dict, changes: dict) -> None:
	"""The cap is on the whole store, not one key, and counts key names too.

	A per-key cap would let an extension write a thousand small keys. A cap on
	values alone would let it hide most of its data in long key names.
	"""
	kept = sum(len(key) + len(row.state_value or "") for key, row in rows.items() if key not in changes)
	incoming = sum(len(key) + len(json.dumps(value)) for key, value in changes.items())
	if kept + incoming <= MAX_STATE_BYTES:
		return

	frappe.throw(_('"{0}" state is larger than {1} kB.').format(extension, MAX_STATE_BYTES // 1000))


def write_rows(installation: str, changes: dict) -> None:
	"""Drop the changed keys, then insert them again, so the query count stays the same for any size.

	The bulk insert skips the document, so this sets what `insert()` would.
	"""
	if not changes:
		return

	user, now = frappe.session.user, frappe.utils.now_datetime()
	frappe.db.delete(
		STATE_DOCTYPE, {"installation": installation, "user": user, "state_key": ("in", list(changes))}
	)
	frappe.db.bulk_insert(
		STATE_DOCTYPE,
		["name", "creation", "modified", "owner", "modified_by", "installation", "user", "state_key", "state_value"],
		[
			(str(uuid.uuid4()), now, now, user, user, installation, user, key, json.dumps(value))
			for key, value in changes.items()
		],
	)
