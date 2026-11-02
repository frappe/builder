"""Compare content revisions under database ownership before applying an effect."""

import hashlib
import json

import frappe

PAGE_FIELDS = (
	"draft_blocks",
	"blocks",
	"page_data_script",
	"page_title",
	"route",
	"head_html",
	"body_html",
	"meta_description",
	"meta_image",
	"canonical_url",
	"language",
	"disable_indexing",
)


def digest(value) -> str:
	return hashlib.sha256(json.dumps(value, sort_keys=True, default=str).encode()).hexdigest()


def page_revision(page_id: str) -> str:
	values = frappe.db.get_value("Builder Page", page_id, PAGE_FIELDS, as_dict=True)
	links = frappe.get_all(
		"Builder Page Client Script", filters={"parent": page_id}, fields=["builder_script"], order_by="idx"
	)
	scripts = []
	for link in links:
		scripts.append(
			frappe.db.get_value(
				"Builder Client Script", link.builder_script, ["name", "script", "script_type"], as_dict=True
			)
		)
	return digest({"page": values, "scripts": scripts})


def require_revision(page_id: str, expected: str | None):
	frappe.db.get_value("Builder Page", page_id, "name", for_update=True)
	frappe.get_doc("Builder Page", page_id).check_permission("write")
	if expected and page_revision(page_id) != expected:
		raise ValueError(
			"The page changed after this work began. Your newer changes were kept. Reload and continue from the current page."
		)
