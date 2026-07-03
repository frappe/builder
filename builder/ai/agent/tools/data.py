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
import re

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


def get_document(ctx, args: dict) -> str:
	"""Read one document's current field values — including SINGLE settings doctypes
	(Website Settings, Builder Settings) where no name is needed. The generic reader:
	answer 'what is X' about any setting/record with this instead of a getter-per-field."""
	dt = (args.get("doctype") or "").strip()
	if not dt or not frappe.db.exists("DocType", dt):
		return json.dumps({"error": f"DocType '{dt}' not found"})
	if not frappe.has_permission(dt, "read"):
		return json.dumps({"error": f"You don't have permission to read {dt}"})
	meta = frappe.get_meta(dt)
	try:
		if meta.issingle:
			doc = frappe.get_cached_doc(dt)
		else:
			name = (args.get("name") or "").strip()
			if not name:
				return json.dumps(
					{"error": f"{dt} needs a 'name' — use list_doctypes / query_records to find one"}
				)
			if not frappe.db.exists(dt, name):
				return json.dumps({"error": f"{dt} '{name}' not found"})
			doc = frappe.get_doc(dt, name)
	except Exception as e:
		return json.dumps({"error": str(e)})

	data = doc.as_dict()
	wanted = args.get("fields")
	if isinstance(wanted, list) and wanted:
		data = {f: data.get(f) for f in wanted}
	else:
		# Drop internal fields and child tables so the read stays legible + cheap.
		data = {k: v for k, v in data.items() if not k.startswith("_") and not isinstance(v, list)}
	# A page's block JSON would only truncate into an unparseable stub here — point at
	# the tool that renders it properly instead.
	if dt == "Builder Page":
		for key in ("blocks", "draft_blocks"):
			if data.get(key):
				data[key] = f"<use read_page('{doc.name}') to see the page structure>"
	# Bound long values (e.g. a raw HTML blob) so a read never blows the context.
	data = {k: (v[:1000] + "…" if isinstance(v, str) and len(v) > 1000 else v) for k, v in data.items()}
	return frappe.as_json(data)


# A data script POPULATES `data` — it must never mutate documents. A script that
# writes would run its mutation on EVERY page render (and is how a weaker model
# once smuggled "doc.published = 0; doc.save()" past the missing lifecycle tool).
DATA_SCRIPT_FORBIDDEN = (
	".save(",
	".insert(",
	".submit(",
	".delete(",
	"delete_doc",
	"set_value",
	"ignore_permissions",
)

# `data` is a frappe._dict: assigning data.items stores the key, but READING
# data.items returns the dict's built-in method (real attributes beat __getattr__)
# — "TypeError: 'builtin_function_or_method' object is not iterable" at render.
RESERVED_DATA_KEYS_RE = re.compile(r"\bdata\.(items|keys|values|get|update|copy|pop|clear|setdefault)\b")

# safe_exec has no __import__ — any import statement dies with ImportError at render.
IMPORT_RE = re.compile(r"^\s*(import|from)\s+\w", re.MULTILINE)


def write_page_data_script(ctx, args: dict) -> str:
	"""Save the server-side Python that populates `data` for the current page (e.g.
	`data.events = frappe.get_list("Event", ...)`). Runs in the frappe safe_exec
	sandbox at render time; bind blocks/repeaters to the keys it sets."""
	if not ctx.page_id:
		return "No page in context to attach a data script to."
	script = args.get("script") or ""
	if any(token in script for token in DATA_SCRIPT_FORBIDDEN):
		return (
			"FAILED: a page data script only READS data into `data` for bindings — it runs on "
			"every page render and must never save/insert/delete documents. To publish, "
			"unpublish, or delete pages use manage_pages; for settings use the settings tools."
		)
	if match := RESERVED_DATA_KEYS_RE.search(script):
		return (
			f"FAILED: 'data.{match.group(1)}' is a reserved dict method name — reading it back "
			"returns the method, not your records, and the page errors at render "
			"(''builtin_function_or_method' is not iterable'). Use a descriptive key instead, "
			"e.g. data.products or data.merch_items."
		)
	if IMPORT_RE.search(script):
		return (
			"FAILED: the data script runs in Frappe's safe_exec sandbox — IMPORT statements are "
			"not allowed (ImportError at render). A curated namespace is already available: "
			"frappe.get_all / frappe.get_list / frappe.db.get_value / frappe.db.count, and date/"
			"format helpers under frappe.utils (frappe.utils.getdate, frappe.utils.formatdate(d, "
			"'MMM dd'), frappe.utils.now_datetime, frappe.utils.add_days, frappe.utils.fmt_money). "
			"Rewrite without imports."
		)
	frappe.db.set_value("Builder Page", ctx.page_id, "page_data_script", script)
	frappe.db.commit()
	return "Saved the page data script (runs server-side to populate `data`)."


# --- writes (terminal, confirm-gated) -----------------------------------


def request_create_doctype(ctx, args: dict) -> str | None:
	"""Returning a string DECLINES the proposal (no confirm card) and feeds the
	reason back to the model — e.g. proposing 'Event', a built-in Frappe doctype."""
	name = (args.get("name") or "").strip()
	fields = args.get("fields") or []
	if not name or not fields:
		return "DECLINED: a doctype proposal needs a name and at least one field."
	if frappe.db.exists("DocType", name):
		return (
			f"DECLINED: DocType '{name}' already EXISTS — do not create it. Either reuse it with its "
			f"REAL fieldnames (schema follows), or propose a different name (e.g. 'Community {name}').\n"
			f"{get_doctype_schema(ctx, {'doctype': name})}"
		)
	summary = f"Create a new DocType '{name}' with {len(fields)} field(s)?"
	pending.request_confirmation(ctx, "create_doctype", summary, {"name": name, "fields": fields})
	return None


def request_seed_sample_data(ctx, args: dict) -> str | None:
	doctype = (args.get("doctype") or "").strip()
	rows = [r for r in (args.get("rows") or []) if isinstance(r, dict)]
	if not doctype or not frappe.db.exists("DocType", doctype):
		return f"DECLINED: DocType '{doctype}' does not exist — create it first (create_doctype)."
	if not rows:
		return "DECLINED: no rows to insert."
	# Rows with made-up fieldnames would insert as empty records — bounce them back
	# with the real schema instead of putting a doomed proposal in front of the user.
	valid = {f.fieldname for f in frappe.get_meta(doctype).fields}
	unknown = sorted({key for row in rows for key in row} - valid)
	if unknown:
		return (
			f"DECLINED: '{doctype}' has no field(s) {unknown}. Re-map your rows to its real "
			f"fieldnames: {sorted(valid)}."
		)
	summary = f"Insert {len(rows)} sample record(s) into '{doctype}'?"
	pending.request_confirmation(ctx, "seed_sample_data", summary, {"doctype": doctype, "rows": rows})
	return None


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

get_document_tool = Tool(
	name="get_document",
	side="server",
	description=(
		"Read the CURRENT values of any document or Single settings doctype — the generic way "
		"to answer 'what is X'. Examples: get_document('Website Settings') for the site home page "
		"and brand; get_document('Builder Settings') for global head/body/script HTML; "
		"get_document('Builder Page', <page_id>) for a page's route/SEO/settings; "
		"get_document('Builder Variable', <name>) for a theme token's value. Omit 'name' for Single "
		"doctypes. Pass 'fields' to read only some. Discover doctypes/fields with list_doctypes / "
		"get_doctype_schema."
	),
	parameters={
		"type": "object",
		"properties": {
			"doctype": {"type": "string"},
			"name": {"type": "string", "description": "Document name; omit for Single doctypes."},
			"fields": {
				"type": "array",
				"items": {"type": "string"},
				"description": "Optional subset of fields.",
			},
		},
		"required": ["doctype"],
	},
	handler=get_document,
)

write_page_data_script_tool = Tool(
	name="write_page_data_script",
	side="server",
	description=(
		"Set the current page's server-side data script (Python). Use it to populate `data` "
		"for data-driven pages, e.g. `data.events = frappe.get_list('Event', fields=['title','date'], "
		"filters={'published': 1})`. Then bind blocks/repeaters to the keys you set. Runs in the "
		"safe_exec SANDBOX at render time: NO import statements — frappe.get_all/get_list/get_doc, "
		"frappe.db.get_value/count, and frappe.utils date/format helpers (getdate, formatdate, "
		"now_datetime, add_days, fmt_money) are preinjected. Keys must be descriptive names "
		"(data.products) — NEVER dict method names like data.items/keys/values/get (they shadow "
		"and break the render). READ-ONLY: never save/insert/delete documents here."
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
	get_document_tool,
	write_page_data_script_tool,
	create_doctype_tool,
	seed_sample_data_tool,
]
