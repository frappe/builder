import frappe

from builder.utils import compact_json, normalize_legacy_raw_styles


def execute():
	migrate_builder_pages()
	migrate_block_doctype("Builder Component")
	migrate_block_doctype("Block Template")


def normalize_block_json(value):
	if not value or "rawStyles" not in value:
		return value
	return compact_json(normalize_legacy_raw_styles(frappe.parse_json(value)))


def migrate_builder_pages():
	for page in frappe.get_all("Builder Page", fields=["name", "blocks", "draft_blocks"]):
		updates = {}
		for field in ["blocks", "draft_blocks"]:
			normalized = normalize_block_json(page.get(field))
			if normalized != page.get(field):
				updates[field] = normalized
		if updates:
			frappe.db.set_value("Builder Page", page.name, updates, update_modified=False)


def migrate_block_doctype(doctype):
	for doc in frappe.get_all(doctype, fields=["name", "block"]):
		normalized = normalize_block_json(doc.block)
		if normalized != doc.block:
			frappe.db.set_value(doctype, doc.name, "block", normalized, update_modified=False)
