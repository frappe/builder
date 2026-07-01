"""Data-layer tools — let the agent build DATA-DRIVEN pages.

Reads (list_doctypes / get_doctype_schema / query_records) are `side="server"`:
the loop runs them and feeds the result back so the model grounds its page data
scripts in the site's REAL schema instead of guessing. write_page_data_script is
also server-side (it edits one page — safe, reversible). Creating a doctype and
seeding sample data are hard to reverse, so they are `side="terminal"` and go
through the confirm-gate (builder/ai/agent/pending.py) — the user approves before
anything is written.
"""

import json
import logging

import frappe

from builder.ai.agent import pending
from builder.ai.agent.registry import Tool

logger = frappe.logger("builder.ai.agent.data")
logger.setLevel(logging.INFO)

STRUCTURAL_FIELDTYPES = {"Section Break", "Column Break", "Tab Break", "HTML"}


# --- reads (server, auto) -----------------------------------------------


def list_doctypes(ctx, args: dict) -> str:
	filters: dict = {"istable": 0}
	if args.get("module"):
		filters["module"] = args["module"]
	if args.get("custom") is not None:
		filters["custom"] = 1 if args["custom"] else 0
	search = (args.get("search") or "").strip()
	if search:
		filters["name"] = ["like", f"%{search}%"]
	rows = frappe.get_all(
		"DocType",
		filters=filters,
		fields=["name", "module", "custom"],
		order_by="modified desc",
		limit=min(int(args.get("limit") or 40), 100),
	)
	return json.dumps([dict(r) for r in rows])


def get_doctype_schema(ctx, args: dict) -> str:
	dt = (args.get("doctype") or "").strip()
	if not dt or not frappe.db.exists("DocType", dt):
		return json.dumps({"error": f"DocType '{dt}' not found"})
	meta = frappe.get_meta(dt)
	fields = [
		{"fieldname": f.fieldname, "label": f.label, "fieldtype": f.fieldtype, "options": f.options}
		for f in meta.fields
		if f.fieldtype not in STRUCTURAL_FIELDTYPES
	]
	return json.dumps({"doctype": dt, "fields": fields})


def query_records(ctx, args: dict) -> str:
	dt = (args.get("doctype") or "").strip()
	if not dt or not frappe.db.exists("DocType", dt):
		return json.dumps({"error": f"DocType '{dt}' not found"})
	fields = args.get("fields") or ["name"]
	filters = args.get("filters") if isinstance(args.get("filters"), dict) else {}
	limit = min(int(args.get("limit") or 20), 100)
	try:
		rows = frappe.get_all(dt, filters=filters, fields=fields, limit=limit)
	except Exception as e:
		return json.dumps({"error": str(e)})
	return json.dumps([dict(r) for r in rows], default=str)


def write_page_data_script(ctx, args: dict) -> str:
	"""Save the server-side Python that populates `data` for the current page (e.g.
	`data.events = frappe.get_list("Event", ...)`). Runs in the frappe safe_exec
	sandbox at render time; bind blocks/repeaters to the keys it sets."""
	if not ctx.page_id:
		return "No page in context to attach a data script to."
	frappe.db.set_value("Builder Page", ctx.page_id, "page_data_script", args.get("script") or "")
	frappe.db.commit()
	return "Saved the page data script (runs server-side to populate `data`)."


# --- writes (terminal, confirm-gated) -----------------------------------


def request_create_doctype(ctx, args: dict) -> None:
	name = (args.get("name") or "").strip()
	fields = args.get("fields") or []
	summary = f"Create a new DocType '{name}' with {len(fields)} field(s)?"
	pending.request_confirmation(ctx, "create_doctype", summary, {"name": name, "fields": fields})


def request_seed_sample_data(ctx, args: dict) -> None:
	doctype = (args.get("doctype") or "").strip()
	rows = args.get("rows") or []
	summary = f"Insert {len(rows)} sample record(s) into '{doctype}'?"
	pending.request_confirmation(ctx, "seed_sample_data", summary, {"doctype": doctype, "rows": rows})


# --- schemas ------------------------------------------------------------

FIELD_SCHEMA = {
	"type": "object",
	"properties": {
		"fieldname": {"type": "string", "description": "snake_case field name."},
		"label": {"type": "string"},
		"fieldtype": {
			"type": "string",
			"description": "Frappe fieldtype: Data, Text, Small Text, Int, Float, Check, Date, Datetime, Select, Link, Attach Image, etc.",
		},
		"options": {
			"type": "string",
			"description": "For Link (target DocType) or Select (newline-separated choices).",
		},
	},
	"required": ["fieldname", "fieldtype"],
}

list_doctypes_tool = Tool(
	name="list_doctypes",
	side="server",
	description="List DocTypes in the site (the data model). Filter by module, custom-only, or a name search. Use this to discover what data already exists before building data-driven pages.",
	parameters={
		"type": "object",
		"properties": {
			"search": {"type": "string", "description": "Substring to match in the DocType name."},
			"module": {"type": "string"},
			"custom": {"type": "boolean", "description": "True = only user/custom DocTypes."},
			"limit": {"type": "integer"},
		},
		"required": [],
	},
	handler=list_doctypes,
)

get_doctype_schema_tool = Tool(
	name="get_doctype_schema",
	side="server",
	description="Return a DocType's fields (name, type, options). Call before writing a page data script or seeding data so you use real field names.",
	parameters={
		"type": "object",
		"properties": {"doctype": {"type": "string"}},
		"required": ["doctype"],
	},
	handler=get_doctype_schema,
)

query_records_tool = Tool(
	name="query_records",
	side="server",
	description="Fetch records from a DocType (like frappe.get_all) to see real data. Provide fields and optional filters.",
	parameters={
		"type": "object",
		"properties": {
			"doctype": {"type": "string"},
			"fields": {"type": "array", "items": {"type": "string"}},
			"filters": {"type": "object", "description": 'Field→value filters, e.g. {"published": 1}.'},
			"limit": {"type": "integer"},
		},
		"required": ["doctype"],
	},
	handler=query_records,
)

write_page_data_script_tool = Tool(
	name="write_page_data_script",
	side="server",
	description=(
		"Set the current page's server-side data script (Python). Use it to populate `data` "
		"for data-driven pages, e.g. `data.events = frappe.get_list('Event', fields=['title','date'], "
		"filters={'published': 1})`. Then bind blocks/repeaters to the keys you set. Runs in the "
		"safe_exec sandbox at render time."
	),
	parameters={
		"type": "object",
		"properties": {"script": {"type": "string", "description": "The full Python data script."}},
		"required": ["script"],
	},
	handler=write_page_data_script,
)

create_doctype_tool = Tool(
	name="create_doctype",
	side="terminal",
	description=(
		"Propose a NEW DocType (custom, created at runtime) to hold structured site data — e.g. "
		"Event, Product, Team Member, Testimonial. Ends your turn and asks the user to confirm "
		"before anything is created. After it exists you can seed_sample_data and query it from a "
		"page data script. Prefer reusing an existing DocType (list_doctypes) when one fits."
	),
	parameters={
		"type": "object",
		"properties": {
			"name": {"type": "string", "description": "Human DocType name, e.g. 'Event'."},
			"fields": {"type": "array", "items": FIELD_SCHEMA},
		},
		"required": ["name", "fields"],
	},
	handler=request_create_doctype,
)

seed_sample_data_tool = Tool(
	name="seed_sample_data",
	side="terminal",
	description=(
		"Propose inserting sample records into a DocType so data-driven pages render with real "
		"content instead of empty states. Ends your turn and asks the user to confirm. Each row is "
		"an object of field→value matching the DocType's schema (call get_doctype_schema first)."
	),
	parameters={
		"type": "object",
		"properties": {
			"doctype": {"type": "string"},
			"rows": {"type": "array", "items": {"type": "object"}},
		},
		"required": ["doctype", "rows"],
	},
	handler=request_seed_sample_data,
)

TOOLS = [
	list_doctypes_tool,
	get_doctype_schema_tool,
	query_records_tool,
	write_page_data_script_tool,
	create_doctype_tool,
	seed_sample_data_tool,
]
