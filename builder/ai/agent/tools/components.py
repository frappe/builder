"""Reusable components — promote what's already built into a Builder Component.

`create_component` (orchestrate.py) GENERATES a fresh component from a brief;
`extract_component` promotes an already-designed block on the focused page. No
LLM call — the copy is pixel-exact, which is the point: shared chrome (header,
footer, CTA banner) must be identical on every page, and after extraction it
lives in ONE place every page embeds."""

import copy

import frappe

from builder.ai.agent.registry import Tool
from builder.utils import compact_json


def run_extract_component(ctx, args: dict) -> str:
	from builder.ai.agent.tree import WorkingTree

	block_id = (args.get("block_id") or "").strip()
	name = (args.get("component_name") or "").strip()
	if not block_id or not name:
		return "FAILED: pass block_id (the block's ref) and component_name."
	root = ctx.tree.root if (getattr(ctx, "tree", None) and ctx.tree.root) else None
	if not isinstance(root, dict):
		return "FAILED: no page in focus — open_page first."
	tree = copy.deepcopy(root)
	view = WorkingTree(tree)
	target = view.resolve(block_id)
	if target is None:
		return f"FAILED: block_id '{block_id}' not found{view.id_hint(block_id)}"
	if target is tree:
		return "FAILED: can't extract the page root — pick a section (e.g. the header)."
	if target.get("extendedFromComponent") or target.get("isChildOfComponent"):
		return "FAILED: that block already belongs to a component — embed or edit that component instead."
	parent = view.parent_of(block_id)
	if parent is None:
		return f"FAILED: block_id '{block_id}' has no parent in the tree."
	from builder.ai.page_writer import component_instance_children

	component_id = create_component_doc(name, target)
	# Swap the subtree for an instance SKELETON — the same shape the editor's own
	# Save As Component persists (extendWithComponent + resetBlock): overrides
	# wiped so later component edits propagate to this page too, and every child
	# mapped to its component twin via referenceBlockId (the published renderer's
	# extend_block walks the PAGE children, so an empty instance renders empty).
	instance = {
		"blockId": target.get("blockId"),
		"element": target.get("element") or "div",
		"blockName": target.get("blockName") or name,
		"extendedFromComponent": component_id,
		"children": component_instance_children(component_id),
	}
	children = parent["children"]
	children[next(i for i, c in enumerate(children) if c.get("blockId") == block_id)] = instance
	ctx.queue_client_op({"tool_name": "set_page_blocks", "args": {"blocks": tree}})
	return (
		f"Extracted '{name}' as Builder Component {component_id}; the block is now an instance of it. "
		f"Embed it on any page as a block {{el: div, component: {component_id}}} — its inner blocks are "
		f"no longer page blocks, so later changes to it go through the component (run_python on the "
		f"Builder Component doc), not block edits."
	)


def create_component_doc(name: str, block: dict) -> str:
	block = copy.deepcopy(block)
	# A component must not carry page-flow positioning (same strip as the editor's
	# own Save As Component).
	for style_key in ("baseStyles", "mobileStyles", "tabletStyles"):
		styles = block.get(style_key)
		if isinstance(styles, dict):
			for prop in ("left", "top", "position"):
				styles.pop(prop, None)
	component_id = frappe.generate_hash(length=12)
	frappe.get_doc(
		{
			"doctype": "Builder Component",
			"component_name": name,
			"component_id": component_id,
			"block": compact_json(block),
		}
	).insert(ignore_permissions=True)
	return component_id


extract_component_tool = Tool(
	name="extract_component",
	side="server",
	description=(
		"Promote an already-built block (with all its children) into a reusable Builder Component — "
		"a pixel-exact copy, no regeneration. The original block becomes an instance of it. Use it when "
		"a designed section should be SHARED across pages (the header/nav, the footer, a CTA banner): "
		"extract once, then embed on other pages as a block {el: div, component: <id>} — header first, "
		"footer last. Every page then stays identical, and one component edit updates all of them."
	),
	parameters={
		"type": "object",
		"properties": {
			"block_id": {
				"type": "string",
				"description": "The block's ref (from the page context / query_blocks).",
			},
			"component_name": {
				"type": "string",
				"description": "Human-readable name, e.g. 'Site Header'.",
			},
		},
		"required": ["block_id", "component_name"],
	},
	handler=run_extract_component,
)

TOOLS = [extract_component_tool]
