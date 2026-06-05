import re
import uuid

import frappe

from builder.builder.doctype.builder_variable.builder_variable import get_css_variables
from builder.utils import camel_case_to_kebab_case

UUID_RE = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")


def execute():
	"""Migrate Builder Variables to UUID names.

	1. Assign a UUID to every variable that doesn't already have one.
	2. Rewrite `var(--old-name)` → `var(--<uuid>)` in page/component blocks.
	3. Normalise legacy type "Spacing" → "Dimension".
	"""
	if not frappe.db.has_column("Builder Variable", "variable_name"):
		return

	variables = frappe.get_all("Builder Variable", fields=["name", "variable_name"])
	non_uuid = [v for v in variables if not UUID_RE.match(v.name)]

	if non_uuid:
		rename_map, css_rewrite_map = build_maps(non_uuid)
		pages_updated = rewrite_doctype_blocks("Builder Page", ["blocks", "draft_blocks"], css_rewrite_map)
		components_updated = rewrite_doctype_blocks("Builder Component", ["block"], css_rewrite_map)
		renamed = rename_variables(rename_map)
		print(
			f"refactor_builder_variables: renamed={renamed} "
			f"pages_updated={pages_updated} components_updated={components_updated}"
		)

	normalise_type_spacing()
	get_css_variables.clear_cache()


def build_maps(variables):
	"""Return (rename_map, css_rewrite_map) for the given non-UUID variables."""
	rename_map = {}
	css_rewrite_map = {}

	for var in variables:
		new_id = str(uuid.uuid4())
		rename_map[var.name] = new_id

		# kebab-case of the display label
		if var.variable_name:
			css_rewrite_map[camel_case_to_kebab_case(var.variable_name, True)] = new_id

		# snake_case doc names used before this refactor
		if "_" in var.name:
			css_rewrite_map[var.name.replace("_", "-")] = new_id

		# 10-char hex hashes from an earlier refactor
		if re.match(r"^[a-f0-9]{10}$", var.name):
			css_rewrite_map[var.name] = new_id

	return rename_map, css_rewrite_map


def rename_variables(rename_map):
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
	return renamed


def normalise_type_spacing():
	frappe.db.sql("UPDATE `tabBuilder Variable` SET type='Dimension' WHERE type='Spacing'")


def rewrite_doctype_blocks(doctype, fields, css_rewrite_map):
	if not css_rewrite_map:
		return 0

	# Longer keys first so "brand-primary-light" matches before "brand-primary"
	parts = [re.escape(k) for k in sorted(css_rewrite_map, key=len, reverse=True)]
	pattern = re.compile(r"var\(--(" + "|".join(parts) + r")(?=[,\s)])")

	def sub(match):
		return f"var(--{css_rewrite_map[match.group(1)]}"

	updated = 0
	for rec in frappe.get_all(doctype, fields=["name", *fields]):
		dirty = {f: pattern.sub(sub, rec[f]) for f in fields if rec.get(f) and isinstance(rec[f], str)}
		dirty = {f: v for f, v in dirty.items() if v != rec[f]}
		if dirty:
			for f, val in dirty.items():
				frappe.db.set_value(doctype, rec.name, f, val, update_modified=False)
			updated += 1
	return updated
