import frappe
from frappe.model.rename_doc import rename_doc


def execute():
	if frappe.db.exists("DocType", "Web Page Component") and not frappe.db.exists(
		"DocType", "Builder Component"
	):
		rename_doc("DocType", "Web Page Component", "Builder Component")
