"""Draft page edits for external agents using Frappe's document and MCP APIs."""

from urllib.parse import urlencode

import frappe
from frappe.utils import get_datetime, get_url
from werkzeug.wrappers import Response

from builder.builder.doctype.builder_snapshot.builder_snapshot import take_snapshot
from builder.utils import compact_json

DRAFT_ROLE = "Builder Draft Editor"


@frappe.whitelist(methods=["POST"])
def create_page(page_title: str, blocks: list[dict], source_page: str | None = None) -> dict:
	"""Create an unpublished page. Optionally reuse a readable page's data and client scripts."""
	frappe.only_for(DRAFT_ROLE)
	validate_blocks(blocks)
	doc = frappe.new_doc("Builder Page")
	doc.page_title = page_title
	doc.draft_blocks = compact_json(blocks)
	if source_page:
		source = frappe.get_doc("Builder Page", source_page)
		source.check_permission("read")
		doc.page_data_script = source.page_data_script
		doc.set("client_scripts", [{"builder_script": row.builder_script} for row in source.client_scripts])
	doc.insert(ignore_permissions=True)
	return draft_result(doc)


@frappe.whitelist(methods=["POST"])
def save_page(page: str, blocks: list[dict], modified: str) -> dict:
	"""Snapshot and replace only draft_blocks. Pass the modified value from the last read."""
	frappe.only_for(DRAFT_ROLE)
	validate_blocks(blocks)
	doc = frappe.get_doc("Builder Page", page, for_update=True)
	doc.check_permission("read")
	if doc.is_standard or doc.is_template:
		frappe.throw(frappe._("Create a regular page before editing a standard or template page."))
	if get_datetime(modified) != get_datetime(doc.modified):
		frappe.throw(
			frappe._("This page has changed. Read it again before editing."), frappe.TimestampMismatchError
		)
	snapshot = take_snapshot(
		"Builder Page",
		page,
		fields=["blocks", "draft_blocks"],
		snapshot_type="Manual",
		label=frappe._("Before agent edit"),
	)
	doc.draft_blocks = compact_json(blocks)
	doc.save(ignore_permissions=True)
	return draft_result(doc, snapshot)


@frappe.whitelist(methods=["GET"])
def preview(page: str) -> Response:
	"""Render a readable page's draft without replacing its published preview image."""
	doc = frappe.get_doc("Builder Page", page)
	doc.check_permission("read")
	return Response(
		doc.get_preview_html(), mimetype="text/html", headers={"Cache-Control": "private, no-store"}
	)


def draft_result(doc, snapshot: str | None = None) -> dict:
	return {
		"page": doc.name,
		"modified": str(doc.modified),
		"snapshot": snapshot,
		"preview_url": get_url("/api/method/builder.draft_api.preview?" + urlencode({"page": doc.name})),
	}


def validate_blocks(blocks: list[dict]) -> None:
	if not isinstance(blocks, list) or not blocks:
		frappe.throw(frappe._("Provide a non-empty list of page blocks."))
	for block in blocks:
		if not isinstance(block, dict):
			frappe.throw(frappe._("Each page block must be an object."))
		children = block.get("children", [])
		if not isinstance(children, list):
			frappe.throw(frappe._("Block children must be a list."))
		if children:
			validate_blocks(children)
