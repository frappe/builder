# Copyright (c) 2026, Frappe Technologies Pvt Ltd and contributors
# For license information, please see license.txt

"""Builder Extension Grant → Builder Extension DocType Grant.

A capability is granted too, so the name says which grant this is. The rename
keeps the table, its rows and its unique index.
"""

import frappe

OLD_DOCTYPE = "Builder Extension Grant"
NEW_DOCTYPE = "Builder Extension DocType Grant"


def execute():
	# guard on the table, not the DocType row: rename_doc cannot rename onto a
	# table that a re-synced old model left behind
	if frappe.db.table_exists(NEW_DOCTYPE) or not frappe.db.exists("DocType", OLD_DOCTYPE):
		return
	frappe.rename_doc("DocType", OLD_DOCTYPE, NEW_DOCTYPE, force=True)
