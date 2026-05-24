import re
import uuid

import frappe

from builder.builder.doctype.builder_variable.builder_variable import get_css_variables
from builder.utils import camel_case_to_kebab_case

UUID_RE = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")


def execute():
	"""Refactor Builder Variables to use UUIDs as `name`.

	Steps:
	1. Mint a UUID for each variable that isn't already on a UUID name.
	2. Rewrite `var(--old-name)` → `var(--<uuid>)` across page/component block JSON.
	3. Rename the records.
	4. Delete the shipped gray-* standards (block fallback hex keeps them rendering).
	5. Normalise legacy type "Spacing" → "Dimension".
	"""
	if not frappe.db.has_column("Builder Variable", "variable_name"):
		return

	variables = frappe.get_all(
		"Builder Variable",
		fields=["name", "variable_name", "is_standard"],
	)
	if not variables:
		normalise_type_spacing()
		return

	if all(UUID_RE.match(v.name) for v in variables):
		normalise_type_spacing()
		return

	rename_map = {}
	css_rewrite_map = {}
	gray_old_names = []

	for var in variables:
		if UUID_RE.match(var.name):
			continue
		new_id = str(uuid.uuid4())
		rename_map[var.name] = new_id

		# Old CSS form blocks reference (kebab-case of the user label).
		if var.variable_name:
			css_rewrite_map[camel_case_to_kebab_case(var.variable_name, True)] = new_id

		# Snake-cased doc names from before the refactor.
		if "_" in var.name:
			css_rewrite_map[var.name.replace("_", "-")] = new_id

		# 10-char hex hashes from the earlier (pre-UUID) refactor.
		if re.match(r"^[a-f0-9]{10}$", var.name):
			css_rewrite_map[var.name] = new_id

		is_gray = (var.variable_name or "").lower().startswith("gray-") or var.name.startswith("gray_")
		if var.is_standard and is_gray:
			gray_old_names.append(var.name)

	pages_updated = rewrite_doctype_blocks("Builder Page", ["blocks", "draft_blocks"], css_rewrite_map)
	components_updated = rewrite_doctype_blocks("Builder Component", ["block"], css_rewrite_map)

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

	normalise_type_spacing()

	new_gray_ids = [rename_map[n] for n in gray_old_names if n in rename_map]
	if new_gray_ids:
		frappe.db.delete("Builder Variable", {"name": ("in", new_gray_ids)})

	get_css_variables.clear_cache()

	print(
		f"refactor_builder_variables: renamed={renamed} "
		f"pages_updated={pages_updated} components_updated={components_updated} "
		f"gray_deleted={len(new_gray_ids)}"
	)


def normalise_type_spacing():
	frappe.db.sql("UPDATE `tabBuilder Variable` SET type='Dimension' WHERE type='Spacing'")


def rewrite_doctype_blocks(doctype, fields, css_rewrite_map):
	if not css_rewrite_map:
		return 0

	# Longer keys first so e.g. "brand-primary-light" matches before "brand-primary".
	parts = [re.escape(k) for k in sorted(css_rewrite_map, key=len, reverse=True)]
	pattern = re.compile(r"var\(--(" + "|".join(parts) + r")(?=[,\s)])")

	def sub(match):
		return f"var(--{css_rewrite_map[match.group(1)]}"

	updated = 0
	for rec in frappe.get_all(doctype, fields=["name", *fields]):
		dirty = {}
		for f in fields:
			raw = rec.get(f)
			if not raw or not isinstance(raw, str):
				continue
			new_raw = pattern.sub(sub, raw)
			if new_raw != raw:
				dirty[f] = new_raw
		if dirty:
			for f, val in dirty.items():
				frappe.db.set_value(doctype, rec.name, f, val, update_modified=False)
			updated += 1
	return updated
