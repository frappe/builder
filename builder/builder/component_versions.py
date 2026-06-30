# Copyright (c) 2026, Frappe Technologies Pvt Ltd and contributors
# For license information, please see license.txt

"""Version-pinned Builder Component dependencies for pages.

Components are shared and mutable, so a page would render with whatever a
component looks like now, not when it was added. We capture immutable component
versions (stored as "Component Version" Builder Snapshots) and pin the exact
version a block referenced via a sibling block key `componentVersion`.

A version is captured whenever a component is saved, and when a component is
first used in a page (drag-drop / save-as-component) the latest version is
pinned to the block. Snapshots store the blocks as-is, pins included.

Each version snapshot stores the full component state (block, scripts, props)
so a pinned instance renders with the exact component it was added with,
not just the block layout.
"""

import copy

import frappe

from builder.builder.doctype.builder_snapshot.builder_snapshot import (
	get_snapshot_data,
	prune_snapshots,
)
from builder.utils import compact_json

COMPONENT_VERSION_TYPE = "Component Version"
# A pin to a pruned version degrades to the latest live component, so pruning is safe.
COMPONENT_VERSION_KEEP = 50

# Fields captured per component version (the full state needed to render)
COMPONENT_VERSION_FIELDS = [
	"block",
	"component_data_script",
]


def walk_blocks(node, visitor):
	"""Call visitor(block) for every block dict in a blocks tree (dict or list)."""
	if isinstance(node, dict):
		visitor(node)
		for child in node.get("children") or []:
			walk_blocks(child, visitor)
	elif isinstance(node, list):
		for item in node:
			walk_blocks(item, visitor)


def pin_components_in_page_data(data: dict) -> dict:
	"""`take_snapshot` transform: pin component versions inside captured blocks.

	Returns a copy of `data` where any `draft_blocks` / `blocks` JSON has
	`componentVersion` set on every component instance block. Other fields pass through untouched.
	"""
	out = dict(data)
	cache: dict[str, str | None] = {}
	for key in ("draft_blocks", "blocks"):
		value = out.get(key)
		if not value:
			continue
		blocks = copy.deepcopy(frappe.parse_json(value))
		walk_blocks(blocks, lambda block: pin_block(block, set(), cache))
		out[key] = compact_json(blocks)
	return out


def canonical(block_json, strip_pins=False):
	"""Stable serialization for comparing two block JSON strings."""
	parsed = frappe.parse_json(block_json or "{}")
	if strip_pins:
		walk_blocks(parsed, lambda block: block.pop("componentVersion", None))
	return frappe.as_json(parsed)


def pin_block(block: dict, visited: set[str], cache: dict) -> None:
	"""Set `componentVersion` on a block that references a component."""
	component_id = block.get("extendedFromComponent")
	if not component_id:
		return
	version = ensure_component_version(component_id, visited, cache)
	if version:
		block["componentVersion"] = version
	else:
		block.pop("componentVersion", None)


def ensure_component_version(
	component_id: str, visited: set[str] | None = None, cache: dict | None = None
) -> str | None:
	"""Ensure a "Component Version" snapshot of the component's current state exists.

	The stored block has its own nested components pinned too (cycle-guarded via
	`visited`). Deduplicates against the latest existing version, and memoizes the
	result per component for the duration of a capture via `cache`. Returns the
	version snapshot name, or None if the component no longer exists.
	"""
	if cache is not None and component_id in cache:
		return cache[component_id]

	values = frappe.db.get_value("Builder Component", component_id, COMPONENT_VERSION_FIELDS, as_dict=True)
	if values is None:
		if cache is not None:
			cache[component_id] = None
		return None

	if visited is None:
		visited = set()
	if component_id in visited:
		# cyclic reference -- break the loop without caching the partial result
		return latest_version(component_id)
	visited.add(component_id)
	try:
		block = frappe.parse_json(values.block or "{}")
		if isinstance(block, dict) and block:
			walk_blocks(block, lambda nested: pin_block(nested, visited, cache))

		data = {
			"block": compact_json(block),
			"component_data_script": values.component_data_script,
		}
		data_json = compact_json(data)

		latest = latest_version(component_id)
		if latest and compact_json(get_snapshot_data(latest)) == data_json:
			version = latest
		else:
			version = (
				frappe.get_doc(
					{
						"doctype": "Builder Snapshot",
						"reference_doctype": "Builder Component",
						"reference_name": component_id,
						"snapshot_type": COMPONENT_VERSION_TYPE,
						"data": data_json,
					}
				)
				.insert(ignore_permissions=True)
				.name
			)
			prune_snapshots(
				"Builder Component",
				component_id,
				keep=COMPONENT_VERSION_KEEP,
				snapshot_type=COMPONENT_VERSION_TYPE,
			)
	finally:
		visited.discard(component_id)

	if cache is not None:
		cache[component_id] = version
	return version


def latest_version(component_id: str) -> str | None:
	names = frappe.get_all(
		"Builder Snapshot",
		filters={
			"reference_doctype": "Builder Component",
			"reference_name": component_id,
			"snapshot_type": COMPONENT_VERSION_TYPE,
		},
		order_by="creation desc",
		limit=1,
		pluck="name",
	)
	return names[0] if names else None


def resolve_component(component_id: str, pinned_version: str | None = None) -> dict | None:
	"""Return the component's fields as a dict, honoring a pinned version.

	Returns a dict with keys from ``COMPONENT_VERSION_FIELDS``. Pinned version
	found -> its fields; pinned version missing (pruned/invalid) -> latest live
	component; component deleted -> None.
	"""
	if pinned_version:
		data = frappe.db.get_value(
			"Builder Snapshot",
			{
				"name": pinned_version,
				"reference_doctype": "Builder Component",
				"reference_name": component_id,
				"snapshot_type": COMPONENT_VERSION_TYPE,
			},
			"data",
		)
		if data:
			return frappe.parse_json(data)
	values = frappe.get_cached_value(
		"Builder Component", component_id, COMPONENT_VERSION_FIELDS, as_dict=True
	)
	if values is None:
		return None
	return {
		"block": values.block,
		"component_data_script": values.component_data_script,
	}


def is_pin_outdated(component_id: str, pinned_version: str) -> bool:
	"""True if the live component differs from the pinned version (ignoring pins)."""
	live = resolve_component(component_id)
	if live is None:
		return False
	pinned = resolve_component(component_id, pinned_version)
	if pinned is None:
		return False
	return canonical_component(live) != canonical_component(pinned)


def canonical_component(data: dict) -> str:
	"""Stable serialization for comparing two component field dicts."""
	out = dict(data)
	block = out.get("block")
	if block:
		parsed = frappe.parse_json(block)
		walk_blocks(parsed, lambda b: b.pop("componentVersion", None))
		out["block"] = frappe.as_json(parsed)
	return compact_json(out)


def collect_restore_warnings(blocks_json: str | None) -> list[str]:
	"""Warnings for component refs that can't render (deleted, with no usable pin)."""
	warnings: list[str] = []
	seen: set[str] = set()

	def check(block):
		component_id = block.get("extendedFromComponent")
		if component_id and component_id not in seen:
			seen.add(component_id)
			if resolve_component(component_id, block.get("componentVersion")) is None:
				warnings.append(
					frappe._("Component {0} was deleted and will not render").format(component_id)
				)

	walk_blocks(frappe.parse_json(blocks_json or "[]"), check)
	return warnings
