import frappe


def execute():
	"""Set Component ID"""
	component_list = frappe.get_all("Builder Component")

	for component in component_list:
		component_doc = frappe.get_doc("Builder Component", component)
		component_doc.component_id = component_doc.name
		component_doc.db_set("component_id", component_doc.name, update_modified=False)
