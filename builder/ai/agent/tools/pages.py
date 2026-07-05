"""Page focus tools — open, create, and read Builder Pages headlessly.

These give the page-less (dashboard) agent the same mental model the editor has:
FOCUS one page (open_page / create_page) and the block tools, query_blocks /
read_block, and generate_page all act on it; or READ any page (read_page)
without moving focus — e.g. to study a reference page's design."""

import re

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
	from builder.ai.orchestration import create_draft_page, get_or_create_site_folder, page_has_blocks

	title = (args.get("page_title") or "").strip()
	if not title:
		return "FAILED: page_title is required."
	if not frappe.has_permission("Builder Page", "create"):
		return "FAILED: you don't have permission to create pages."
	# The page the user has OPEN is where their build must land. create_page while
	# the open page is still empty silently splits the build onto an orphan page:
	# the canvas shows only the throwaway preview and the user's page stays blank.
	canvas_page = getattr(ctx, "canvas_page_id", None)
	if canvas_page and not page_has_blocks(canvas_page):
		return (
			"DECLINED: the page the user has OPEN is still empty — build THAT page. "
			"generate_page builds the currently open page; rename it / set its route via "
			"set_page_settings or run_python. create_page is only for ADDITIONAL pages, "
			"after the open one has content."
		)
	folder = (args.get("folder") or "").strip() or None
	if folder and not frappe.db.exists("Builder Project Folder", folder):
		folder = get_or_create_site_folder(folder, title)
	page_id = create_draft_page(folder, title, args.get("route"))
	route = frappe.db.get_value("Builder Page", page_id, "route")
	ctx.focus_page(page_id)
	if ctx.current_activity is not None:
		ctx.current_activity["page"] = page_id  # "Open" link on the activity line
	result = f"Created draft page '{title}' (id={page_id}, route=/{route}) and opened it — build it with generate_page."
	# An additional page must read as the SAME SITE. Weaker loop models skim the
	# system prompt's consistency rule, so restate it here — with the sibling's
	# actual design system in hand — right before the model writes the brief.
	if consistency := sibling_design_summary(canvas_page):
		result += (
			f"\nCONSISTENCY (mandatory): this is an additional page of an existing site — it must look like "
			f"the SAME site as {canvas_page}. Do NOT present design/layout/typography cards for it. Write the "
			f"generate_page brief FROM that page's system: the same nav and footer structure (link this new "
			f"page in both), and exactly these tokens —\n{consistency}\n"
			f"Reuse its client scripts' class hooks (get_page_scripts on {canvas_page}) via set_page_script "
			f"on this page."
		)
	return result


def sibling_design_summary(page_id: str | None) -> str:
	"""The design tokens an additional page must inherit, read from the sibling
	page's draft: fonts and var(--…) palette handles, plus its script names."""
	if not page_id:
		return ""
	blocks = frappe.db.get_value("Builder Page", page_id, "draft_blocks") or ""
	if len(blocks) < 200:
		blocks = frappe.db.get_value("Builder Page", page_id, "blocks") or ""
	if not blocks:
		return ""
	fonts = sorted(set(re.findall(r'"fontFamily":\s*"([^"]+)"', blocks)))
	handles = sorted(set(re.findall(r"var\((--[a-zA-Z0-9-]+)", blocks)))
	scripts = frappe.get_all(
		"Builder Client Script",
		filters=[
			[
				"name",
				"in",
				[
					r.builder_script
					for r in frappe.get_doc("Builder Page", page_id).get("client_scripts") or []
				],
			]
		],
		fields=["name", "script_type"],
	)
	parts = []
	if fonts:
		parts.append(f"fonts: {', '.join(fonts)}")
	if handles:
		parts.append(f"palette handles: {', '.join(f'var({h})' for h in handles)}")
	if scripts:
		parts.append(f"scripts: {', '.join(f'{s.name} ({s.script_type})' for s in scripts)}")
	return "\n".join(parts)


def run_copy_page_design(ctx, args: dict) -> str:
	"""The high-fidelity path for "make a page like @X": copy X's block tree (and
	repeater data script) into the focused page verbatim — a data copy, no LLM in
	the loop, so components, theme tokens, spacing and typography survive exactly.
	The agent then ADAPTS the copy with the surgical block tools."""
	from builder.ai import page_writer
	from builder.ai.agent.loop import render_page_context
	from builder.ai.agent.tree import WorkingTree
	from builder.utils import compact_json

	if not ctx.page_id:
		return "FAILED: no page is open — create_page or open_page first, then copy into it."
	source = (args.get("source_page_id") or "").strip()
	if not source or not frappe.db.exists("Builder Page", source):
		return f"FAILED: source page '{source}' not found — find its id with query_records."
	if source == ctx.page_id:
		return "FAILED: the source is the page you're editing."
	if not frappe.has_permission("Builder Page", "read", source):
		return "FAILED: you don't have permission to read the source page."
	root = page_writer.load_page_root(source)
	if root is None:
		return f"Page {source} is empty — nothing to copy."
	data_script = frappe.db.get_value("Builder Page", source, "page_data_script")
	ctx.ensure_revert_snapshot()  # copying replaces the focused page's block tree
	frappe.db.set_value(
		"Builder Page",
		ctx.page_id,
		{"draft_blocks": compact_json([root]), "page_data_script": data_script or ""},
	)
	frappe.db.commit()
	ctx.tree = WorkingTree(root)
	return (
		f"Copied the full design of {source} into this page — components, theme tokens, and "
		"layout are now identical. ADAPT it for its new purpose with the block tools "
		"(query_blocks + update_blocks patches for the copy, remove/add sections as needed).\n"
		f"{render_page_context(root)}"
	)


def request_manage_pages(ctx, args: dict) -> str | None:
	from builder.ai.agent import pending

	action = (args.get("action") or "").strip()
	page_ids = [p for p in (args.get("page_ids") or []) if frappe.db.exists("Builder Page", p)]
	if not page_ids:
		return (
			"DECLINED: none of those page ids exist — find the real ids with query_records('Builder Page')."
		)
	titles = [frappe.db.get_value("Builder Page", p, "page_title") or p for p in page_ids]
	summary = f"{action.capitalize()} {len(titles)} page(s): {', '.join(titles)}?"
	pending.request_confirmation(ctx, "manage_pages", summary, {"action": action, "page_ids": page_ids})
	return None


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
		"new page ALWAYS use this — never spawn_parallel_agents. When the site already has "
		"designed pages, do NOT run the design flow for the new page: it inherits the "
		"existing site's design system (the result of this call names the exact tokens)."
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

copy_page_design = Tool(
	name="copy_page_design",
	side="server",
	handler=run_copy_page_design,
	description=(
		"Copy another page's ENTIRE design (block tree + repeater data) into the page you "
		"have open — an exact, lossless copy that keeps shared components, var(--token) "
		"references, spacing and typography identical. THE default first step when the user "
		"wants a new page matching an existing one ('like @X', 'refer @X for design'): "
		"create_page, copy_page_design, then adapt the copy's text and sections with the "
		"block tools. Far more faithful and cheaper than regenerating from scratch."
	),
	parameters={
		"type": "object",
		"properties": {
			"source_page_id": {
				"type": "string",
				"description": "The Builder Page id whose design to copy from.",
			},
		},
		"required": ["source_page_id"],
	},
)

manage_pages = Tool(
	name="manage_pages",
	side="terminal",
	handler=request_manage_pages,
	description=(
		"Publish, unpublish, or DELETE pages — the ONLY way to take a page down or remove "
		"it. Asks the user to confirm before anything changes. NEVER improvise page "
		"lifecycle through scripts or data tools."
	),
	parameters={
		"type": "object",
		"properties": {
			"action": {"type": "string", "enum": ["publish", "unpublish", "delete"]},
			"page_ids": {
				"type": "array",
				"items": {"type": "string"},
				"description": "Builder Page ids (find them with query_records).",
			},
		},
		"required": ["action", "page_ids"],
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

TOOLS = [open_page, create_page, copy_page_design, read_page, manage_pages]
