"""Transactional event journal. Socket delivery is a replayable notification."""

import json

import frappe

from builder.ai.runs import AIRun

DOCTYPE = "Builder AI Event"


def append(run_id, kind, payload):
	sequence = (frappe.db.get_value(AIRun.DOCTYPE, run_id, "event_seq", for_update=True) or 0) + 1
	frappe.db.set_value(AIRun.DOCTYPE, run_id, "event_seq", sequence, update_modified=False)
	payload = {**payload, "seq": sequence, "journal": True}
	frappe.get_doc(
		{
			"doctype": DOCTYPE,
			"run": run_id,
			"sequence": sequence,
			"event_type": kind,
			"payload_json": json.dumps(payload, separators=(",", ":")),
		}
	).insert(ignore_permissions=True, set_name=f"{run_id}-{sequence}")
	return payload


@frappe.whitelist()
def replay(run_id: str, after_seq: int = 0, limit: int = 200):
	from builder.ai.session import AISession

	run = frappe.get_doc(AIRun.DOCTYPE, run_id)
	AISession.get(run.session, page_id=run.page)
	frappe.get_doc("Builder Page", run.page).check_permission("read")
	limit = max(1, min(int(limit), 500))
	rows = frappe.get_all(
		DOCTYPE,
		filters={"run": run_id, "sequence": [">", max(0, int(after_seq))]},
		fields=["sequence", "event_type", "payload_json"],
		order_by="sequence asc",
		limit=limit,
	)
	return {
		"events": [{"type": row.event_type, "data": json.loads(row.payload_json)} for row in rows],
		"cursor": rows[-1].sequence if rows else int(after_seq),
		"has_more": len(rows) == limit,
		"status": run.status,
		"expired": not rows and (run.event_seq or 0) > int(after_seq),
	}


def prune():
	# Transcripts, receipts and final run metadata outlive the transient stream journal.
	cutoff = frappe.utils.add_days(frappe.utils.now_datetime(), -7)
	for run in frappe.get_all(
		AIRun.DOCTYPE, filters={"finished_on": ["<", cutoff]}, pluck="name", limit=1000
	):
		frappe.db.delete(DOCTYPE, {"run": run})
