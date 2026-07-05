"""Connect a page form to real data — the 'make this form actually save' tool.

A form on a published Builder page is public (a guest fills it), so it can't
insert into a DocType directly. The safe, code-free path is Frappe's built-in
Web Form: its `accept` endpoint is guest-allowed, rate-limited, field-whitelisted,
and inserts with ignore_permissions — the Web Form is the trusted boundary, so
the submission DocType needs NO guest permission.

`connect_form` (confirm-gated) provisions the whole chain on approval:
  1. a private submission DocType (System Manager only — no guest read),
  2. a Web Form bound to it (login_required off, published),
  3. a page client script that POSTs the form's fields to the accept endpoint.
The user then reads submissions in Desk at /app/<doctype>.
"""

import frappe
from frappe.model import child_table_fields, default_fields

from builder.ai.agent import pending
from builder.ai.agent.registry import Tool

# Fieldtypes a public form can safely write. Anything else (Link, Table, Attach…)
# is coerced to Data so a guest submission can't reach into other doctypes/files.
SAFE_FIELDTYPES = {"Data", "Small Text", "Text", "Int", "Float", "Check", "Select", "Date", "Datetime"}

# Fieldnames Frappe reserves (every doc has `name`, `owner`, `parent`, …). A form
# input called "name" would otherwise crash DocType creation ("Fieldname name is
# restricted"), so the DocType field is renamed (`name` → `name_field`) while the
# input keeps its own name attribute — the wiring script maps between them.
RESERVED_FIELDNAMES = (
	set(default_fields)
	| set(child_table_fields)
	| {
		"name",
		"parent",
		"idx",
		"naming_series",
		"amended_from",
		"workflow_state",
	}
)


def safe_fieldname(fieldname: str) -> str:
	return f"{fieldname}_field" if fieldname in RESERVED_FIELDNAMES else fieldname


def request_connect_form(ctx, args: dict) -> str | None:
	"""Validate the proposal and raise the confirm card. Nothing is created until
	the user approves (see pending.apply_connect_form)."""
	if not getattr(ctx, "page_id", None):
		return "DECLINED: no page is open — build the form's page first."
	doctype = (args.get("doctype_name") or "").strip()
	fields = [f for f in (args.get("fields") or []) if isinstance(f, dict) and f.get("fieldname")]
	selector = (args.get("form_selector") or "").strip()
	if not doctype or not fields or not selector:
		return (
			"DECLINED: connect_form needs doctype_name, at least one field, and form_selector "
			'(the CSS selector of the <form> or its container — set name="<fieldname>" on each input first).'
		)
	if frappe.db.exists("DocType", doctype) and not is_builder_submission_doctype(doctype):
		return (
			f"DECLINED: '{doctype}' already exists and isn't a Builder submission doctype — pick a new "
			f"name (e.g. '{doctype} Submission') so real data isn't touched."
		)
	summary = (
		f"Create the DocType '{doctype}' ({len(fields)} field(s)) and wire this form to save "
		f"submissions to it? You'll see entries in Desk at /app/{desk_slug(doctype)}."
	)
	payload = {
		"doctype_name": doctype,
		"fields": [normalize_field(f) for f in fields],
		"page_id": ctx.page_id,
		"form_selector": selector,
	}
	pending.request_confirmation(ctx, "connect_form", summary, payload)
	return None


def normalize_field(f: dict) -> dict:
	fieldtype = f.get("fieldtype") if f.get("fieldtype") in SAFE_FIELDTYPES else "Data"
	input_name = frappe.scrub(f["fieldname"])  # the form input's `name` attribute
	out = {
		"input_name": input_name,
		"fieldname": safe_fieldname(input_name),  # DocType fieldname (reserved names remapped)
		"label": f.get("label") or f["fieldname"].replace("_", " ").title(),
		"fieldtype": fieldtype,
	}
	if fieldtype == "Select" and f.get("options"):
		out["options"] = f["options"]
	return out


def is_builder_submission_doctype(name: str) -> bool:
	row = frappe.db.get_value("DocType", name, ["custom", "module"], as_dict=True)
	return bool(row and row.custom and row.module == "Builder")


def desk_slug(doctype: str) -> str:
	return frappe.scrub(doctype).replace("_", "-")


connect_form_tool = Tool(
	name="connect_form",
	side="terminal",
	description=(
		"Make a form on the page actually SAVE its submissions to the database. Use this whenever "
		"you build a real form that collects user input (contact, booking, signup, waitlist, RSVP). "
		"Under the hood it creates a private DocType for the submissions, a guest-safe Web Form, and a "
		"script that sends the form's fields to it — the owner reads entries in Desk at /app/<doctype>. "
		'BEFORE calling: give the form a container with a stable class and set name="<fieldname>" on '
		"every input/select the form has (matching the fieldnames you pass here). Ends your turn to ask "
		"the user to confirm creating the DocType."
	),
	parameters={
		"type": "object",
		"properties": {
			"doctype_name": {
				"type": "string",
				"description": "Human name for the submissions DocType, e.g. 'Stillpoint Reservation'.",
			},
			"fields": {
				"type": "array",
				"description": "One entry per form input. fieldname must equal the input's name attribute.",
				"items": {
					"type": "object",
					"properties": {
						"fieldname": {
							"type": "string",
							"description": "snake_case; equals the input's name attr.",
						},
						"label": {"type": "string"},
						"fieldtype": {
							"type": "string",
							"description": "Data (default), Small Text, Text, Int, Float, Check, Select, Date, Datetime.",
						},
						"options": {
							"type": "string",
							"description": "For Select: newline-separated choices.",
						},
					},
					"required": ["fieldname"],
				},
			},
			"form_selector": {
				"type": "string",
				"description": "CSS selector of the <form> or its container block, e.g. '.reservation-form'.",
			},
		},
		"required": ["doctype_name", "fields", "form_selector"],
	},
	handler=request_connect_form,
)

TOOLS = [connect_form_tool]
