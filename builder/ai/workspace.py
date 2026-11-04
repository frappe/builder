"""Saved design decisions and upload preparation for Bob."""

import json

import frappe

from builder.ai.brief import DesignBrief
from builder.ai.revisions import digest

MAX_RECORDS = 30


def decision_records(records, source_message=None, user_edit=False):
	if not isinstance(records, list) or len(records) > MAX_RECORDS:
		raise ValueError("Keep at most 30 active facts or decisions")
	clean, seen = [], set()
	for record in records:
		if not isinstance(record, dict) or not isinstance(record.get("value"), str):
			raise ValueError("Each decision needs a text value")
		identity = str(record.get("id") or digest(record)[:12])[:80]
		if identity in seen or len(record["value"]) > 1000:
			raise ValueError("Decision IDs must be unique and values under 1000 characters")
		seen.add(identity)
		status = record.get("status", "proposed")
		if status not in ("proposed", "accepted", "rejected"):
			raise ValueError("Invalid decision status")
		clean.append(
			{
				"id": identity,
				"label": str(record.get("label") or "")[:100],
				"value": record["value"],
				"status": status if user_edit else "proposed",
				"source_message": source_message,
				"source": "user" if user_edit else "assistant",
			}
		)
	return clean


def update_decisions(brief, patch, source_message=None, user_edit=False):
	for field in ("facts", "decisions"):
		if field not in patch:
			continue
		records = decision_records(patch[field], source_message, user_edit)
		previous = {record["id"]: record for record in brief.get(field, [])}
		for record in records:
			old = previous.get(record["id"])
			if old and old.get("source") == "user" and not user_edit:
				if record["value"] != old["value"]:
					raise ValueError("A user-approved decision must be changed by the user in the brief")
				continue
			previous[record["id"]] = record
		if len(previous) > MAX_RECORDS:
			raise ValueError("Archive an older decision before adding more")
		brief[field] = list(previous.values())


@frappe.whitelist()
def get_pending_media_requests(page_id: str):
	frappe.get_doc("Builder Page", page_id).check_permission("read")
	rows = frappe.get_all(
		"Builder AI Artifact",
		filters={"page": page_id, "kind": "media_request", "status": "pending"},
		fields=["name", "label", "payload_json"],
		limit=50,
	)
	requests = []
	for row in rows:
		value = json.loads(row.payload_json)
		requests.append(
			{
				"id": row.name,
				"label": row.label,
				"reserved_usd": value.get("reserved_usd"),
			}
		)
	return {
		"requests": requests,
		"can_reconcile": "System Manager" in frappe.get_roles(),
	}


@frappe.whitelist(methods=["POST"])
def classify_asset(page_id: str, asset_id: str, role: str):
	frappe.get_doc("Builder Page", page_id).check_permission("write")
	frappe.db.get_value("Builder Page", page_id, "name", for_update=True)
	if role not in ("undecided", "reference", "content", "logo", "product", "team"):
		raise ValueError("Choose how this image should be used")
	brief = DesignBrief(page_id)
	state = brief.read()
	asset = next((item for item in state.get("assets", []) if brief.asset_key(item) == asset_id), None)
	if not asset:
		raise ValueError("Choose an image from this page's library")
	asset["role"] = role
	state["revision"] = int(state.get("revision", 0)) + 1
	brief.save(state)
	return state


@frappe.whitelist(methods=["POST"])
def prepare_upload(page_id: str, asset_id: str):
	from frappe.utils.file_manager import save_file

	from builder.ai.media import raster, selected_asset

	frappe.get_doc("Builder Page", page_id).check_permission("write")
	frappe.db.get_value("Builder Page", page_id, "name", for_update=True)
	asset = selected_asset(page_id, asset_id)
	if asset.get("provider") != "Upload" or asset.get("role") not in ("content", "logo", "product", "team"):
		raise ValueError(
			"Mark the upload as content, logo, product or team before making it available on the published page"
		)
	file = frappe.get_doc("File", {"file_url": asset["original_url"]})
	file.check_permission("read")
	if file.owner != frappe.session.user and "System Manager" not in frappe.get_roles():
		raise frappe.PermissionError("Only the uploader can make this private image public")
	content = file.get_content()
	raster(content)
	public = save_file(file.file_name, content, "Builder Page", page_id, is_private=0)
	brief = DesignBrief(page_id)
	state = brief.read()
	for item in state.get("assets", []):
		if item.get("id") == asset_id:
			item.update(url=public.file_url, thumb=public.file_url, preview_only=False)
	brief.save(state)
	return state
