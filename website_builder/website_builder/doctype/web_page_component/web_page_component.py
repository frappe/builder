# Copyright (c) 2023, asdf and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document

class WebPageComponent(Document):
	pass

# TODO: Allow only for logged in users
@frappe.whitelist(allow_guest=True)
def create_component(component_name, block):
	component = frappe.new_doc("Web Page Component")
	component.component_name = component_name
	component.block = block
	component.save(ignore_permissions=True)
	return component
