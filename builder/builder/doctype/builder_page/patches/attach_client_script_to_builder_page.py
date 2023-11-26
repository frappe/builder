
import frappe

def execute():
	"""Attach Client Script to Builder Page"""
	for builder_page in frappe.db.sql("""select name, client_script, style from `tabBuilder Page`""", as_dict=True):
		if builder_page.client_script:
			if script_name := frappe.db.exists("Builder Client Script", {"script": builder_page.client_script}):
				script_doc = frappe.get_doc("Builder Client Script", script_name)
			else:
				script_doc = frappe.get_doc({
					"doctype": "Builder Client Script",
					"script_type": "JavaScript",
					"script": builder_page.client_script
				}).insert(ignore_permissions=True)
			frappe.get_doc({
				"doctype": "Builder Page Client Script",
				"parent": builder_page.name,
				"builder_script": script_doc.name,
				"parentfield": "client_scripts",
				"parenttype": "Builder Page"
			}).insert(ignore_permissions=True)
		elif builder_page.style:
			if script_name := frappe.db.exists("Builder Client Script", {"script": builder_page.style}):
				style_doc = frappe.get_doc("Builder Client Script", script_name)
			else:
				style_doc = frappe.get_doc({
					"doctype": "Builder Client Script",
					"script_type": "CSS",
					"script": builder_page.style
				}).insert(ignore_permissions=True)
			frappe.get_doc({
				"doctype": "Builder Page Client Script",
				"parent": builder_page.name,
				"builder_script": style_doc.name,
				"parentfield": "client_scripts",
				"parenttype": "Builder Page"
			}).insert(ignore_permissions=True)
