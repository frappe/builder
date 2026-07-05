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


def fetch_page_scripts(ctx, args: dict) -> str:
	"""Return the scripts attached to ctx.page_id as a JSON string."""
	page_id = ctx.page_id
	script_type = args.get("script_type")
	if not page_id:
		return json.dumps([])
	try:
		script_names = frappe.db.get_all(
			"Builder Page Client Script",
			filters={"parent": page_id, "parenttype": "Builder Page"},
			pluck="builder_script",
		)
		if not script_names:
			return json.dumps([])
		filters: dict = {"name": ["in", script_names]}
		if script_type:
			filters["script_type"] = script_type
		scripts = frappe.db.get_all(
			"Builder Client Script",
			filters=filters,
			fields=["name", "script_type", "script"],
		)
		return json.dumps(
			[{"script_name": s.name, "script_type": s.script_type, "script": s.script} for s in scripts]
		)
	except Exception as e:
		logger.warning(f"fetch_page_scripts failed: {e}")
		return json.dumps([])


def apply_set_page_script(ctx, args: dict) -> str:
	"""Headless twin of the editor's set_page_script apply (toolDispatch.ts): create
	the Builder Client Script (model's descriptive name when free) and attach it."""
	from builder.ai.agent.tree import validate_script

	if not ctx.page_id:
		return "FAILED: no page is open — open_page or create_page first."
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
	frappe.db.commit()
	# The created name rides the op back to the canvas (see SCRIPT_TWIN_TOOLS
	# mirroring in the loop) so its script list / undo tracking pick it up.
	args["script_name"] = doc.name
	return f"Created {script_type} script '{doc.name}' and attached it to the page."


def apply_update_script(ctx, args: dict) -> str:
	"""Headless twin of the editor's update_script apply."""
	from builder.ai.agent.tree import validate_script

	name = (args.get("script_name") or "").strip()
	if not name or not frappe.db.exists("Builder Client Script", name):
		return f"FAILED: script '{name}' not found — call get_page_scripts and use its exact script_name."
	if (verdict := validate_script(args)) != "Applied.":
		return verdict
	values = {"script": args.get("script") or ""}
	if args.get("script_type"):
		values["script_type"] = args["script_type"]
	frappe.db.set_value("Builder Client Script", name, values)
	frappe.db.commit()
	return f"Updated script '{name}'."


set_page_script = Tool(
	name="set_page_script",
	side="client",
	handler=apply_set_page_script,  # used by HEADLESS turns only; the editor applies client-side
	description=(
		"Create a new JavaScript or CSS client script and attach it to the page. "
		"Use this to add event listeners, animations, dynamic behaviour, fetch calls, "
		"or any page-level code that cannot be expressed via block styles alone. "
		"CSS and JS are SEPARATE scripts: put stylesheet content (reveal/hover classes, "
		"@keyframes, cursors) in a script_type='CSS' script and behaviour in a "
		"'JavaScript' one — never inject a <style> tag from JS "
		"(document.createElement('style') is always wrong; make two calls instead). "
		"To target an element, in the SAME turn give it a hook — a class (preferred) in "
		"'classes', or attrs.id for a single unique element — via update_block or "
		"run_python, and select that. Do NOT select by a block's 'ref'/blockId "
		"(editor handle): it is not in the published DOM and matches nothing on the live page."
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
					"A short, descriptive name for the script (2–4 words, Title Case) saying what it "
					"does — e.g. 'Confetti On Load', 'Mobile Nav Toggle', 'Hero Parallax'. Shown in the "
					"page's script list. Do NOT use generic names like 'Script' or 'JavaScript'."
				),
			},
		},
		"required": ["script", "name"],
	},
)

update_script = Tool(
	name="update_script",
	side="client",
	handler=apply_update_script,  # used by HEADLESS turns only; the editor applies client-side
	description=(
		"Replace the source code of an existing page script. "
		"You MUST call get_page_scripts first and copy the exact 'script_name' value "
		"from that response — do not guess or invent a name. "
		"Same targeting rule as set_page_script: select by a class/attrs.id hook you add "
		"via update_block or run_python, never by a block's 'ref'/blockId (not in the "
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

TOOLS = [set_page_script, update_script, get_page_scripts]
