import frappe


def execute():
	frappe.db.add_index("Web Page View", ["creation", "is_unique", "path"])
