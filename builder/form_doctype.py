import re

import frappe
from frappe.model import child_table_fields, default_fields
from frappe.model.base_document import RESERVED_KEYWORDS

# what a form's inputs can be saved as; anything else is saved as Data
FIELDTYPES = {
	"Data",
	"Small Text",
	"Text",
	"Int",
	"Float",
	"Check",
	"Select",
	"Date",
	"Time",
	"Datetime",
	"Password",
	"Color",
}

# every doc has these (`name`, `owner`, `parent`, …), so an input called "name" can't be a field
# of that name: it is saved as `name_field` instead, and the input renamed to match
RESERVED_FIELDNAMES = (
	set(default_fields)
	| set(child_table_fields)
	| RESERVED_KEYWORDS
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


def create_form_doctype(doctype: str, fields: list[dict]) -> list[str]:
	"""Make a private DocType for a form's submissions, with a field for each of its inputs.
	Returns each input's fieldname, which the input is named after so the two match."""
	docfields = [get_docfield(field, index) for index, field in enumerate(fields)]
	frappe.get_doc(
		{
			"doctype": "DocType",
			"name": doctype,
			"module": "Builder",
			"custom": 1,
			"naming_rule": "Random",
			"autoname": "hash",
			# inputs that share a name (a group of checkboxes) submit as one field
			"fields": list({docfield["fieldname"]: docfield for docfield in docfields}.values()),
			# a guest saves through the form, so no one else needs to read the submissions
			"permissions": [{"role": "System Manager", "read": 1, "write": 1, "create": 1, "delete": 1}],
		}
	).insert()
	return [docfield["fieldname"] for docfield in docfields]


def get_docfield(field: dict, index: int) -> dict:
	name = field.get("fieldname") or field.get("label") or ""
	# Frappe drops or refuses other characters, and the input is renamed to the stored name
	fieldname = safe_fieldname(
		re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")[:64] or f"field_{index + 1}"
	)
	fieldtype = field.get("fieldtype") if field.get("fieldtype") in FIELDTYPES else "Data"
	return {
		"fieldname": fieldname,
		"label": field.get("label") or (name or fieldname).replace("_", " ").title(),
		"fieldtype": fieldtype,
		"options": field.get("options") if fieldtype in ("Data", "Select") else None,
		"reqd": 1 if field.get("reqd") else 0,
		"in_list_view": 1,
	}
