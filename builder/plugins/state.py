# Copyright (c) 2026, Frappe Technologies Pvt Ltd and contributors
# For license information, please see license.txt

"""Storage a plugin owns outright.

One row per user and installation, holding the whole store as one JSON object.
The plugin is installed for the whole site, but what it stores is one user's.
The store used to be `localStorage`, which is per browser, so two people sharing
a machine shared every plugin's state. Here it follows the user between
machines.

A development plugin still uses the browser, so a reload keeps nothing here
that an author would need to clear.

These methods are the only way in. Each opens with `assert_plugin_access`,
so the writes skip the doctype permission, which only a System Manager holds.
"""

import json

import frappe
from frappe import _

from builder.plugins.access import assert_plugin_access
from builder.plugins.constants import MAX_STATE_BYTES

STATE_DOCTYPE = "Builder Plugin State"


@frappe.whitelist()
def get_state(plugin: str) -> dict:
	"""Everything this plugin stored for this user."""
	installation = assert_plugin_access(plugin)
	return read_values(read_row(installation))


@frappe.whitelist(methods=["POST"])
def set_state(plugin: str, state: dict) -> None:
	"""Only the keys that change, merged at the top level.

	`set` never removes what a call leaves unmentioned. Two parts of a plugin
	can store at once, and merging stops one from erasing what the other stored.
	"""
	installation = assert_plugin_access(plugin)
	changes = get_changes(state)
	writes_before = frappe.db.transaction_writes
	try:
		merge_changes(plugin, installation, changes)
	except (frappe.QueryDeadlockError, frappe.UniqueValidationError):
		# Two calls made this user's first write at once, so neither had a row to
		# lock. The database ends one transaction: MariaDB with a deadlock, Postgres
		# with a duplicate. The other call's row exists now, so merging again is
		# safe, but only when the rollback takes no earlier write with it.
		if writes_before:
			raise
		frappe.db.rollback()
		frappe.clear_messages()
		merge_changes(plugin, installation, changes)


@frappe.whitelist(methods=["POST"])
def unset_state(plugin: str, key: str) -> None:
	"""Drop one key.

	Quiet about a key that is not there. A plugin clearing what it has already
	cleared is not an error.
	"""
	installation = assert_plugin_access(plugin)
	row = read_row(installation, for_update=True)
	values = read_values(row)
	if key in values:
		del values[key]
		write_row(plugin, installation, row, values)


def merge_changes(plugin: str, installation: str, changes: dict) -> None:
	row = read_row(installation, for_update=True)
	values = read_values(row)
	values.update(changes)
	write_row(plugin, installation, row, values)


def read_row(installation: str, for_update: bool = False):
	"""This user's row, or None before the first write.

	`for_update` locks the row until the request commits. Two calls that merge at
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


def get_changes(state) -> dict:
	changes = frappe.parse_json(state)
	if not isinstance(changes, dict):
		frappe.throw(_('"state" must be an object.'))
	return changes


def write_row(plugin: str, installation: str, row, values: dict) -> None:
	"""The cap is on the whole store, key names included, not on one key."""
	stored = json.dumps(values)
	if len(stored) > MAX_STATE_BYTES:
		frappe.throw(_('"{0}" state is larger than {1} kB.').format(plugin, MAX_STATE_BYTES // 1000))

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
