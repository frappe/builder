"""Page client-script tools.

`set_page_script` and `update_script` are client-side in the editor (the
frontend creates / updates the Builder Client Script and tracks it for undo),
but they also carry a handler: HEADLESS turns (dashboard chat + sub-agents)
have no browser, so the loop runs the handler instead — same outcome, applied
server-side. `get_page_scripts` is server-side everywhere: the loop runs it and
feeds the result back so the model can read existing code before editing it.
"""

import json
import logging

import frappe

from builder.ai.agent.registry import Tool

logger = frappe.logger("builder.ai.agent.scripts")
logger.setLevel(logging.INFO)

LIVE_NOTE = (
	" This is live: the published page runs it now, while block edits wait for Publish, "
	"so tell the user it is already live."
)


def page_scripts(page_id: str, script_type: str | None = None) -> list[dict]:
	"""The client scripts attached to a page — shared by get_page_scripts (this
	page) and read_page (a reference page, whose look may live in its CSS)."""
	script_names = frappe.db.get_all(
		"Builder Page Client Script",
		filters={"parent": page_id, "parenttype": "Builder Page"},
		pluck="builder_script",
	)
	if not script_names:
		return []
	filters: dict = {"name": ["in", script_names]}
	if script_type:
		filters["script_type"] = script_type
	scripts = frappe.db.get_all(
		"Builder Client Script",
		filters=filters,
		fields=["name", "script_type", "script"],
	)
	return [{"script_name": s.name, "script_type": s.script_type, "script": s.script} for s in scripts]


def fetch_page_scripts(ctx, args: dict) -> str:
	"""Return the scripts attached to ctx.page_id as a JSON string."""
	if not ctx.page_id:
		return json.dumps([])
	try:
		return json.dumps(page_scripts(ctx.page_id, args.get("script_type")))
	except Exception as e:
		logger.warning(f"fetch_page_scripts failed: {e}")
		return json.dumps([])


def apply_set_page_script(ctx, args: dict) -> str:
	"""Headless twin of the editor's set_page_script apply (toolDispatch.ts): create
	the Builder Client Script (model's descriptive name when free) and attach it."""
	from builder.ai.agent.tree import validate_script

	if not ctx.page_id:
		return "FAILED: no page is open."
	if (verdict := validate_script(args)) != "Applied.":
		return verdict
	script_type = args.get("script_type") or "JavaScript"
	name = (args.get("name") or "").strip()[:120]
	doc_fields = {
		"doctype": "Builder Client Script",
		"script_type": script_type,
		"script": args.get("script") or "",
	}
	if name and frappe.db.exists("Builder Client Script", name):
		name = f"{name}-{frappe.generate_hash(length=5)}"
	doc = frappe.get_doc({**doc_fields, **({"name": name} if name else {})}).insert(ignore_permissions=True)
	page = frappe.get_doc("Builder Page", ctx.page_id)
	page.append("client_scripts", {"builder_script": doc.name})
	page.save(ignore_permissions=True)
	# The created name rides the op back to the canvas (see SCRIPT_TWIN_TOOLS
	# mirroring in the loop) so its script list / undo tracking pick it up.
	args["script_name"] = doc.name
	return f"Created {script_type} script '{doc.name}' and attached it to the page.{LIVE_NOTE}"


def apply_attach_page_script(ctx, args: dict) -> str:
	"""Headless twin of the editor's attach_page_script apply: link an EXISTING
	Builder Client Script doc to this page. Shared on purpose — one doc drives
	every page attached to it, so the site's behaviour stays editable in one place."""
	if not ctx.page_id:
		return "FAILED: no page is open."
	name = (args.get("script_name") or "").strip()
	if not name or not frappe.db.exists("Builder Client Script", name):
		return (
			f"FAILED: script '{name}' not found — use the exact script name from "
			"read_page's script listing or get_page_scripts."
		)
	page = frappe.get_doc("Builder Page", ctx.page_id)
	doc = frappe.db.get_value("Builder Client Script", name, ["script_type", "script"], as_dict=True)
	# The content rides the op to the canvas so its script list picks it up.
	args["script_type"] = doc.script_type
	args["script"] = doc.script
	if any(row.builder_script == name for row in page.get("client_scripts") or []):
		return f"Script '{name}' is already attached to this page."
	page.append("client_scripts", {"builder_script": name})
	page.save(ignore_permissions=True)
	return (
		f"Attached shared {doc.script_type} script '{name}'. It is the SAME doc the other page "
		"uses — editing it changes every page it is attached to; to diverge later, create a "
		f"copy with set_page_script instead.{LIVE_NOTE}"
	)


def apply_update_script(ctx, args: dict) -> str:
	"""Headless twin of the editor's update_script apply. Only a script attached to
	the open page: the turn's revert snapshot covers no other."""
	from builder.ai.agent.tree import validate_script

	name = (args.get("script_name") or "").strip()
	attached = {"parent": ctx.page_id, "parenttype": "Builder Page", "builder_script": name}
	if not (name and ctx.page_id and frappe.db.exists("Builder Page Client Script", attached)):
		return (
			f"FAILED: script '{name}' is not attached to this page. Call get_page_scripts and use "
			"its exact script_name."
		)
	if (verdict := validate_script(args)) != "Applied.":
		return verdict
	doc = frappe.get_doc("Builder Client Script", name)
	doc.script = args.get("script") or ""
	if args.get("script_type"):
		doc.script_type = args["script_type"]
	# A full save, never db.set_value: on_update rewrites the minified public file
	# the published page serves and bumps its cache-busting URL — a bare column
	# write leaves every published page running the OLD script.
	doc.save(ignore_permissions=True)
	return f"Updated script '{name}'.{LIVE_NOTE}"


def apply_detach_page_script(ctx, args: dict) -> str:
	"""Unlink a script from the open page, like the editor's Remove: the doc stays, so
	other pages using it keep working and the turn's revert can link it back."""
	name = (args.get("script_name") or "").strip()
	page = frappe.get_doc("Builder Page", ctx.page_id) if ctx.page_id else None
	rows = [row for row in (page.get("client_scripts") or []) if row.builder_script == name] if page else []
	if not rows:
		return (
			f"FAILED: script '{name}' is not attached to this page. Call get_page_scripts and use "
			"its exact script_name."
		)
	for row in rows:
		page.remove(row)
	page.save(ignore_permissions=True)
	return f"Removed script '{name}' from this page; the script itself is kept.{LIVE_NOTE}"


set_page_script = Tool(
	name="set_page_script",
	side="client",
	handler=apply_set_page_script,  # used by HEADLESS turns only; the editor applies client-side
	description=(
		"Create a JavaScript or CSS script and attach it to the page, for page-level behaviour "
		"block styles can't express. CSS and JS are SEPARATE scripts: stylesheet content "
		"(reveal/hover classes, @keyframes) goes in a script_type='CSS' script, never a <style> "
		"tag built from JS. Target elements by a hook you give them in the same turn (a class, "
		"or [id=x] for one element) via edit_page, never by a block's @ref: it is not in the "
		"published DOM."
	),
	parameters={
		"type": "object",
		"properties": {
			"script": {
				"type": "string",
				"description": "The full JavaScript or CSS source code to add to the page.",
			},
			"script_type": {
				"type": "string",
				"enum": ["JavaScript", "CSS"],
				"description": "Whether this is a JavaScript or CSS script. Defaults to 'JavaScript'.",
			},
			"name": {
				"type": "string",
				"description": (
					"What it does, 2-4 words in Title Case ('Mobile Nav Toggle'), shown in the page's "
					"script list; never a generic 'Script'."
				),
			},
		},
		"required": ["script", "name"],
	},
)

attach_page_script = Tool(
	name="attach_page_script",
	side="client",
	handler=apply_attach_page_script,  # the loop applies script ops server-side
	description=(
		"Attach an EXISTING client script doc (one another page of this site already uses) to "
		"this page — the right way to reuse a reference page's motion/behaviour. The script "
		"stays SHARED: one doc drives every page it is attached to, so a later edit rethemes "
		"them all together. Pass the exact script name from read_page's script listing. Attach "
		"whenever the script is cleanly reusable here (it targets class hooks this page also "
		"carries); only when it does work unrelated to this page (sections this page doesn't "
		"have, other-page logic) copy just the relevant part into a new set_page_script instead."
	),
	parameters={
		"type": "object",
		"properties": {
			"script_name": {
				"type": "string",
				"description": (
					"The exact script doc name from read_page/get_page_scripts "
					"(e.g. 'Studio Motion' or 'BSC-00001'). Never invent this value."
				),
			},
		},
		"required": ["script_name"],
	},
)

update_script = Tool(
	name="update_script",
	side="client",
	handler=apply_update_script,  # the loop applies script ops server-side
	description=(
		"Replace the source code of an existing page script. "
		"You MUST call get_page_scripts first and copy the exact 'script_name' value "
		"from that response — do not guess or invent a name. "
		"Same targeting rule as set_page_script: select by a class/attrs.id hook you add "
		"via edit_page, never by a block's @ref/blockId (not in the "
		"published DOM)."
	),
	parameters={
		"type": "object",
		"properties": {
			"script_name": {
				"type": "string",
				"description": "The exact 'script_name' value returned by get_page_scripts (e.g. 'BSC-00001'). Never invent this value.",
			},
			"script": {
				"type": "string",
				"description": "The new full source code that replaces the existing script content.",
			},
			"script_type": {
				"type": "string",
				"enum": ["JavaScript", "CSS"],
				"description": "Change the script type. Omit to keep the existing type.",
			},
		},
		"required": ["script_name", "script"],
	},
)

detach_page_script = Tool(
	name="detach_page_script",
	side="client",
	handler=apply_detach_page_script,  # the loop applies script ops server-side
	description=(
		"Remove a script from this page, like the editor's Remove action: it stops running here "
		"and the script doc is kept for any other page using it. This is how a script comes off "
		"a page; never blank one with update_script. Remove only scripts you added in this chat "
		"or ones the user named."
	),
	parameters={
		"type": "object",
		"properties": {
			"script_name": {
				"type": "string",
				"description": "The exact 'script_name' value returned by get_page_scripts. Never invent this value.",
			},
		},
		"required": ["script_name"],
	},
)

get_page_scripts = Tool(
	name="get_page_scripts",
	side="server",
	description=(
		"Fetch the JavaScript and/or CSS scripts attached to this page. "
		"Call this before using update_script so you can read the existing code. "
		"Pass script_type to fetch only one kind."
	),
	parameters={
		"type": "object",
		"properties": {
			"script_type": {
				"type": "string",
				"enum": ["JavaScript", "CSS"],
				"description": "Return only scripts of this type. Omit to return all scripts.",
			},
		},
		"required": [],
	},
	handler=fetch_page_scripts,
)

TOOLS = [set_page_script, attach_page_script, update_script, detach_page_script, get_page_scripts]
