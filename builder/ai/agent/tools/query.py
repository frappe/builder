"""Selector tools: read block trees, on this page and across the site.

`query_blocks` is server-side — it walks the turn-start page tree the frontend
shipped and returns the matching blocks' refs (+ element and full text). This
grounds bulk edits: instead of scanning the page context and hoping it catches
every block, the model asks for the exact set ("all text", "all h2", "every
button") and gets it deterministically, then applies one `update_blocks` call.
Text is returned in FULL — translation/rewrite needs every block's real copy.

`read_page` crosses pages: it reads ANOTHER Builder Page's tree as a read-only
reference, so "match the rest of the site" and "use this page as reference" are
answered from the site's real design instead of the model's priors.
"""

import frappe

from builder.ai.agent.registry import Tool
from builder.ai.agent.selectors import (
	block_text,
	design_digest,
	find_block,
	match_block,
	render_skeleton,
	walk_blocks,
)
from builder.ai.block_codec import BlockCodec
from builder.utils import to_compact_yaml


def run_query_blocks(ctx, args: dict) -> str:
	root = ctx.page_root()
	if root is None:
		return "The page is empty — nothing to select."

	scope = args.get("within")
	start = root
	if scope:
		start = find_block(root, scope)
		if start is None:
			return f"No block found with ref {scope}."

	element = args.get("element")
	text_only = bool(args.get("text_only"))
	contains = args.get("contains")
	class_name = args.get("class_name")

	matches = []
	for block, _depth in walk_blocks(start):
		if match_block(
			block,
			element=element,
			text_only=text_only,
			contains=contains,
			class_name=class_name,
		):
			ref = block.get("blockId")
			if not ref:
				continue
			entry = {"ref": ref, "el": block.get("element") or "div"}
			if text := block_text(block):
				entry["text"] = text  # full text, never truncated — needed for translate/rewrite
			if classes := block.get("classes"):
				entry["classes"] = classes
			matches.append(entry)

	if not matches:
		return "No blocks matched. Loosen the filters or check the page outline."
	header = f"{len(matches)} block(s) matched:\n"
	return header + to_compact_yaml(matches)


query_blocks = Tool(
	name="query_blocks",
	side="server",
	handler=run_query_blocks,
	description=(
		"Find blocks on the current page by structural filters, returning each match's "
		"'ref' (its block_id), element, and FULL text. Use this before any change that "
		"affects MANY blocks — translate the page, restyle every button, rewrite all "
		"headings — so you act on the complete, exact set instead of guessing from the "
		"outline. Filters AND together. Then apply the change with ONE update_blocks call."
	),
	parameters={
		"type": "object",
		"properties": {
			"element": {
				"type": "string",
				"description": "Match only this HTML tag (e.g. 'h2', 'button', 'p').",
			},
			"text_only": {
				"type": "boolean",
				"description": "Match only text-bearing blocks (headings, paragraphs, labels, buttons, list items…). Use this for translate/rewrite-all requests.",
			},
			"contains": {
				"type": "string",
				"description": "Match only blocks whose text contains this substring (case-insensitive).",
			},
			"class_name": {
				"type": "string",
				"description": "Match only blocks carrying this CSS class.",
			},
			"within": {
				"type": "string",
				"description": "Limit the search to the subtree under this block's ref. Defaults to the whole page.",
			},
		},
	},
)


def run_read_block(ctx, args: dict) -> str:
	root = ctx.page_root()
	if root is None:
		return "The page is empty."
	ref = args.get("block_id")
	block = find_block(root, ref) if ref else None
	if block is None:
		return f"No block found with ref {ref}."
	detail = to_compact_yaml(BlockCodec.compress(block, depth=0, task_tier="complex"))
	return f"Block {ref} (full styles/attributes/children):\n{detail}"


read_block = Tool(
	name="read_block",
	side="server",
	handler=run_read_block,
	description=(
		"Return a block's FULL detail — its styles, attributes, text, and child subtree — "
		"by ref. Use this on a large page (where the context is only an outline) before "
		"editing a block whose current styles you need to see, or to match the styling of an "
		"existing section."
	),
	parameters={
		"type": "object",
		"properties": {
			"block_id": {"type": "string", "description": "The ref of the block to inspect."},
		},
		"required": ["block_id"],
	},
)

MAX_PAGE_READS_PER_TURN = 3  # each read is thousands of tokens — bound a sweep of the whole site


def resolve_page_reference(ref: str) -> tuple[str | None, str]:
	"""A page named ANY way users name pages — doc id, route, page title, or a
	pasted URL (editor link or published address) — resolved to a Builder Page id.
	Uniform addressing keeps ONE general read tool instead of a tool per shape.
	Returns (page_id, "") or (None, why)."""
	from urllib.parse import urlparse

	ref = (ref or "").strip().strip("<>")
	if not ref:
		return None, "pass a page id, route, page title, or a URL of this site"
	if "://" in ref:
		parsed = urlparse(ref)
		site_host = urlparse(frappe.utils.get_url()).netloc
		if parsed.netloc and parsed.netloc != site_host:
			return None, (
				f"'{parsed.netloc}' is not this site ({site_host}) — an external page can't be "
				"read with your tools; ask the user to paste its content or a screenshot"
			)
		path = (parsed.path or "").strip("/")
		editor_prefix = (frappe.conf.builder_path or "builder") + "/page/"
		ref = path[len(editor_prefix) :].split("/")[0] if path.startswith(editor_prefix) else path
	if frappe.db.exists("Builder Page", ref):
		return ref, ""
	# Routes are stored both with and without a leading slash — match either.
	bare = ref.lstrip("/")
	for route in (bare, f"/{bare}"):
		if name := frappe.db.get_value("Builder Page", {"route": route}):
			return name, ""
	if name := frappe.db.get_value("Builder Page", {"page_title": ref}):
		return name, ""
	return None, f"no page on this site has id, route, or title '{ref}'"


def run_read_page(ctx, args: dict) -> str:
	page_id, why = resolve_page_reference(args.get("page_id") or "")
	if page_id is None:
		return (
			f"FAILED: {why} — list the site's pages with "
			"query_records('Builder Page', fields=['name', 'route', 'page_title'])."
		)
	if page_id == ctx.page_id:
		return "That's the page you have open — its structure is already in your context."
	if ctx.page_read_count >= MAX_PAGE_READS_PER_TURN:
		return "Page-read limit reached for this turn — work with the references you have."
	ctx.page_read_count += 1

	from builder.ai.page_writer import load_page_root

	title, route = frappe.db.get_value("Builder Page", page_id, ["page_title", "route"])
	label = f"Page '{title or page_id}' (route: {route})"
	root = load_page_root(page_id)
	if root is None:
		return f"{label} has no blocks yet."
	parts = [
		f"{label} — READ-ONLY reference; its refs are NOT editable from here.",
		render_reference(root),
	]
	if scripts := render_scripts(page_id):
		parts.append(scripts)
	return "\n".join(parts)


# A reference read is a ONE-TIME tool result, not per-round context — it affords a
# far higher complete-structure budget than the page context's limit. Real pages
# (15-50k chars) always ship whole; only stress-fixture monsters fall back to the
# outline, which loses styles and is why the threshold errs high.
REFERENCE_FULL_LIMIT = 120_000
OUTLINE_LIMIT = 20_000  # a reference outline is for rhythm, not coverage — bound the tail
SCRIPT_LIMIT = 4_000  # per attached script


def render_reference(root: dict) -> str:
	"""Digest + structure. The digest leads so the design language survives even
	when the tree is big and only the outline ships."""
	digest = f"Design digest (base styles, with use counts):\n{design_digest(root)}"
	full = to_compact_yaml(BlockCodec.compress(root, depth=0, task_tier="complex"))
	if len(full) <= REFERENCE_FULL_LIMIT:
		return f"{digest}\n\nFull structure and styles (YAML):\n{full}"
	outline = render_skeleton(root)
	if len(outline) > OUTLINE_LIMIT:
		kept = outline[:OUTLINE_LIMIT].rsplit("\n", 1)[0]
		dropped = outline.count("\n") - kept.count("\n")
		outline = f"{kept}\n… ({dropped} more blocks — the rhythm above is representative)"
	return (
		f"{digest}\n\nThe page is extremely large, so its structure is an OUTLINE (styles "
		"omitted — the digest above carries them):\n" + outline
	)


def render_scripts(page_id: str) -> str:
	"""A reference page's look can live in its attached CSS as much as its blocks."""
	from builder.ai.agent.tools.scripts import page_scripts

	parts = []
	for script in page_scripts(page_id):
		body = script["script"] or ""
		if len(body) > SCRIPT_LIMIT:
			body = body[:SCRIPT_LIMIT] + "\n… (truncated)"
		parts.append(f"--- {script['script_type']} script '{script['script_name']}':\n{body}")
	if not parts:
		return ""
	return "Attached page scripts:\n" + "\n".join(parts)


read_page = Tool(
	name="read_page",
	side="server",
	handler=run_read_page,
	description=(
		"Read ANOTHER page of this site as a read-only reference: its design digest "
		"(fonts, colours, radii, section rhythm) plus its block structure. THE way to "
		"understand the site's existing design language before matching it — when the "
		"user names a reference page or asks that this page fit the rest of the site, "
		"read the reference FIRST and carry its exact values (font families, hexes, "
		"var(--id) handles, section structure) into your brief or edits. For a normal-"
		"size page the YAML is complete — exact enough to rebuild sections from "
		"(add_block) when the user wants a page copied. You cannot edit another page's "
		"blocks directly."
	),
	parameters={
		"type": "object",
		"properties": {
			"page_id": {
				"type": "string",
				"description": (
					"The page, named any way the user named it: its id ('page-f664795a'), "
					"its route, its title, or a pasted URL of this site (an editor link or "
					"a published address)."
				),
			},
		},
		"required": ["page_id"],
	},
)

TOOLS = [query_blocks, read_block, read_page]
