import frappe
import json
import random

@frappe.whitelist(allow_guest=True)
def publish(blocks, page_name=None):
	page = frappe.db.exists("Web Page Beta", {"page_name": page_name})
	blocks = json.dumps(blocks)

	if page:
		page = frappe.get_doc("Web Page Beta", page)
	else:
		page = frappe.new_doc("Web Page Beta")
		page.page_name = page_name

	page.route = f"pages/{frappe.generate_hash(length=20)}"
	page.blocks = blocks
	page.save(ignore_permissions=True)
	return page