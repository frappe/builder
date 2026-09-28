# Copyright (c) 2026, Frappe Technologies Pvt Ltd and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document

from builder.utils import compact_json


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


def take_snapshot(reference_doctype, reference_name, fields, label=None, snapshot_type=None, transform=None):
	"""Capture the current value of `fields` on a document as a snapshot.

	Stores `{fieldname: value}` as JSON in the snapshot's `data` field.
	Returns the new snapshot's name.

	`transform`, if given, is a callable that receives the captured
	`{fieldname: value}` dict and returns a (possibly rewritten) dict to store.
	It lets a consuming app post-process the captured values — e.g. pin
	dependency versions into a JSON field — without this generic layer needing
	any domain knowledge.
	"""
	doc = frappe.get_doc(reference_doctype, reference_name)
	data = {field: doc.get(field) for field in fields}
	if transform:
		data = transform(data)
	return create_snapshot(reference_doctype, reference_name, data, label, snapshot_type)


def create_snapshot(reference_doctype, reference_name, data: dict, label=None, snapshot_type=None):
	"""Store an already-captured `{fieldname: value}` dict as a snapshot.

	Use this when the data was captured earlier (e.g. before a long async operation)
	rather than read live from the document. `take_snapshot` is the read-live wrapper.
	"""
	snapshot = frappe.get_doc(
		{
			"doctype": "Builder Snapshot",
			"reference_doctype": reference_doctype,
			"reference_name": reference_name,
			"data": compact_json(data),
			"label": label,
			"snapshot_type": snapshot_type,
		}
	).insert(ignore_permissions=True)
	return snapshot.name


def get_snapshot_data(snapshot_name) -> dict:
	"""Return the stored `{fieldname: value}` dict for a snapshot."""
	snapshot = frappe.get_doc("Builder Snapshot", snapshot_name)
	return frappe.parse_json(snapshot.data)


def get_versioned_doc(snapshot_name):
	"""Return the referenced doc with this snapshot's captured fields overlaid (unsaved).

	Like `get_doc`, but as the document looked at `snapshot_name` for the captured fields —
	every other field comes from the current doc. If the referenced doc was deleted, the
	captured fields are overlaid onto a fresh doc (non-captured fields are doctype defaults)
	so the version stays resolvable.
	"""
	snapshot = frappe.get_doc("Builder Snapshot", snapshot_name)
	try:
		doc = frappe.get_doc(snapshot.reference_doctype, snapshot.reference_name)
	except frappe.DoesNotExistError:
		doc = frappe.new_doc(snapshot.reference_doctype)
		doc.name = snapshot.reference_name
	for field, value in frappe.parse_json(snapshot.data).items():
		doc.set(field, value)
	return doc


def restore_snapshot(snapshot_name, save=True):
	"""Generic write-back: apply a snapshot's stored fields onto its document.

	Apps that need custom restore semantics (e.g. routing the value into a draft
	field for review) should use `get_versioned_doc` / `get_snapshot_data` and apply
	it themselves rather than calling this.
	"""
	doc = get_versioned_doc(snapshot_name)
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
