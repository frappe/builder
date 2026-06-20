"""Page client-script tools.

`set_page_script` and `update_script` are client-side (the frontend creates /
updates the Builder Client Script and tracks it for undo). `get_page_scripts`
is server-side: the loop runs it and feeds the result back to the model so it
can read existing code before editing it.
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


set_page_script = Tool(
	name="set_page_script",
	side="client",
	description=(
		"Create a new JavaScript or CSS client script and attach it to the page. "
		"Use this to add event listeners, animations, dynamic behaviour, fetch calls, "
		"or any page-level code that cannot be expressed via block styles alone. "
		"To target an element, in the SAME turn give it a hook via update_block — a class "
		"(preferred) in 'classes', or attrs.id for a single unique element — and select "
		"that. Do NOT select by a block's 'ref' (editor handle): it is not in the published "
		"DOM and matches nothing on the live page."
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
	description=(
		"Replace the source code of an existing page script. "
		"You MUST call get_page_scripts first and copy the exact 'script_name' value "
		"from that response — do not guess or invent a name. "
		"Same targeting rule as set_page_script: select by a class/attrs.id hook you add "
		"via update_block, never by a block's 'ref' (not in the published DOM)."
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
