"""User-editable design state, with explicit decisions instead of transcript guesses."""

import json

import frappe

from builder.ai.artifacts import Artifact
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
def get_design_workspace(page_id: str):
	from builder.ai.design import brief_revision, direction_option

	frappe.get_doc("Builder Page", page_id).check_permission("read")
	brief = DesignBrief(page_id).read()
	variants = []
	for row in Artifact.list(page_id, "design"):
		value = json.loads(row.payload_json)
		variants.append(
			{
				**direction_option(row.name, value),
				"status": row.status,
				"stale": value["brief_revision"] != brief_revision(brief),
			}
		)
	from builder.ai.projects import for_page
	from builder.ai.revisions import page_revision

	revision = page_revision(page_id)
	verification = []
	for row in Artifact.list(page_id, "verification", limit=5):
		value = json.loads(row.payload_json)
		verification.append(
			{"id": row.name, "created": row.modified, "stale": value.get("revision") != revision, **value}
		)
	media = []
	for row in Artifact.list(page_id, "media_request", limit=50):
		value = json.loads(row.payload_json)
		media.append(
			{
				"id": row.name,
				"status": row.status,
				"label": row.label,
				"reserved_usd": value.get("reserved_usd"),
				"actual_cost_usd": value.get("actual_cost_usd"),
				"reconciliation": value.get("reconciliation"),
			}
		)
	return {
		"brief": brief,
		"variants": variants,
		"project": for_page(page_id),
		"verification": verification,
		"media": media,
		"media_budget_usd": frappe.conf.get("bob_media_budget_usd") or 0,
		"can_reconcile_media": "System Manager" in frappe.get_roles(),
	}


@frappe.whitelist(methods=["POST"])
def save_design_brief(page_id: str, patch: dict, expected_revision: int = 0):
	frappe.get_doc("Builder Page", page_id).check_permission("write")
	frappe.db.get_value("Builder Page", page_id, "name", for_update=True)
	brief = DesignBrief(page_id)
	if int(brief.read().get("revision", 0)) != int(expected_revision):
		raise ValueError("The brief changed in another tab. Reload it before saving your changes.")
	return brief.update(patch, user_edit=True)


@frappe.whitelist(methods=["POST"])
def select_asset(page_id: str, asset_id: str, selected: bool):
	frappe.get_doc("Builder Page", page_id).check_permission("write")
	frappe.db.get_value("Builder Page", page_id, "name", for_update=True)
	brief = DesignBrief(page_id)
	state = brief.read()
	asset = next((item for item in state.get("assets", []) if brief.asset_key(item) == asset_id), None)
	if not asset:
		raise ValueError("The asset is no longer in this project's library")
	asset["selected"] = bool(frappe.utils.cint(selected))
	state["revision"] = int(state.get("revision", 0)) + 1
	brief.save(state)
	return state


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
