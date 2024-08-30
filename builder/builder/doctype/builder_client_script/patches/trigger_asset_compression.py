import frappe


def execute():
	for doc in frappe.get_all("Builder Client Script"):
		script_doc = frappe.get_doc("Builder Client Script", doc.name)
		try:
			script_doc.on_update()  # this will compress script and save it to file
		except Exception as e:
			print(f"Error compressing script for {script_doc.name}: {e}")
			continue
