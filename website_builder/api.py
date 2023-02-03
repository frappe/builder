import frappe
import json
import random

@frappe.whitelist(allow_guest=True)
def publish(blocks, route, page_name=None):
	page = frappe.db.exists("Web Page Beta", {"page_name": page_name})
	blocks = json.dumps(blocks)

	if page:
		page = frappe.get_doc("Web Page Beta", page)
	else:
		page = frappe.new_doc("Web Page Beta")
		page.page_name = page_name or f"test {random.randint(0, 1000)}"

	page.route = route
	page.blocks = blocks
	page.save(ignore_permissions=True)
	return page