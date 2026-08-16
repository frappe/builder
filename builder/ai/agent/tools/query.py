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

import re

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
				f"'{parsed.netloc}' is not this site ({site_host}) — an EXTERNAL page. Read its "
				"content with read_url (source material, not something you can edit)"
			)
		path = (parsed.path or "").strip("/")
		editor_prefix = (frappe.conf.builder_path or "builder") + "/page/"
		ref = path[len(editor_prefix) :].split("/")[0] if path.startswith(editor_prefix) else path
	if frappe.db.exists("Builder Page", ref):
		return ref, ""
	# Routes are stored both with and without a leading slash — match either.
	# Several pages can share a route (drafts of a redesign); the one serving the
	# route — published, most recently touched — is the one a reference means.
	prefer_live = "published desc, modified desc"
	bare = ref.lstrip("/")
	if name := frappe.db.get_value(
		"Builder Page", {"route": ("in", (bare, f"/{bare}"))}, order_by=prefer_live
	):
		return name, ""
	if name := frappe.db.get_value("Builder Page", {"page_title": ref}, order_by=prefer_live):
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
	components = render_components(root)
	fonts_missing = font_warning(root)
	digest = design_digest(root)
	parts = [
		f"{label} — READ-ONLY reference; its refs are NOT editable from here.",
		render_reference(root, digest),
	]
	if fonts_missing:
		parts.append(fonts_missing)
	if components:
		parts.append(components)
	if scripts := render_scripts(page_id):
		parts.append(scripts)
	# For the generation step, which sees only the brief — and briefs lose exactly
	# this (geometry, font roles). See artifact.reference_geometry.
	if (reads := getattr(ctx, "reference_reads", None)) is not None:
		sections = (f"{label}:", layout_scaffold(root), digest, fonts_missing, components)
		reads.append("\n".join(section for section in sections if section))
	return "\n".join(parts)


# A reference read is a ONE-TIME tool result, not per-round context — it affords a
# far higher complete-structure budget than the page context's limit. Real pages
# (15-50k chars) always ship whole; only stress-fixture monsters fall back to the
# outline, which loses styles and is why the threshold errs high.
REFERENCE_FULL_LIMIT = 120_000
OUTLINE_LIMIT = 20_000  # a reference outline is for rhythm, not coverage — bound the tail
SCRIPT_LIMIT = 4_000  # per attached script


def render_reference(root: dict, digest: str) -> str:
	"""Digest + structure. The digest leads so the design language survives even
	when the tree is big and only the outline ships."""
	digest = f"Design digest (base styles, with use counts):\n{digest}"
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


LAYOUT_STYLE_KEYS = (
	"position",
	"display",
	"flexDirection",
	"alignItems",
	"flexWrap",
	"gridTemplateColumns",
	"width",
	"minWidth",
	"maxWidth",
	"height",
	"minHeight",
	"flex",
	"left",
	"top",
	"zIndex",
	"overflowX",
	"overflowY",
	"transition",
)

SCAFFOLD_DEPTH = 2  # root + panes + their immediate children: the shell, not the content
SCAFFOLD_MAX_LINES = 30


def layout_styles(block: dict) -> dict:
	return {k: v for k, v in (block.get("baseStyles") or {}).items() if k in LAYOUT_STYLE_KEYS}


def strip_tags(html: str) -> str:
	return re.sub(r"<[^>]+>", " ", html or "").strip()


def layout_scaffold(root: dict) -> str:
	"""The page-level geometry as indented lines — the HOW a prose brief loses."""
	lines = []
	for block, depth in walk_blocks(root):
		if depth > SCAFFOLD_DEPTH:
			continue
		if len(lines) == SCAFFOLD_MAX_LINES:
			lines.append("…")
			break
		name = block.get("blockName") or block.get("element") or "div"
		component = f" [component {c}]" if (c := block.get("extendedFromComponent")) else ""
		detail = ", ".join(f"{k}: {v}" for k, v in layout_styles(block).items())
		lines.append(f"{'  ' * depth}- {name}{component} {{{detail}}}")
	return "\n".join(lines)


def render_components(root: dict, on_open_page: bool = False) -> str:
	"""The layout contract of each embedded component. An instance block shows only
	overrides — the component's own root styles (a fit-content rail, a fixed strip)
	are what the page must NOT fight with wrappers and constraints. Honours each
	instance's pinned version: the contract must describe what THIS page renders,
	which is not always the live component."""
	from builder.builder.component_versions import resolve_component
	from builder.builder.doctype.builder_component.builder_component import get_component_prop_values

	# Deduped by (component, pinned version) — two instances of the SAME component
	# can validly pin different versions, and each renders its own. The FIRST
	# instance of each pair also contributes its per-instance overrides: how the
	# reference ADAPTS the shared chrome is as much the contract as its layout.
	instances: dict = {}
	for block, _depth in walk_blocks(root):
		if component := block.get("extendedFromComponent"):
			instances.setdefault((component, block.get("componentVersion")), block)
	if not instances:
		return ""
	pairs = list(instances)[:8]
	names = {
		row.name: row.component_name
		for row in frappe.get_all(
			"Builder Component",
			filters={"name": ("in", {component for component, _version in pairs})},
			fields=["name", "component_name"],
		)
	}
	lines = []
	for component_id, version in pairs:
		resolved = resolve_component(component_id, version)
		if not resolved:
			continue
		block = frappe.parse_json(resolved.get("block") or "{}")
		if not isinstance(block, dict):
			continue
		classes = block.get("classes") or []
		detail = ", ".join(f"{k}: {v}" for k, v in layout_styles(block).items()) or "no layout styles"
		hooks = f" — classes {classes}" if classes else ""
		lines.append(
			f"- {component_id} ('{names.get(component_id, component_id)}'): root {{{detail}}}{hooks}"
		)
		if texts := component_texts(block):
			lines.append(f"  default content: {' · '.join(repr(t) for t in texts)}")
		if props := get_component_prop_values(block):
			lines.append(f"  props (each instance sets its own values): {props}")
		if scripts := client_script_count(block):
			lines.append(
				f"  carries {scripts} client script(s) on its blocks — behaviour/styles ship "
				"with every embed; nothing to attach page-side"
			)
		if resolved.get("component_data_script"):
			lines.append(
				"  has a server data script (runs with the instance's props, fills component.* "
				f"bindings) — read it via get_document('Builder Component', '{component_id}')"
			)
		if overrides := instance_overrides(instances[(component_id, version)]):
			owner = "this page" if on_open_page else "the reference"
			lines.append(f"  {owner}'s instance overrides: {'; '.join(overrides)}")
	if not lines:
		return ""
	if on_open_page:
		preamble = (
			"Embedded components on this page (their ROOT styles are the layout contract — a "
			"component sizes itself; do not wrap or constrain it to force layout). An instance "
			"renders the component's DEFAULT content plus the overrides below; its internal "
			"blocks appear in the tree as child_of refs, `of` naming the mirrored block. Adapt "
			"page-specific chrome through the declared props (update_block's props on the "
			"instance root) or by overriding those children:"
		)
	else:
		preamble = (
			"Embedded components (their ROOT styles are the layout contract — a component "
			"sizes itself; do not wrap or constrain it to force layout). Embedding is HALF "
			"the job: an instance renders the component's DEFAULT content until the page "
			"overrides its children, and the overrides below are how the reference makes "
			"the shared chrome its own — mirror that pattern:"
		)
	return preamble + "\n" + "\n".join(lines)


def client_script_count(block: dict) -> int:
	return sum(
		1
		for child, _depth in walk_blocks(block)
		for kind in ("js", "css")
		if (child.get("clientScript") or {}).get(kind) or (kind == "js" and child.get("blockClientScript"))
	)


def component_texts(block: dict) -> list[str]:
	"""The component's default copy — what an embedding page must override."""
	texts = []
	for child, _depth in walk_blocks(block):
		if clean := strip_tags(child.get("innerHTML")):
			texts.append(clean[:30])
		if len(texts) == 6:
			break
	return texts


def instance_overrides(instance: dict) -> list[str]:
	"""Per-instance adjustments: replaced text, hidden parts, props, attributes."""
	from builder.builder.doctype.builder_component.builder_component import get_component_prop_values

	notes = []
	if props := get_component_prop_values(instance):
		notes.append(f"props {props}")
	if root_styles := visible_styles(instance.get("baseStyles")):
		hidden = " (HIDDEN — the page suppresses this chrome and builds its own variant nearby)"
		notes.append(f"root {root_styles}{hidden if root_styles.get('display') == 'none' else ''}")
	for child, _depth in walk_blocks(instance):
		if child is instance:
			continue
		ref = child.get("referenceBlockId") or child.get("blockId")
		if text := strip_tags(child.get("innerHTML")):
			notes.append(f"{ref} text → {text[:40]!r}")
		if styles := visible_styles(child.get("baseStyles")):
			notes.append(f"{ref} {styles}")
		if attrs := child.get("attributes"):
			notes.append(f"{ref} attrs {attrs}")
		if len(notes) >= 8:
			break
	return notes[:8]


def visible_styles(styles: dict | None) -> dict:
	return {k: v for k, v in (styles or {}).items() if not k.startswith("__")}


FONT_CHECK_TIMEOUT = 3
# Wall-clock budget for ALL probes of one read TOGETHER (they run in parallel);
# families that don't answer in time are simply not judged — fail open. A
# bounded synchronous wait is the right trade here: read_page is a model-facing
# tool inside multi-second agent turns (its own YAML serialization costs more),
# and deferring the probe would drop the warning on the FIRST read of a
# reference — the read where an unresolvable font must be caught.
FONT_PROBE_BUDGET = 3
# A combined css2 request cannot replace per-family probes: multi-family mode
# answers 200 and silently DROPS unknown families.
FONT_PROBE_LIMIT = 5


def google_font_exists(family: str) -> bool:
	"""Bare probe: css2 answers 400 for a family Google Fonts does not ship.
	Raises on network trouble; caching and fail-open live in the caller."""
	from urllib.parse import quote_plus

	import requests

	return requests.head(
		f"https://fonts.googleapis.com/css2?family={quote_plus(family)}:wght@400",
		timeout=FONT_CHECK_TIMEOUT,
	).ok


def probe_google_fonts(families: list[str]) -> dict:
	"""One parallel sweep under ONE wall-clock budget: the slowest a reference
	read can stall on fonts is FONT_PROBE_BUDGET, not one timeout per family.
	Returns {family: exists} only for families that answered in time."""
	import concurrent.futures

	results: dict = {}
	pool = concurrent.futures.ThreadPoolExecutor(max_workers=len(families))
	futures = {pool.submit(google_font_exists, family): family for family in families}
	try:
		for future in concurrent.futures.as_completed(futures, timeout=FONT_PROBE_BUDGET):
			try:
				results[futures[future]] = future.result()
			except Exception:
				pass
	except concurrent.futures.TimeoutError:
		pass
	finally:
		pool.shutdown(wait=False, cancel_futures=True)
	return results


# CSS keywords that resolve in every browser — never worth probing as font names.
GENERIC_FAMILIES = {
	"serif",
	"sans-serif",
	"monospace",
	"cursive",
	"fantasy",
	"system-ui",
	"ui-sans-serif",
	"ui-serif",
	"ui-monospace",
	"inherit",
	"initial",
}

# Browser/OS-native families: not on Google Fonts, yet they render fine — a
# probe would brand them missing and push generation to replace them.
WEB_SAFE_FAMILIES = {
	"arial",
	"arial black",
	"helvetica",
	"helvetica neue",
	"georgia",
	"times",
	"times new roman",
	"courier",
	"courier new",
	"verdana",
	"tahoma",
	"trebuchet ms",
	"impact",
	"palatino",
	"palatino linotype",
	"garamond",
	"comic sans ms",
	"segoe ui",
	"lucida console",
	"lucida sans",
	"lucida sans unicode",
	"menlo",
	"monaco",
	"consolas",
	"avenir",
	"avenir next",
	"futura",
	"gill sans",
	"optima",
	"baskerville",
	"didot",
	"american typewriter",
}


def primary_family(value: str) -> str:
	"""'Inter, sans-serif' names the font 'Inter' — never probe the stack as one name."""
	return value.split(",")[0].strip().strip("'\"")


def unavailable_fonts(root: dict) -> list[str]:
	"""Families that will NOT render here: no User Font record, not on Google Fonts."""
	families = set()
	for block, _depth in walk_blocks(root):
		value = (block.get("baseStyles") or {}).get("fontFamily")
		if not value or value.startswith("var("):
			continue
		family = primary_family(value)
		if family and family.lower() not in GENERIC_FAMILIES and family.lower() not in WEB_SAFE_FAMILIES:
			families.add(family)
	if not families:
		return []
	from builder.builder.doctype.user_font.user_font import get_all_user_fonts

	user_fonts = {font.font_name for font in get_all_user_fonts()}
	missing, unknown = [], []
	for family in sorted(families - user_fonts)[:FONT_PROBE_LIMIT]:
		cached = frappe.cache().get_value(f"google_font_exists:{family}")
		if cached is None:
			unknown.append(family)
		elif cached == "0":
			missing.append(family)
	if unknown:
		results = probe_google_fonts(unknown)
		# Negatives count (and cache) only when the WHOLE sweep answered: on a
		# flaky network, or behind a proxy that 4xxs everything, a partial sweep's
		# negatives must not drive font replacement — now or on a later read.
		# Positives are safe evidence in any sweep and always cache.
		complete = len(results) == len(unknown)
		for family, exists in results.items():
			if exists or complete:
				frappe.cache().set_value(
					f"google_font_exists:{family}", "1" if exists else "0", expires_in_sec=86400
				)
		if complete:
			missing.extend(family for family, exists in results.items() if not exists)
	return sorted(missing)


def font_warning(root: dict) -> str:
	missing = unavailable_fonts(root)
	if not missing:
		return ""
	return (
		"FONT AVAILABILITY: "
		+ ", ".join(f"'{family}'" for family in missing)
		+ " does NOT resolve on this site — no User Font record here and not a Google Fonts "
		"family, so text set in it abandons the page's Inter default and falls back to the "
		"browser's own Times-like serif (the reference itself renders broken on this site). "
		"Never copy the name as-is: use the "
		"closest family that IS available (a real Google Fonts family, or an installed User "
		"Font), and tell the user this site is missing the font asset the reference names."
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
	return (
		"Attached page scripts — these often CARRY the behaviour of the page's components "
		"(a sidebar's expand, a nav's toggle). Embedding a component and attaching its "
		"companion scripts are ONE action, not optional polish: without them the chrome is "
		"dead (no hover-expand, no mobile toggle), and styling the instance to LOOK right "
		"statically does not replace the behaviour. Attach the SAME scripts verbatim "
		"(set_page_script with this exact content); never write your own replacement for "
		"behaviour you can copy, and never skip them:\n" + "\n".join(parts)
	)


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
