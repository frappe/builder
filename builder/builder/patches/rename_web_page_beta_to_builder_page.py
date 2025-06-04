import frappe
from frappe.model.rename_doc import rename_doc


def execute():
	if frappe.db.exists("DocType", "Web Page Beta") and not frappe.db.exists("DocType", "Builder Page"):
		rename_doc("DocType", "Web Page Beta", "Builder Page")
