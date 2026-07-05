"""Settings & theme tools.

Page-level settings (SEO/meta/lang/custom HTML) and theme variables are safe and
reversible, so they are `side="server"` and apply immediately. Site-wide settings
(global script/style/head/body HTML), the home page, and publishing affect every
visitor and are hard to undo — those are `side="terminal"` and go through the
confirm-gate (builder/ai/agent/pending.py); the user approves before they apply.
"""

import re

import frappe

from builder.ai.agent import pending
from builder.ai.agent.registry import Tool

PAGE_SETTING_FIELDS = {
	"page_title",
	"meta_description",
	"meta_image",
	"canonical_url",
	"language",
	"head_html",
	"body_html",
	"disable_indexing",
}


# --- page + theme (server, auto) ----------------------------------------


def set_page_settings(ctx, args: dict) -> str:
	if not ctx.page_id:
		return "No page in context."
	updates = {f: args[f] for f in PAGE_SETTING_FIELDS if f in args and args[f] is not None}
	if args.get("route"):
		route = args["route"].strip().strip("/")
		taken = frappe.db.get_value("Builder Page", {"route": route, "name": ("!=", ctx.page_id)})
		if taken:
			return f"FAILED: route '/{route}' is already used by page {taken} — pick another."
		updates["route"] = route
	if not updates:
		return "No recognised settings to update."
	if "route" in updates:
		# A route change must run the doc lifecycle (dynamic-route detection,
		# website cache clear) or the new URL won't resolve until a manual clear.
		doc = frappe.get_doc("Builder Page", ctx.page_id)
		doc.update(updates)
		doc.save()
	else:
		frappe.db.set_value("Builder Page", ctx.page_id, updates)
	frappe.db.commit()
	emit_refetch(ctx, "page")
	return f"Updated page settings: {', '.join(updates)}."


def emit_refetch(ctx, *resources: str) -> None:
	"""Tell any open editor to refetch state this tool changed OUTSIDE the block
	ops it mirrors (theme variables, evaluated page data, page doc fields) — the
	canvas loads these once at editor start and would otherwise show stale state
	until a manual refresh."""
	if ctx is not None and hasattr(ctx, "emit"):
		ctx.emit("refetch", resources=list(resources))


def clean_variable_id(raw: str) -> str:
	"""A Builder Token's doc name doubles as its CSS custom-property name, so it
	must be a valid css ident: lowercase, [a-z0-9_-] only."""
	return re.sub(r"[^a-z0-9_-]+", "-", (raw or "").strip().lower()).strip("-")


def set_design_token(ctx, args: dict) -> str:
	"""Create or update a site theme token (Builder Token). The CSS handle is
	var(--<doc name>); token_name is only the human label. An explicit `id`
	becomes the doc name, so the caller knows the handle before creating it. The
	result names the exact handle so the model references something that resolves."""
	label = (args.get("token_name") or "").strip().lstrip("-")
	value = (args.get("value") or "").strip()
	if not label or not value:
		return "token_name and value are required."
	token_type = args.get("type") if args.get("type") in ("Color", "Dimension", "Font") else "Color"
	if token_type == "Font":
		# A Font token's value is a bare family name — a stack or var() here would
		# break resolution at every font-loading site.
		value = value.split(",")[0].strip().strip("'\"")
		if not value or value.startswith("var("):
			return "FAILED: a Font token's value must be a bare font family name, e.g. 'Fraunces'."
	fields = {
		"type": token_type,
		"value": value,
		"dark_value": (args.get("dark_value") or "").strip() if token_type == "Color" else "",
	}
	wanted_id = clean_variable_id(args.get("id") or "")
	# The model may pass the label OR the id/handle it saw in query_records.
	existing = (
		(wanted_id and frappe.db.exists("Builder Token", wanted_id))
		or frappe.db.exists("Builder Token", label)
		or frappe.db.exists("Builder Token", {"token_name": label})
	)
	if existing:
		doc = frappe.get_doc("Builder Token", existing)
		doc.update(fields)
		# Full save (not db.set_value) so on_update busts the rendered-CSS cache.
		doc.save(ignore_permissions=True)
		frappe.db.commit()
		emit_refetch(ctx, "variables")
		return f"Updated theme variable '{doc.token_name}' — reference it in styles as var(--{doc.name})."
	doc = frappe.get_doc(
		{"doctype": "Builder Token", "token_name": label, "group": "Brand", **fields}
		# set_name survives naming (insert clears doc.name before autoname runs),
		# so the caller can know the var(--<id>) handle before the doc exists.
	).insert(ignore_permissions=True, set_name=wanted_id or None)
	frappe.db.commit()
	emit_refetch(ctx, "variables")
	return (
		f"Created theme variable '{label}'. Reference it in styles EXACTLY as var(--{doc.name}) — "
		f"'{label}' is only the display label, so var(--{label}) will NOT resolve."
	)


# --- sensitive (terminal, confirm-gated) --------------------------------


def request_set_home_page(ctx, args: dict) -> None:
	route = (args.get("route") or "").strip()
	pending.request_confirmation(ctx, "home_page", f"Set the site home page to '{route}'?", {"route": route})


def request_edit_global_settings(ctx, args: dict) -> None:
	payload = {f: args[f] for f in pending.GLOBAL_SETTING_FIELDS if f in args and args[f] is not None}
	summary = f"Update site-wide settings ({', '.join(payload) or 'none'})? These load on EVERY page."
	pending.request_confirmation(ctx, "global_settings", summary, payload)


def request_publish_site(ctx, args: dict) -> None:
	folder = None
	if ctx.page_id:
		folder = frappe.db.get_value("Builder Page", ctx.page_id, "project_folder")
	if not folder:
		# fall back to a folder passed explicitly (site flow)
		folder = (args.get("folder") or "").strip()
	if not folder:
		ctx.emit(
			"clarify",
			question="This page isn't part of a site folder, so there's nothing to publish as a site.",
			options=[],
		)
		return
	count = frappe.db.count("Builder Page", {"project_folder": folder})
	pending.request_confirmation(
		ctx, "publish_site", f"Publish all {count} page(s) in this site?", {"folder": folder}
	)


set_page_settings_tool = Tool(
	name="set_page_settings",
	side="server",
	description="Update the current page's SEO/meta and page-level settings (title, URL route, meta description, meta image, canonical URL, language, custom head/body HTML, disable indexing). Applies immediately.",
	parameters={
		"type": "object",
		"properties": {
			"page_title": {"type": "string"},
			"route": {
				"type": "string",
				"description": "The page's URL path, e.g. 'bakery' or 'menu/drinks' (no leading slash needed).",
			},
			"meta_description": {"type": "string"},
			"meta_image": {"type": "string"},
			"canonical_url": {"type": "string"},
			"language": {"type": "string"},
			"head_html": {"type": "string"},
			"body_html": {"type": "string"},
			"disable_indexing": {"type": "boolean"},
		},
		"required": [],
	},
	handler=set_page_settings,
)

set_design_token_tool = Tool(
	name="set_design_token",
	side="server",
	description=(
		"Create or update a design token (Builder Token) — the site's design system. "
		"Colors, font families, and dimensions (spacing/radius) all restyle the whole "
		"site from one place. The result names the exact CSS handle to use in styles — "
		"var(--<id>). Pass an explicit `id` (e.g. 'acme-ink', 'acme-font-heading', "
		"'acme-space-section') to CHOOSE that handle upfront, so you can write "
		"var(--acme-ink) in briefs and styles you compose in the same turn. type is "
		"Color, Font (value = bare family name), or Dimension; give a dark_value for colours."
	),
	parameters={
		"type": "object",
		"properties": {
			"token_name": {
				"type": "string",
				"description": "Human label, e.g. Brand Primary.",
			},
			"id": {
				"type": "string",
				"description": (
					"Optional explicit handle id: lowercase letters/digits/hyphens, unique and "
					"brand-prefixed (e.g. 'acme-ink'). Becomes the <id> in var(--<id>). Omit to "
					"get a generated uuid handle."
				),
			},
			"value": {"type": "string"},
			"dark_value": {"type": "string"},
			"type": {"type": "string", "enum": ["Color", "Dimension", "Font"]},
		},
		"required": ["token_name", "value"],
	},
	handler=set_design_token,
)

set_home_page_tool = Tool(
	name="set_home_page",
	side="terminal",
	description="Propose making a route the site's home page (served at /). SENSITIVE — ends your turn and asks the user to confirm before changing the global setting.",
	parameters={
		"type": "object",
		"properties": {"route": {"type": "string"}},
		"required": ["route"],
	},
	handler=request_set_home_page,
)

edit_global_settings_tool = Tool(
	name="edit_global_settings",
	side="terminal",
	description="Propose site-wide code that loads on EVERY page: global script (JS), style (CSS), head_html, body_html. SENSITIVE — ends your turn and asks the user to confirm before applying.",
	parameters={
		"type": "object",
		"properties": {
			"script": {"type": "string"},
			"style": {"type": "string"},
			"head_html": {"type": "string"},
			"body_html": {"type": "string"},
		},
		"required": [],
	},
	handler=request_edit_global_settings,
)

publish_site_tool = Tool(
	name="publish_site",
	side="terminal",
	description="Propose publishing every page in this site (makes them live). SENSITIVE — ends your turn and asks the user to confirm.",
	parameters={"type": "object", "properties": {}, "required": []},
	handler=request_publish_site,
)

TOOLS = [
	set_page_settings_tool,
	set_design_token_tool,
	set_home_page_tool,
	edit_global_settings_tool,
	publish_site_tool,
]
