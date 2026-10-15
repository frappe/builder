"""Extension doctypes made before page editors got access: give them the roles a new one gets.

A patch runs as the Administrator, so it can add every role that writes a Builder Page.
"""

import frappe

from builder.extensions.resources import RESOURCE_DOCTYPE
from builder.extensions.schema import default_permissions


def execute():
	names = frappe.get_all(RESOURCE_DOCTYPE, filters={"resource_type": "DocType"}, pluck="resource_name")
	for name in dict.fromkeys(names):
		if frappe.db.exists("DocType", name) and not frappe.db.get_value("DocType", name, "istable"):
			add_missing_roles(frappe.get_doc("DocType", name))


def add_missing_roles(document) -> None:
	existing = {row.role for row in document.permissions if not row.permlevel}
	missing = [row for row in default_permissions() if row["role"] not in existing]
	if not missing:
		return
	for row in missing:
		document.append("permissions", row)
	document.save()
