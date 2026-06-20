"""Pre-turn page snapshots for reverting an AI turn.

Reuses Builder's generic Builder Snapshot system, tagged snapshot_type="AI". State is
captured synchronously at request time (reliably pre-turn, before the worker or any
streaming touches the canvas); the snapshot doc is created ONLY when a turn actually
mutates the page — so no-op, clarify, and plan turns leave nothing behind.
"""

import frappe

from builder.builder.component_versions import pin_components_in_page_data
from builder.builder.doctype.builder_snapshot.builder_snapshot import create_snapshot, prune_snapshots

logger = frappe.logger("builder.ai.snapshots")

# How many auto "AI" snapshots to keep per page. Independent of Publish/Manual snapshots.
KEEP_AI_SNAPSHOTS = 10


def capture_page_state(page_id: str | None) -> dict | None:
	"""Read the page's current blocks + data script + client scripts into a plain dict
	(no doc created), so ONE revert restores everything the turn touched.

	Returns None when there is nothing worth reverting to (missing/empty page)."""
	if not page_id or not frappe.db.exists("Builder Page", page_id):
		return None
	doc = frappe.get_doc("Builder Page", page_id)
	field = "draft_blocks" if doc.get("draft_blocks") else "blocks"
	if not doc.get(field):
		return None
	state = {field: doc.get(field), "page_data_script": doc.get("page_data_script")}
	# Capture client scripts so revert handles them too (no separate "undo script"):
	# the page's links (always, even empty — so scripts the turn CREATES get unlinked on
	# revert) plus each linked script's content (so scripts the turn EDITS are reverted).
	links = doc.get("client_scripts") or []
	state["client_scripts"] = [{"builder_script": row.builder_script} for row in links if row.builder_script]
	contents: dict[str, dict] = {}
	for row in links:
		if not row.builder_script:
			continue
		script = frappe.db.get_value(
			"Builder Client Script", row.builder_script, ["script", "script_type"], as_dict=True
		)
		if script:
			contents[row.builder_script] = {"script": script.script, "script_type": script.script_type}
	state["_ai_scripts"] = contents
	return state


def save_revert_snapshot(page_id: str | None, state: dict | None) -> str | None:
	"""Persist a captured pre-turn `state` as an "AI" snapshot and prune old ones.

	Returns the snapshot name, or None if there was nothing to save. A snapshot failure
	never blocks the turn — the change is already applied; revert just won't be offered."""
	if not page_id or not state:
		return None
	try:
		name = create_snapshot(
			"Builder Page", page_id, pin_components_in_page_data(state), "Before AI edit", "AI"
		)
		prune_snapshots("Builder Page", page_id, keep=KEEP_AI_SNAPSHOTS, snapshot_type="AI")
		return name
	except Exception:
		logger.warning("Failed to save AI revert snapshot", exc_info=True)
		return None
