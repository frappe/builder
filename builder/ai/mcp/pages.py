"""MCP-native page management tools.

The in-app agent gets its page focus from the editor session; over MCP every
call is self-contained, so these tools cover discovery and lifecycle (list,
create, read, duplicate, publish, delete, snapshot). Page resolution happens
in dispatch: page-taking handlers receive a ctx already bound to a validated
page, with the `page` argument popped from args.
"""

import base64

import frappe

from builder.ai import page_writer
from builder.ai.agent.registry import Tool

PAGE_PARAM = {"type": "string", "description": "The Builder Page id to act on (from list_pages)."}


def run_list_pages(ctx, args: dict) -> str:
	filters = {"project_folder": args["folder"]} if args.get("folder") else {}
	pages = frappe.get_all(
		"Builder Page",
		fields=["name", "page_title", "route", "published", "modified"],
		filters=filters,
		order_by="modified desc",
		limit=int(args.get("limit") or 50),
	)
	lines = [
		f"{p.name}  '{p.page_title or ''}'  /{p.route or ''}  {'published' if p.published else 'draft'}"
		for p in pages
	]
	return "\n".join(lines) or "No pages found."


def run_create_page(ctx, args: dict) -> str:
	title = (args.get("page_title") or "").strip()
	if not title:
		return "FAILED: page_title is required."
	if not frappe.has_permission("Builder Page", "create"):
		return "FAILED: you don't have permission to create pages."
	route = (args.get("route") or title).strip().strip("/").lower().replace(" ", "-") or "home"
	if taken := frappe.db.get_value("Builder Page", {"route": route}):
		return f"FAILED: route '/{route}' is already used by page {taken}. Pick another."
	folder = (args.get("folder") or "").strip() or None
	if folder and not frappe.db.exists("Builder Project Folder", folder):
		folder = frappe.get_doc({"doctype": "Builder Project Folder", "folder_name": folder}).insert().name
	doc = frappe.get_doc(
		{
			"doctype": "Builder Page",
			"page_title": title,
			"route": route,
			"project_folder": folder or "",
			"published": 0,
			"draft_blocks": "[]",
		}
	).insert()
	return f"Created draft page '{title}' (id={doc.name}, route=/{doc.route}). Build it with add_block."


def run_read_page(ctx, args: dict) -> str:
	from builder.ai.agent.loop import render_page_context
	from builder.ai.agent.selectors import find_block
	from builder.ai.block_codec import BlockCodec
	from builder.utils import to_compact_yaml

	root = page_writer.load_page_root(ctx.page_id)
	if root is None:
		return f"Page {ctx.page_id} is empty. Build it with add_block."
	if ref := (args.get("block_id") or "").strip():
		block = find_block(root, ref)
		if block is None:
			return f"No block found with ref {ref} on page {ctx.page_id}."
		detail = to_compact_yaml(BlockCodec.compress(block, depth=0, task_tier="complex"))
		return f"Block {ref} of page {ctx.page_id}:\n{detail}"
	return f"Structure of page {ctx.page_id}:\n{render_page_context(root)}"


def run_duplicate_page(ctx, args: dict) -> str:
	from builder.api import duplicate_page

	new_page = duplicate_page(ctx.page_id)
	return f"Duplicated {ctx.page_id} as {new_page.name} (route=/{new_page.route}, draft)."


def run_publish_page(ctx, args: dict) -> str:
	from frappe.utils import get_url

	doc = frappe.get_doc("Builder Page", ctx.page_id)
	route = doc.publish()
	return f"Published {ctx.page_id} at {get_url('/' + (route or ''))}"


def run_unpublish_page(ctx, args: dict) -> str:
	frappe.get_doc("Builder Page", ctx.page_id).unpublish()
	return f"Unpublished {ctx.page_id}. Its route no longer serves."


def run_delete_page(ctx, args: dict) -> str:
	if not frappe.has_permission("Builder Page", "delete", ctx.page_id):
		return "FAILED: you don't have permission to delete this page."
	frappe.delete_doc("Builder Page", ctx.page_id)
	return f"Deleted page {ctx.page_id}."


def run_snapshot_page(ctx, args: dict) -> str:
	doc = frappe.get_doc("Builder Page", ctx.page_id)
	snap = doc.create_manual_snapshot(args.get("label") or "MCP checkpoint")
	if not snap:
		return "FAILED: the page is empty, nothing to snapshot."
	return f"Snapshot saved: {snap}"


def run_revert_page(ctx, args: dict) -> str:
	snap = (args.get("snapshot") or "").strip() or frappe.db.get_value(
		"Builder Snapshot",
		{"reference_doctype": "Builder Page", "reference_name": ctx.page_id},
		"name",
		order_by="creation desc",
	)
	if not snap:
		return "FAILED: no snapshot exists for this page."
	doc = frappe.get_doc("Builder Page", ctx.page_id)
	doc.restore_snapshot(snap)
	if root := page_writer.load_page_root(ctx.page_id):
		ctx.mirror_page_root(root)
	return f"Restored snapshot {snap} into the draft. Publish to take it live."


def run_copy_page_design(ctx, args: dict) -> str:
	from builder.ai.agent.loop import render_page_context
	from builder.utils import compact_json

	source = (args.get("source_page_id") or "").strip()
	if not source or not frappe.db.exists("Builder Page", source):
		return f"FAILED: source page '{source}' not found. Find its id with list_pages."
	if source == ctx.page_id:
		return "FAILED: the source is the page you're copying into."
	if not frappe.has_permission("Builder Page", "read", source):
		return "FAILED: you don't have permission to read the source page."
	root = page_writer.load_page_root(source)
	if root is None:
		return f"Page {source} is empty, nothing to copy."
	data_script = frappe.db.get_value("Builder Page", source, "page_data_script")
	ctx.ensure_revert_snapshot()
	frappe.db.set_value(
		"Builder Page",
		ctx.page_id,
		{"draft_blocks": compact_json([root]), "page_data_script": data_script or ""},
	)
	ctx.mirror_page_root(root)
	return (
		f"Copied the full design of {source} into {ctx.page_id}: components, theme tokens and "
		"layout are now identical. Adapt the copy with the block tools.\n"
		f"{render_page_context(root)}"
	)


def run_preview_page(ctx, args: dict) -> str | list:
	from builder.ai.agent.tools.preview import (
		MAX_IMAGE_BYTES,
		refresh_page_thumbnail,
		render_page_image,
		tile_screenshot,
	)

	page = frappe.get_doc("Builder Page", ctx.page_id)
	try:
		image = render_page_image(page)
	except Exception:
		return "Preview unavailable (screenshot renderer not reachable). Continue without the visual check."
	refresh_page_thumbnail(page)
	try:
		tiles, complete = tile_screenshot(image)
	except Exception:
		tiles, complete = [image], True
	note = "Draft screenshots, top to bottom." if len(tiles) > 1 else "Draft screenshot."
	if not complete:
		note += " They stop before the end of the page."
	note += " Review for breakage: unreadable contrast, overlap, empty or collapsed sections."
	content: list[dict] = [{"type": "text", "text": note}]
	for tile in tiles:
		if len(tile) <= MAX_IMAGE_BYTES:
			content.append(
				{"type": "image", "data": base64.b64encode(tile).decode(), "mimeType": "image/webp"}
			)
	return content


def page_tool(
	name: str, handler, description: str, properties: dict | None = None, required: list | None = None
) -> Tool:
	return Tool(
		name=name,
		side="server",
		handler=handler,
		description=description,
		parameters={
			"type": "object",
			"properties": {"page": PAGE_PARAM, **(properties or {})},
			"required": ["page", *(required or [])],
		},
	)


TOOLS = [
	Tool(
		name="list_pages",
		side="server",
		handler=run_list_pages,
		description=(
			"List this site's Builder Pages (id, title, route, published state), most recently "
			"modified first. The id is what every page tool's `page` argument takes."
		),
		parameters={
			"type": "object",
			"properties": {
				"folder": {"type": "string", "description": "Optional Builder Project Folder to filter by."},
				"limit": {"type": "integer", "description": "Max pages to return (default 50)."},
			},
		},
	),
	Tool(
		name="create_page",
		side="server",
		handler=run_create_page,
		description=(
			"Create a new draft Builder Page. When the site already has designed pages, make the "
			"new one look like the same site: study a sibling with read_page and reuse its tokens, "
			"components and script hooks (copy_page_design is the high-fidelity starting point)."
		),
		parameters={
			"type": "object",
			"properties": {
				"page_title": {
					"type": "string",
					"description": "Human title of the page (e.g. 'Philosophy').",
				},
				"route": {
					"type": "string",
					"description": "URL route (e.g. 'philosophy'). Defaults to a slug of the title.",
				},
				"folder": {
					"type": "string",
					"description": "Optional Builder Project Folder to group under (created if missing).",
				},
			},
			"required": ["page_title"],
		},
	),
	page_tool(
		"read_page",
		run_read_page,
		description=(
			"Read a page's full structure as compact YAML (an outline for very large pages). "
			"Each block shows a ref; pass a ref as block_id to any block tool to edit it, or "
			"pass block_id here to expand one block in full detail. Read before you edit."
		),
		properties={
			"block_id": {"type": "string", "description": "Optional: a block ref to expand in full detail."},
		},
	),
	page_tool(
		"duplicate_page",
		run_duplicate_page,
		description="Duplicate a page (blocks, settings and scripts) as a new draft.",
	),
	page_tool(
		"publish_page",
		run_publish_page,
		description="Publish a page's draft so it serves at its route. Returns the live URL.",
	),
	page_tool(
		"unpublish_page",
		run_unpublish_page,
		description="Take a published page down. Its route stops serving until published again.",
	),
	page_tool(
		"delete_page",
		run_delete_page,
		description="Permanently delete a page. Unrecoverable; prefer unpublish_page to take it offline.",
	),
	page_tool(
		"snapshot_page",
		run_snapshot_page,
		description=(
			"Save a named checkpoint of a page (blocks + data script) that revert_page can "
			"restore. Mutating tools already snapshot automatically; call this before a risky "
			"multi-step rework."
		),
		properties={
			"label": {"type": "string", "description": "Checkpoint label (default 'MCP checkpoint')."}
		},
	),
	page_tool(
		"revert_page",
		run_revert_page,
		description=(
			"Restore a page's draft to a snapshot: by name, or the most recent one when omitted. "
			"Undoes draft edits made since that snapshot."
		),
		properties={
			"snapshot": {
				"type": "string",
				"description": "Snapshot name; defaults to the latest for this page.",
			}
		},
	),
	page_tool(
		"copy_page_design",
		run_copy_page_design,
		description=(
			"Copy another page's ENTIRE design (block tree + data script) into `page`, an exact "
			"lossless copy that keeps shared components, var(--token) references, spacing and "
			"typography identical. The default first step for 'a new page like X': create_page, "
			"copy_page_design, then adapt the copy's text and sections with the block tools. "
			"Replaces the target page's current draft."
		),
		properties={
			"source_page_id": {
				"type": "string",
				"description": "The Builder Page id whose design to copy from.",
			},
		},
		required=["source_page_id"],
	),
	page_tool(
		"preview_page",
		run_preview_page,
		description=(
			"Render a page's draft to screenshots and return them so you can SEE what you built. "
			"Review for breakage (contrast, overlap, collapsed layout) before reporting done."
		),
	),
]

PAGE_TAKING = {t.name for t in TOOLS} - {"list_pages", "create_page"}
