"""Reusable components — promote what's already built into a Builder Component.

`extract_component` promotes an already-designed block on the open page. No
LLM call — the copy is pixel-exact, which is the point: shared chrome (header,
footer, CTA banner) must be identical on every page, and after extraction it
lives in ONE place every page embeds. `edit_component` changes that one place and
syncs every page that embeds it."""

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
		return "FAILED: no page is open."
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
		f"no longer page blocks, so later changes to it go through the component "
		f"(edit_component), not block edits."
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


EDIT_OPS = ("update_block", "update_blocks", "add_block", "remove_block", "move_block")


def run_edit_component(ctx, args: dict) -> str:
	"""Apply block ops to a Builder Component's own definition, save it and sync every page that embeds it."""
	from builder.ai.agent.tree import ComponentTree

	component_id = (args.get("component_id") or "").strip()
	ops = [op for op in args.get("ops") or [] if isinstance(op, dict)]
	if not component_id or not ops:
		return "FAILED: pass component_id and at least one op."
	if not frappe.db.exists("Builder Component", component_id):
		return f"FAILED: Builder Component '{component_id}' not found. query_records('Builder Component') lists them."
	component = frappe.get_doc("Builder Component", component_id)
	if not component.has_permission("write"):
		return "FAILED: you don't have permission to edit Builder Components."
	tree = ComponentTree(frappe.parse_json(component.block or "{}"), component_id)
	if not isinstance(tree.root, dict) or not tree.root:
		return f"FAILED: component {component_id} has no readable block tree."
	results = [apply_component_op(tree, op) for op in ops]
	report = "\n".join(results)
	if all("FAILED" in result for result in results):
		return f"FAILED: nothing changed.\n{report}"
	component.block = compact_json(tree.root)
	component.save()
	pages = component.sync_component()
	refresh_open_page(ctx, pages)
	return f"Saved component {component_id} and synced {len(pages)} page(s) that embed it, published ones included.\n{report}"


def apply_component_op(tree, op: dict) -> str:
	"""Run one {tool, args} op on the component tree, prefixing the result with the tool name."""
	tool = op.get("tool")
	if tool not in EDIT_OPS:
		return f"{tool}: FAILED: not an edit op. Use one of {', '.join(EDIT_OPS)}."
	return f"{tool}: {tree.apply(tool, op.get('args') or {})}"


def refresh_open_page(ctx, synced_pages: list[str]) -> None:
	"""The sync rewrote the open page in the database; point the working tree and canvas at it."""
	from builder.ai.page_writer import load_page_root

	page_id = getattr(ctx, "page_id", None)
	if page_id in synced_pages and (root := load_page_root(page_id)):
		ctx.queue_client_op({"tool_name": "set_page_blocks", "args": {"blocks": root}})


edit_component_tool = Tool(
	name="edit_component",
	side="server",
	description=(
		"Change a Builder Component's OWN definition and sync it to every page that embeds it. This "
		"is how shared chrome changes site-wide: rename or add a nav link, restyle the footer, declare "
		"a new prop. Block edits on a page's child_of refs only override that one page. Refs here are "
		"the component's internal refs: the `ref`s get_document('Builder Component', id) shows, which "
		"are also the `of` values on a page's child_of refs. Each op is {tool, args}: tool is "
		"update_block, update_blocks, add_block, remove_block or move_block, and args are that tool's "
		"usual arguments. On the component root, update_block `props` declare the component's props "
		"with their defaults, and client_script works on any block. Put every change to one component "
		"in ONE call. Published pages that embed it update immediately."
	),
	parameters={
		"type": "object",
		"properties": {
			"component_id": {
				"type": "string",
				"description": "The Builder Component's component_id.",
			},
			"ops": {
				"type": "array",
				"description": "Edits applied in order to the component's block tree.",
				"items": {
					"type": "object",
					"properties": {
						"tool": {"type": "string", "enum": list(EDIT_OPS)},
						"args": {
							"type": "object",
							"description": "That tool's usual arguments, with refs from the component.",
						},
					},
					"required": ["tool", "args"],
				},
			},
		},
		"required": ["component_id", "ops"],
	},
	handler=run_edit_component,
)


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

TOOLS = [extract_component_tool, edit_component_tool]
