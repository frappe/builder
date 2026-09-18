"""What changed on a page, in lines Bob can act on, and folding the user's mid-turn
edits into the working tree.

Bob works from the page as it last saw it. When the user edits between turns, or
while a turn is running, these lines tell Bob what they changed so it builds on
those edits instead of undoing them."""

import copy
import json
import re
from collections import defaultdict

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


def snapshot_blocks(root: dict | None) -> dict[str, tuple]:
	"""Each block's parent, position and compared values, frozen so later edits can't reach them."""
	snapshot = {}
	stack = [(root, None, 0)] if isinstance(root, dict) else []
	while stack:
		block, parent_ref, position = stack.pop()
		snapshot[block.get("blockId")] = (
			parent_ref,
			position,
			{key: frozen(block.get(key)) for key in COMPARED_KEYS},
		)
		stack.extend(
			(child, block.get("blockId"), i)
			for i, child in enumerate(block.get("children") or [])
			if isinstance(child, dict)
		)
	return snapshot


def frozen(value) -> str:
	return json.dumps(value or None, sort_keys=True, default=str)


def round_effects(before: dict, after: dict) -> list[tuple]:
	"""What one round of block ops did to the page: field changes, added, removed and moved blocks."""
	effects = []
	for ref, (parent_ref, position, values) in after.items():
		if ref not in before:
			if parent_ref in before:
				effects.append(("add", ref, parent_ref, position))
			continue
		old_parent, _, old_values = before[ref]
		effects += [
			("field", ref, key, old_values[key], value)
			for key, value in values.items()
			if old_values[key] != value
		]
		if old_parent != parent_ref:
			effects.append(("move", ref, old_parent, parent_ref, position))
	effects += [
		("remove", ref)
		for ref, (parent_ref, _, _) in before.items()
		if ref not in after and parent_ref in after
	]
	return effects


def merge_saved_draft(saved: dict, rounds: list[list[tuple]], current: dict) -> dict:
	"""The draft the user saved mid-turn, plus the rounds the editor had not saved yet.
	A round the saved draft already shows is never re-applied, and an unsaved field
	change lands only where the field still holds its old value, so the user's edits win."""
	merged = copy.deepcopy(saved)
	shown = snapshot_blocks(merged)
	saved_up_to = max(
		(i for i, effects in enumerate(rounds) if any(is_shown(effect, shown) for effect in effects)),
		default=-1,
	)
	latest = index_blocks(current)
	for effects in rounds[saved_up_to + 1 :]:
		for effect in effects:
			reapply(merged, effect, latest)
	return merged


def is_shown(effect: tuple, shown: dict) -> bool:
	kind, ref = effect[0], effect[1]
	if kind == "field":
		return ref in shown and shown[ref][2][effect[2]] == effect[4]
	if kind == "add":
		return ref in shown
	if kind == "remove":
		return ref not in shown
	return ref in shown and shown[ref][0] == effect[3]


def reapply(merged: dict, effect: tuple, latest: dict) -> None:
	index = index_blocks(merged)
	kind, ref = effect[0], effect[1]
	if kind == "field":
		_, _, key, old_value, new_value = effect
		block = index[ref][0] if ref in index else None
		if block is not None and frozen(block.get(key)) == old_value:
			if (value := json.loads(new_value)) is None:
				block.pop(key, None)
			else:
				block[key] = value
	elif kind == "add":
		_, _, parent_ref, position = effect
		if ref not in index and parent_ref in index and ref in latest:
			insert_at(index[parent_ref][0], copy.deepcopy(latest[ref][0]), position)
	elif kind == "remove":
		if ref in index and index[ref][1] in index:
			detach(index[index[ref][1]][0], ref)
	elif ref in index and index[ref][1] == effect[2] and effect[3] in index:
		detach(index[effect[2]][0], ref)
		insert_at(index[effect[3]][0], index[ref][0], effect[4])


def insert_at(parent: dict, block: dict, position: int) -> None:
	children = parent.setdefault("children", [])
	children.insert(min(position, len(children)), block)


def detach(parent: dict, ref: str) -> None:
	parent["children"] = [child for child in parent.get("children") or [] if child.get("blockId") != ref]


def page_state(page_id: str, root: dict | None, doc_keys) -> dict:
	"""The open page as a turn left it, plus when each other document the chat changed was last modified."""
	return {
		"page": page_id,
		"blocks": root,
		"fields": page_fields(page_id),
		"scripts": attached_scripts(page_id),
		"docs": modified_stamps(key for key in doc_keys if key != ("Builder Page", page_id)),
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
	docs = state.get("docs") or {}
	stamps = modified_stamps(tuple(key.split("::", 1)) for key in docs)
	for key, modified in docs.items():
		doctype, name = key.split("::", 1)
		if key not in stamps:
			lines.append(f"{doctype} '{name}' was deleted")
		elif stamps[key] != modified:
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


def modified_stamps(doc_keys) -> dict[str, str]:
	"""`doctype::name` -> last modified, one query per doctype. Singles and missing documents are left out."""
	names_by_doctype = defaultdict(list)
	for doctype, name in doc_keys:
		names_by_doctype[doctype].append(name)
	stamps = {}
	for doctype, names in names_by_doctype.items():
		if not frappe.db.exists("DocType", doctype) or frappe.get_meta(doctype).issingle:
			continue
		for row in frappe.get_all(doctype, filters={"name": ("in", names)}, fields=["name", "modified"]):
			stamps[f"{doctype}::{row.name}"] = str(row.modified)
	return stamps
