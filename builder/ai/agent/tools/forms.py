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

import hashlib
import json
import re

import frappe
from frappe.model import child_table_fields, default_fields

from builder.ai.agent import pending
from builder.ai.agent.registry import Tool

# Fieldtypes a public form can safely write. Select is deliberately mapped to Data:
# an HTML <select> submits its
# option's `value` attr (e.g. "breathwork"), which rarely matches the DocType's
# Select option labels ("Breathwork & Stillness") — Frappe then rejects the insert
# with a validation error. Storing dropdowns as Data accepts whatever was chosen.
SAFE_FIELDTYPES = {"Data", "Small Text", "Text", "Int", "Float", "Check", "Date", "Datetime"}

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


def form_script_name(page_id: str, doctype: str, web_form: str, selector: str) -> str:
	identity = json.dumps([page_id, web_form, selector])
	suffix = hashlib.sha256(identity.encode()).hexdigest()[:12]
	return f"Save {doctype} submissions [{suffix}]"


def connected_submission_doctype(page_id: str, selector: str = "") -> str | None:
	"""The submission DocType a form on this page already saves to, if any — read
	from the attached 'Save <doctype> submissions' client script. Lets a "where do
	my submissions go?" question be answered instead of creating a duplicate."""
	if not page_id or not frappe.db.exists("Builder Page", page_id):
		return None
	names = frappe.get_all(
		"Builder Page Client Script",
		filters={"parent": page_id, "parenttype": "Builder Page"},
		pluck="builder_script",
	)
	for name in names:
		m = re.match(r"^Save (.+) submissions(?: \[[a-f0-9]+\])?$", name or "")
		if m and frappe.db.exists("DocType", m.group(1)):
			doctype = m.group(1)
			if not selector or name == form_script_name(page_id, doctype, desk_slug(doctype), selector):
				return doctype
	return None


def missing_create_permission(doctype: str) -> str | None:
	"""What connecting a form to `doctype` would create that this user can't. Only
	Website Manager holds Web Form create, but whoever can create DocTypes can grant
	themselves any role, so either one may create the form."""
	can_create_doctype = frappe.has_permission("DocType", "create")
	if not frappe.db.exists("DocType", doctype) and not can_create_doctype:
		return "create the DocType a form saves to"
	if not frappe.db.exists("Web Form", desk_slug(doctype)) and not (
		can_create_doctype or frappe.has_permission("Web Form", "create")
	):
		return "create the Web Form a form submits through"
	return None


def request_connect_form(ctx, args: dict) -> str | None:
	"""Validate the proposal and raise the confirm card. Nothing is created until
	the user approves (see pending.apply_connect_form)."""
	if not getattr(ctx, "page_id", None):
		return "DECLINED: no page is open — build the form's page first."
	# A form here is already wired — very likely a "where do submissions go?" ask.
	# Answer with the existing DocType; don't create a duplicate (unless forced).
	selector = (args.get("form_selector") or "").strip()
	if not args.get("force_new") and (connected := connected_submission_doctype(ctx.page_id, selector)):
		return (
			f"ALREADY CONNECTED: a form on this page saves to the '{connected}' DocType — its "
			f"submissions are in Desk at /app/{desk_slug(connected)}. Do NOT create a new doctype; "
			f"just tell the user where to find the entries (give that link). Only pass force_new=true "
			f"if they explicitly want a SEPARATE, additional form."
		)
	doctype = (args.get("doctype_name") or "").strip()
	fields = [f for f in (args.get("fields") or []) if isinstance(f, dict) and f.get("fieldname")]
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
	if action := missing_create_permission(doctype):
		return pending.not_permitted(action)
	try:
		fields = normalize_fields(fields)
	except ValueError as exc:
		return f"DECLINED: {exc}"
	summary = (
		f"Create the DocType '{doctype}' ({len(fields)} field(s)) and wire this form to save "
		f"submissions to it? You'll see entries in Desk at /app/{desk_slug(doctype)}."
	)
	payload = {
		"doctype_name": doctype,
		"fields": fields,
		"page_id": ctx.page_id,
		"form_selector": selector,
	}
	pending.request_confirmation(ctx, "connect_form", summary, payload)
	return None


def normalize_field(f: dict) -> dict:
	fieldtype = f.get("fieldtype") or "Data"
	if fieldtype == "Select":
		fieldtype = "Data"
	if fieldtype not in SAFE_FIELDTYPES:
		raise ValueError(f"Unsupported form fieldtype: {fieldtype}")
	input_name = f.get("input_name") or f["fieldname"]
	out = {
		"input_name": input_name,
		"fieldname": safe_fieldname(frappe.scrub(f["fieldname"])),
		"label": f.get("label") or f["fieldname"].replace("_", " ").title(),
		"fieldtype": "Text" if f.get("multiple") else fieldtype,
		"multiple": bool(f.get("multiple")),
		"reqd": int(bool(f.get("required") or f.get("reqd"))),
	}
	return out


def normalize_fields(fields: list) -> list[dict]:
	if not all(isinstance(f, dict) and isinstance(f.get("fieldname"), str) for f in fields):
		raise ValueError("Each form field needs a fieldname.")
	normalized = [normalize_field(f) for f in fields]
	if any(not isinstance(f["input_name"], str) or not f["input_name"].strip() for f in normalized):
		raise ValueError("Each form field needs a nonempty HTML input name.")
	for key in ("fieldname", "input_name"):
		values = [f[key] for f in normalized]
		if len(values) != len(set(values)):
			raise ValueError(f"Duplicate form {key}; use one mapping per named control or group.")
	if any(not re.fullmatch(r"[a-z][a-z0-9_]*", f["fieldname"]) for f in normalized):
		raise ValueError(
			"Form fieldnames must start with a letter and contain only letters, digits, or underscores."
		)
	return normalized


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
		"Set a name on every input and provide one field mapping per name (one for a radio/checkbox group). "
		"input_name preserves the exact HTML name when fieldname differs. Use Check for a single checkbox; "
		"set multiple=true for checkbox groups or multiple selects (stored as a JSON array in Text). "
		"form_selector must match this form or its container. Ends your turn to confirm."
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
				"description": "One mapping per HTML name, including one mapping per radio/checkbox group.",
				"items": {
					"type": "object",
					"properties": {
						"fieldname": {
							"type": "string",
							"description": "DocType fieldname; input_name defaults to this exact value.",
						},
						"input_name": {
							"type": "string",
							"description": "Exact original HTML name attribute.",
						},
						"multiple": {"type": "boolean", "description": "Checkbox group or select multiple."},
						"required": {"type": "boolean"},
						"label": {"type": "string"},
						"fieldtype": {
							"type": "string",
							"description": "Data (default, also for selects), Small Text, Text, Int, Float, Check, Date, Datetime.",
						},
					},
					"required": ["fieldname"],
				},
			},
			"form_selector": {
				"type": "string",
				"description": "CSS selector of the <form> or its container block, e.g. '.reservation-form'.",
			},
			"force_new": {
				"type": "boolean",
				"description": "Only set true to add a SEPARATE form when the page already has a connected one.",
			},
		},
		"required": ["doctype_name", "fields", "form_selector"],
	},
	handler=request_connect_form,
)

TOOLS = [connect_form_tool]
