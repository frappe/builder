"""What changed on a page, in lines Bob can act on.

Bob works from the page as it last saw it. When the user edits between turns, or
while a turn is running, these lines tell Bob what they changed so it builds on
those edits instead of undoing them."""

import re

import frappe

COMPARED_KEYS = (
	"blockName",
	"element",
	"innerHTML",
	"baseStyles",
	"mobileStyles",
	"tabletStyles",
	"attributes",
	"customAttributes",
	"classes",
	"props",
	"dynamicValues",
	"visibilityCondition",
	"clientScript",
)
MAX_LINES = 25


def block_label(block: dict) -> str:
	return block.get("blockName") or f"<{block.get('element') or 'div'}>"


def describe_block_changes(before: dict | None, after: dict | None) -> list[str]:
	old, new = index_blocks(before), index_blocks(after)
	lines = []
	for ref, (block, parent_ref) in new.items():
		if ref in old:
			if changes := block_changes(old[ref], (block, parent_ref), new):
				lines.append(f"{block_label(block)} (ref {ref}): {', '.join(changes)}")
		elif parent_ref in old:
			lines.append(f"added {block_label(block)} (ref {ref}) inside {block_label(new[parent_ref][0])}")
	for ref, (block, parent_ref) in old.items():
		if ref not in new and parent_ref in new:
			lines.append(f"removed {block_label(block)} (ref {ref})")
	if len(lines) > MAX_LINES:
		lines = [*lines[:MAX_LINES], f"and {len(lines) - MAX_LINES} more"]
	return lines


def block_changes(
	previous: tuple[dict, str | None], current: tuple[dict, str | None], index: dict
) -> list[str]:
	(old_block, old_parent), (block, parent_ref) = previous, current
	changes = [key for key in COMPARED_KEYS if (old_block.get(key) or None) != (block.get(key) or None)]
	if "innerHTML" in changes:
		changes[changes.index("innerHTML")] = (
			f"text {plain_text(old_block.get('innerHTML'))!r} -> {plain_text(block.get('innerHTML'))!r}"
		)
	if old_parent != parent_ref and parent_ref in index:
		changes.append(f"moved inside {block_label(index[parent_ref][0])}")
	return changes


def index_blocks(root: dict | None) -> dict[str, tuple[dict, str | None]]:
	index = {}
	stack = [(root, None)] if isinstance(root, dict) else []
	while stack:
		block, parent_ref = stack.pop()
		index[block.get("blockId")] = (block, parent_ref)
		stack.extend(
			(child, block.get("blockId")) for child in block.get("children") or [] if isinstance(child, dict)
		)
	return index


def plain_text(html) -> str:
	return re.sub(r"<[^>]+>", " ", str(html or "")).strip()[:60]


def page_state(page_id: str, root: dict | None, doc_keys) -> dict:
	"""The open page as a turn left it, plus when each other document the chat changed was last modified."""
	return {
		"page": page_id,
		"blocks": root,
		"fields": page_fields(page_id),
		"scripts": attached_scripts(page_id),
		"docs": {
			f"{doctype}::{name}": modified
			for doctype, name in doc_keys
			if (doctype, name) != ("Builder Page", page_id) and (modified := last_modified(doctype, name))
		},
	}


def describe_user_changes(state: dict | None, page_id: str | None, root: dict | None) -> list[str]:
	if not state or not page_id or state.get("page") != page_id:
		return []
	lines = describe_block_changes(state.get("blocks"), root)
	fields = page_fields(page_id)
	lines += [
		f"page field {field} changed"
		for field, value in (state.get("fields") or {}).items()
		if fields.get(field) != value
	]
	if attached_scripts(page_id) != state.get("scripts"):
		lines.append("the scripts attached to the page changed")
	for key, modified in (state.get("docs") or {}).items():
		doctype, name = key.split("::", 1)
		now = last_modified(doctype, name)
		if now is None:
			lines.append(f"{doctype} '{name}' was deleted")
		elif now != modified:
			lines.append(f"{doctype} '{name}' was edited")
	return lines


def page_fields(page_id: str) -> dict:
	from builder.ai.agent.tools.settings import PAGE_SETTING_FIELDS

	fields = sorted(PAGE_SETTING_FIELDS | {"page_data_script"})
	values = frappe.db.get_value("Builder Page", page_id, fields, as_dict=True) or {}
	return {field: values.get(field) for field in fields}


def attached_scripts(page_id: str) -> list[str]:
	return frappe.get_all(
		"Builder Page Client Script",
		filters={"parent": page_id, "parenttype": "Builder Page"},
		pluck="builder_script",
		order_by="idx asc",
	)


def last_modified(doctype: str, name: str) -> str | None:
	if not frappe.db.exists("DocType", doctype) or frappe.get_meta(doctype).issingle:
		return None
	value = frappe.db.get_value(doctype, name, "modified")
	return str(value) if value else None
