import re

import frappe

from builder.builder.doctype.builder_variable.builder_variable import get_css_variables
from builder.utils import camel_case_to_kebab_case

HASH_NAME_RE = re.compile(r"^[a-f0-9]{10}$")


def execute():
	"""Refactor Builder Variables to use stable random IDs as `name`.

	- Mint a new random-hash ID for each existing Builder Variable.
	- Rewrite var(--old-kebab-name) → var(--new-id) across all block JSON.
	- Rename the records.
	- Drop the shipped gray-* standards (the var(--id, #fallback) carries the colour).
	- Normalise type "Spacing" → "Dimension".
	"""
	if not frappe.db.has_column("Builder Variable", "variable_name"):
		return

	variables = frappe.get_all(
		"Builder Variable",
		fields=["name", "variable_name", "is_standard"],
	)
	if not variables:
		frappe.db.sql("UPDATE `tabBuilder Variable` SET type='Dimension' WHERE type='Spacing'")
		return

	if all(HASH_NAME_RE.match(v.name) for v in variables):
		# Already migrated.
		frappe.db.sql("UPDATE `tabBuilder Variable` SET type='Dimension' WHERE type='Spacing'")
		return

	rename_map = {}  # old doc name → new id
	css_rewrite_map = {}  # old kebab CSS name → new id
	gray_old_names = []

	for var in variables:
		if HASH_NAME_RE.match(var.name):
			continue
		new_id = frappe.generate_hash(length=10)
		rename_map[var.name] = new_id
		if var.variable_name:
			css_rewrite_map[camel_case_to_kebab_case(var.variable_name, True)] = new_id
		if "_" in var.name:
			css_rewrite_map[var.name.replace("_", "-")] = new_id

		looks_like_gray = (var.variable_name or "").lower().startswith("gray-") or var.name.startswith(
			"gray_"
		)
		if var.is_standard and looks_like_gray:
			gray_old_names.append(var.name)

	pages_updated = _rewrite_doctype_blocks("Builder Page", ["blocks", "draft_blocks"], css_rewrite_map)
	components_updated = _rewrite_doctype_blocks("Builder Component", ["block"], css_rewrite_map)

	renamed = 0
	for old_name, new_id in rename_map.items():
		try:
			frappe.rename_doc("Builder Variable", old_name, new_id, force=True, merge=False)
			renamed += 1
		except Exception as e:
			frappe.log_error(
				title="refactor_builder_variables: rename failed",
				message=f"{old_name} → {new_id}: {e!s}",
			)

	frappe.db.sql("UPDATE `tabBuilder Variable` SET type='Dimension' WHERE type='Spacing'")

	new_gray_ids = [rename_map[n] for n in gray_old_names if n in rename_map]
	if new_gray_ids:
		frappe.db.delete("Builder Variable", {"name": ("in", new_gray_ids)})

	get_css_variables.clear_cache()

	print(
		f"refactor_builder_variables: renamed={renamed} "
		f"pages_updated={pages_updated} components_updated={components_updated} "
		f"gray_deleted={len(new_gray_ids)}"
	)


def _rewrite_doctype_blocks(doctype, fields, css_rewrite_map):
	if not css_rewrite_map:
		return 0

	# Longer keys first so e.g. "brand-primary-light" matches before "brand-primary".
	parts = [re.escape(k) for k in sorted(css_rewrite_map, key=len, reverse=True)]
	pattern = re.compile(r"var\(--(" + "|".join(parts) + r")(?=[,\s)])")

	def _sub(match):
		return f"var(--{css_rewrite_map[match.group(1)]}"

	updated = 0
	records = frappe.get_all(doctype, fields=["name", *fields])
	for rec in records:
		dirty = {}
		for f in fields:
			raw = rec.get(f)
			if not raw or not isinstance(raw, str):
				continue
			new_raw = pattern.sub(_sub, raw)
			if new_raw != raw:
				dirty[f] = new_raw
		if dirty:
			for f, val in dirty.items():
				frappe.db.set_value(doctype, rec.name, f, val, update_modified=False)
			updated += 1
	return updated
