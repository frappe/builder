# Copyright (c) 2026, Frappe Technologies Pvt Ltd and contributors
# For license information, please see license.txt

"""Give each access of an extension grant its own answer.

A grant held three checks, and one `denied` flag for the whole doctype. Read,
write and delete now each hold allowed, denied or not asked.

A check that was set becomes allowed. A denial stood for every access the user
had not allowed, so each of those becomes denied. Frappe keeps the column of a
removed field, so the old values are still there to read.
"""

import frappe

GRANT_DOCTYPE = "Builder Extension Grant"
OLD_FIELDS = {"can_read": "read_access", "can_write": "write_access", "can_delete": "delete_access"}


def execute():
	if not all(frappe.db.has_column(GRANT_DOCTYPE, field) for field in [*OLD_FIELDS, "denied"]):
		return

	grant = frappe.qb.DocType(GRANT_DOCTYPE)
	columns = [grant.name, grant.denied, *(grant[field] for field in OLD_FIELDS)]
	for row in frappe.qb.from_(grant).select(*columns).run(as_dict=True):
		refused = "denied" if row.denied else "not asked"
		answers = {new: "allowed" if row[old] else refused for old, new in OLD_FIELDS.items()}
		frappe.db.set_value(GRANT_DOCTYPE, row.name, answers, update_modified=False)
