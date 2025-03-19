import frappe


def execute():
	"""Attach Client Script to Builder Page"""
	for builder_page in frappe.db.sql(
		"""select name, client_script, style from `tabBuilder Page`""", as_dict=True
	):
		if builder_page.client_script:
			script_doc = get_or_create_builder_script(
				"Builder Client Script", builder_page.client_script, "JavaScript"
			)
			create_builder_page_client_script(builder_page.name, script_doc.name)
		elif builder_page.style:
			style_doc = get_or_create_builder_script("Builder Client Script", builder_page.style, "CSS")
			create_builder_page_client_script(builder_page.name, style_doc.name)


def get_or_create_builder_script(doctype, script, script_type):
	script_name = frappe.db.exists(doctype, {"script": script})
	if script_name:
		return frappe.get_doc(doctype, script_name)
	else:
		return frappe.get_doc({"doctype": doctype, "script_type": script_type, "script": script}).insert(
			ignore_permissions=True
		)


def create_builder_page_client_script(
	parent, builder_script, parentfield="client_scripts", parenttype="Builder Page"
):
	frappe.get_doc(
		{
			"doctype": "Builder Page Client Script",
			"parent": parent,
			"builder_script": builder_script,
			"parentfield": parentfield,
			"parenttype": parenttype,
		}
	).insert(ignore_permissions=True)
