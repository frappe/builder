# Copyright (c) 2026, Frappe Technologies Pvt Ltd and contributors
# For license information, please see license.txt

"""Doctypes an extension creates while the editor runs.

Always `custom: 1`. Frappe refuses a non-custom doctype outside developer mode
(`doctype.py:334`), and a custom one writes no files, so what an extension makes
lives in the database and can be dropped again.

The permission floor is Frappe's own and nothing here lifts it: inserting a
`DocType` needs create permission on `DocType`, which is System Manager. An
extension asking a page editor to model a table simply fails, and that is the
right answer rather than a bug.

Ownership is a record, not a naming convention. `Builder Extension Resource`
says which extension made which doctype, so a creating extension can be given a
full grant with no second question.

Ownership names the extension, not one user's installation of it. A doctype holds
the site's data, so it outlives the person who installed the extension, and the
next person to install it owns what the first one made.
"""

import frappe
from frappe import _

from builder.extensions.access import assert_extension_access
from builder.extensions.data import (
	ACCESS_FIELDS,
	ALLOWED,
	assert_grant,
	describe_grant,
	forget_grant,
	upsert_grant,
)
from builder.extensions.resources import (
	RESOURCE_DOCTYPE,
	find_resource,
	forget_resource,
	list_resources,
	record_resource,
)

MODULE = "Builder"

# The roles a new doctype is usable by. Both are what this app already grants on
# its own records (`builder_token.json`). Neither is a custom role nor an
# automatic one, so a System Manager may add them to a custom doctype
# (`doctype.py:2037`); only the Administrator could add the rest.
DEFAULT_ROLES = ("System Manager", "Website Manager")

# What an extension may say instead of Frappe's own naming_rule vocabulary. A
# short list, because a naming rule that goes wrong cannot be changed later
# without renaming every document.
NAMING_RULES = {
	"hash": {"naming_rule": "Random"},
	"autoincrement": {"naming_rule": "Autoincrement"},
	"prompt": {"naming_rule": "Set by user"},
}

# Field types that need nothing but themselves. A Table needs a child doctype, a
# Dynamic Link needs a companion field, and a Button needs client code, so none
# of the three is here yet.
ALLOWED_FIELDTYPES = {
	"Data",
	"Small Text",
	"Text",
	"Long Text",
	"Text Editor",
	"Markdown Editor",
	"HTML Editor",
	"Code",
	"JSON",
	"Int",
	"Float",
	"Currency",
	"Percent",
	"Rating",
	"Duration",
	"Check",
	"Select",
	"Link",
	"Date",
	"Datetime",
	"Time",
	"Attach",
	"Attach Image",
	"Color",
	"Phone",
	"Password",
	"Read Only",
	"Signature",
	"Barcode",
	"Geolocation",
	"Section Break",
	"Column Break",
	"Tab Break",
	"Heading",
}

FIELD_KEYS = (
	"fieldname",
	"label",
	"fieldtype",
	"options",
	"reqd",
	"unique",
	"default",
	"in_list_view",
	"in_standard_filter",
	"read_only",
	"description",
	"precision",
)


@frappe.whitelist(methods=["POST"])
def create_doctype(
	extension: str,
	doctype: str,
	fields: list[dict] | None = None,
	naming: str = "hash",
	istable: bool = False,
) -> dict:
	"""A new custom doctype, owned by this extension.

	The extension is given a full grant on it in the same call. It made the
	table, so asking whether it may read the table would be a question with one
	sensible answer.
	"""
	installation = assert_extension_access(extension, "schema.write", writes=RESOURCE_DOCTYPE)
	rows = read_fields(fields)
	if not rows:
		frappe.throw(_("A doctype needs at least one field."))

	document = frappe.get_doc(
		{
			"doctype": "DocType",
			"name": read_doctype_name(doctype),
			"module": MODULE,
			"custom": 1,
			"istable": int(bool(istable)),
			"fields": rows,
			"permissions": [] if istable else default_permissions(),
			**read_naming(naming),
		}
	).insert()

	record_resource(extension, "DocType", document.name)
	grant_everything(installation, document.name)
	return describe_doctype(document.name)


@frappe.whitelist()
def get_doctype(extension: str, doctype: str) -> dict:
	"""The field list of a doctype this extension may read."""
	installation = assert_extension_access(extension, "schema.write")
	assert_grant(installation, extension, doctype, "read")
	return describe_doctype(doctype)


@frappe.whitelist(methods=["POST"])
def update_doctype(extension: str, doctype: str, fields: list[dict] | None = None) -> dict:
	"""Adds fields, and updates the ones already there by fieldname.

	Never removes a field the call leaves unmentioned. That is the rule
	`set_extension_tokens` and `record_extension_grant` follow, and it matters
	more here: a removed field drops a column and the data in it.
	"""
	assert_extension_access(extension, "schema.write")
	assert_owned(extension, doctype)

	document = frappe.get_doc("DocType", doctype)
	existing = {row.fieldname: row for row in document.fields}

	for row in read_fields(fields):
		found = existing.get(row["fieldname"])
		if found:
			found.update(row)
		else:
			document.append("fields", row)

	document.save()
	return describe_doctype(doctype)


@frappe.whitelist(methods=["POST"])
def delete_doctype(extension: str, doctype: str) -> None:
	"""Drops a doctype this extension made, and the table under it.

	The grant goes with it. Frappe does not stop a `DocType` being deleted while
	a Link names it, so the row would otherwise outlive the doctype — and a
	doctype created later under the same name would inherit that grant without
	anyone being asked.
	"""
	installation = assert_extension_access(extension, "schema.write")
	assert_owned(extension, doctype)

	frappe.delete_doc("DocType", doctype)
	forget_resource(extension, "DocType", doctype)
	forget_grant(installation, doctype)


@frappe.whitelist()
def list_doctypes(extension: str) -> list[dict]:
	"""Every doctype this extension made, whether or not it still exists."""
	assert_extension_access(extension, "schema.write")

	names = list_resources(extension, "DocType")
	return [{"doctype": name, "exists": bool(frappe.db.exists("DocType", name))} for name in names]


def read_doctype_name(doctype: str) -> str:
	"""A title, not a path. The name becomes a table name, so it stays plain."""
	name = (doctype or "").strip()
	if not name or not all(part.isalnum() for part in name.replace("-", " ").split()):
		frappe.throw(_("A doctype name holds letters, digits, spaces and hyphens."))
	if frappe.db.exists("DocType", name):
		frappe.throw(_("A doctype called {0} already exists.").format(name))
	return name


def read_naming(naming: str) -> dict:
	if naming not in NAMING_RULES:
		frappe.throw(_("Naming must be one of: {0}").format(", ".join(sorted(NAMING_RULES))))
	return NAMING_RULES[naming]


def read_fields(fields: list[dict] | None) -> list[dict]:
	return [read_field(field) for field in (fields or [])]


def read_field(field: dict) -> dict:
	fieldtype = field.get("fieldtype")
	if fieldtype not in ALLOWED_FIELDTYPES:
		frappe.throw(
			_("{0} is not a field type an extension can add. Allowed: {1}").format(
				fieldtype, ", ".join(sorted(ALLOWED_FIELDTYPES))
			)
		)

	row = {key: field[key] for key in FIELD_KEYS if field.get(key) is not None}
	# a layout break carries no data, so it needs no fieldname of its own
	if not row.get("fieldname") and "Break" not in fieldtype and fieldtype != "Heading":
		frappe.throw(_("Every field needs a fieldname."))

	row["fieldtype"] = fieldtype
	return row


def default_permissions() -> list[dict]:
	return [{"role": role, "read": 1, "write": 1, "create": 1, "delete": 1} for role in DEFAULT_ROLES]


def describe_doctype(doctype: str) -> dict:
	meta = frappe.get_meta(doctype)
	return {
		"doctype": meta.name,
		"istable": bool(meta.istable),
		"fields": [
			{key: field.get(key) for key in ("fieldname", "label", "fieldtype", "options", "reqd")}
			for field in meta.fields
		],
	}


def grant_everything(installation: str, doctype: str) -> None:
	"""A full grant on a doctype this extension just made, with no prompt.

	For this installation alone. Another user installing the same extension is
	asked the ordinary way, because they did not make this table.
	"""
	upsert_grant(installation, doctype, dict.fromkeys(ACCESS_FIELDS.values(), ALLOWED))


def assert_owned(extension: str, doctype: str) -> None:
	"""Only the extension that made a doctype may change or drop it.

	A grant is not enough. A grant says the user let this extension read and
	write **documents**, which is not the same as letting it change the shape of
	the table or drop it.
	"""
	if find_resource(extension, "DocType", doctype):
		return

	frappe.throw(
		_('"{0}" did not create {1}, so it cannot change it.').format(extension, doctype),
		frappe.PermissionError,
	)
