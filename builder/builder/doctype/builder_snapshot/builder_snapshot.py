# Copyright (c) 2026, Frappe Technologies Pvt Ltd and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class BuilderSnapshot(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		data: DF.Code
		label: DF.Data | None
		reference_doctype: DF.Link
		reference_name: DF.Data
		snapshot_type: DF.Data | None
	# end: auto-generated types
	pass


# ---------------------------------------------------------------------------
# Generic, framework-promotable snapshot utilities.
#
# These helpers are intentionally domain-agnostic: they take a doctype/name and
# a list of fieldnames, and never reference Builder-specific fields. Apps store
# a point-in-time copy of selected fields and can restore them later. This layer
# is a candidate for promotion into Frappe core.
# ---------------------------------------------------------------------------


def take_snapshot(reference_doctype, reference_name, fields, label=None, snapshot_type=None):
	"""Capture the current value of `fields` on a document as a snapshot.

	Stores `{fieldname: value}` as JSON in the snapshot's `data` field.
	Returns the new snapshot's name.
	"""
	doc = frappe.get_doc(reference_doctype, reference_name)
	data = {field: doc.get(field) for field in fields}
	snapshot = frappe.get_doc(
		{
			"doctype": "Builder Snapshot",
			"reference_doctype": reference_doctype,
			"reference_name": reference_name,
			"data": frappe.as_json(data),
			"label": label,
			"snapshot_type": snapshot_type,
		}
	).insert(ignore_permissions=True)
	return snapshot.name


def get_snapshot_data(snapshot_name) -> dict:
	"""Return the stored `{fieldname: value}` dict for a snapshot."""
	snapshot = frappe.get_doc("Builder Snapshot", snapshot_name)
	return frappe.parse_json(snapshot.data)


def restore_snapshot(snapshot_name, save=True):
	"""Generic write-back: apply a snapshot's stored fields onto its document as-is.

	Apps that need custom restore semantics (e.g. routing the value into a draft
	field for review) should use `get_snapshot_data` and apply it themselves
	rather than calling this.
	"""
	snapshot = frappe.get_doc("Builder Snapshot", snapshot_name)
	doc = frappe.get_doc(snapshot.reference_doctype, snapshot.reference_name)
	for field, value in frappe.parse_json(snapshot.data).items():
		doc.set(field, value)
	if save:
		doc.save()
	return doc


def prune_snapshots(reference_doctype, reference_name, keep, snapshot_type=None):
	"""Delete the oldest snapshots beyond `keep` for a document.

	Optionally restrict pruning to a single `snapshot_type` so that other types
	(e.g. manual checkpoints) are never auto-deleted.
	"""
	filters = {"reference_doctype": reference_doctype, "reference_name": reference_name}
	if snapshot_type:
		filters["snapshot_type"] = snapshot_type
	names = frappe.get_all(
		"Builder Snapshot",
		filters=filters,
		order_by="creation desc",
		pluck="name",
	)
	for name in names[keep:]:
		frappe.delete_doc("Builder Snapshot", name, ignore_permissions=True)
