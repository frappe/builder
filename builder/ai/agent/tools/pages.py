"""Page focus tools — open, create, and read Builder Pages headlessly.

These give the page-less (dashboard) agent the same mental model the editor has:
FOCUS one page (open_page / create_page) and the block tools, query_blocks /
read_block, and generate_page all act on it; or READ any page (read_page)
without moving focus — e.g. to study a reference page's design."""

import frappe

from builder.ai.agent.registry import Tool


def run_open_page(ctx, args: dict) -> str:
	page_id = (args.get("page_id") or "").strip()
	if not page_id or not frappe.db.exists("Builder Page", page_id):
		return f"FAILED: Builder Page '{page_id}' not found — find its id with query_records."
	if not frappe.has_permission("Builder Page", "write", page_id):
		return "FAILED: you don't have permission to edit this page."
	return ctx.focus_page(page_id)


def run_create_page(ctx, args: dict) -> str:
	from builder.ai.orchestration import create_draft_page, get_or_create_site_folder

	title = (args.get("page_title") or "").strip()
	if not title:
		return "FAILED: page_title is required."
	if not frappe.has_permission("Builder Page", "create"):
		return "FAILED: you don't have permission to create pages."
	folder = (args.get("folder") or "").strip() or None
	if folder and not frappe.db.exists("Builder Project Folder", folder):
		folder = get_or_create_site_folder(folder, title)
	page_id = create_draft_page(folder, title, args.get("route"))
	route = frappe.db.get_value("Builder Page", page_id, "route")
	ctx.focus_page(page_id)
	if ctx.current_activity is not None:
		ctx.current_activity["page"] = page_id  # "Open" link on the activity line
	return f"Created draft page '{title}' (id={page_id}, route=/{route}) and opened it — build it with generate_page."


def run_read_page(ctx, args: dict) -> str:
	from builder.ai import page_writer
	from builder.ai.agent.loop import render_page_context
	from builder.ai.agent.selectors import find_block
	from builder.ai.block_codec import BlockCodec
	from builder.utils import to_compact_yaml

	page_id = (args.get("page_id") or "").strip()
	if not page_id or not frappe.db.exists("Builder Page", page_id):
		return f"FAILED: Builder Page '{page_id}' not found — find its id with query_records."
	if not frappe.has_permission("Builder Page", "read", page_id):
		return "FAILED: you don't have permission to read this page."
	root = page_writer.load_page_root(page_id)
	if root is None:
		return f"Page {page_id} is empty."
	if ref := (args.get("block_id") or "").strip():
		block = find_block(root, ref)
		if block is None:
			return f"No block found with ref {ref} on page {page_id}."
		detail = to_compact_yaml(BlockCodec.compress(block, depth=0, task_tier="complex"))
		return f"Block {ref} of page {page_id}:\n{detail}"
	return f"Structure of page {page_id} (read-only — edits still target your focused page):\n{render_page_context(root)}"


open_page = Tool(
	name="open_page",
	side="server",
	handler=run_open_page,
	description=(
		"Open an existing Builder Page for editing: loads its structure into your context "
		"and points the block tools (update_block, add_block, …), query_blocks/read_block, "
		"and generate_page at it. Use this before any surgical change to an existing page."
	),
	parameters={
		"type": "object",
		"properties": {
			"page_id": {
				"type": "string",
				"description": "The Builder Page id (find it with query_records('Builder Page', ['name','page_title','route']) or from an @mention hint).",
			},
		},
		"required": ["page_id"],
	},
)

create_page = Tool(
	name="create_page",
	side="server",
	handler=run_create_page,
	description=(
		"Create a new draft Builder Page and open it for building. Then call generate_page "
		"with a rich brief for a full page, or add_block for a small fragment. For a single "
		"new page ALWAYS use this — never spawn_parallel_agents."
	),
	parameters={
		"type": "object",
		"properties": {
			"page_title": {"type": "string", "description": "Human title of the page (e.g. 'Philosophy')."},
			"route": {
				"type": "string",
				"description": "URL route (e.g. 'philosophy'). Defaults to a slug of the title.",
			},
			"folder": {
				"type": "string",
				"description": "Optional Builder Project Folder to group the page under (created if missing).",
			},
		},
		"required": ["page_title"],
	},
)

read_page = Tool(
	name="read_page",
	side="server",
	handler=run_read_page,
	description=(
		"Read any page's full structure (compact YAML; an outline for very large pages) "
		"WITHOUT changing which page you're editing. Use it to study a reference page's "
		"design — layout rhythm, typography, palette, spacing — before building something "
		"that should match it. Pass block_id to drill into one block in full detail."
	),
	parameters={
		"type": "object",
		"properties": {
			"page_id": {"type": "string", "description": "The Builder Page id to read."},
			"block_id": {
				"type": "string",
				"description": "Optional: a block ref from a previous read to expand in full detail.",
			},
		},
		"required": ["page_id"],
	},
)

TOOLS = [open_page, create_page, read_page]
