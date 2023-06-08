import json

import frappe
from frappe.integrations.utils import make_post_request


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

@frappe.whitelist(allow_guest=True)
def get_blocks(prompt):
	API_KEY = frappe.conf.openai_api_key
	if not API_KEY:
		frappe.throw("OpenAI API Key not set in site config.")

	messages = [
		{"role": "system", "content": "You are a website developer. You use any publicly available image and use it in the webpage. You can use any fonts available in fonts.google.com. You NEVER add \<style\> tag to the HTML. You style the webpage using inline styles. You can also use tailwind css classes to style the webpage. You respond only with HTML code WITHOUT any EXPLANATION"},
		{"role": "user", "content": prompt}
	]

	response = make_post_request(
		"https://api.openai.com/v1/chat/completions",
		headers={
			"Content-Type": "application/json",
			"Authorization": f"Bearer {API_KEY}"
		},
		data=json.dumps({
			"model": "gpt-3.5-turbo",
			"messages": messages,
		}),
	)
	return response['choices'][0]['message']['content']

@frappe.whitelist(allow_guest=True)
def create_new_page(blocks):
	page = frappe.new_doc("Web Page Beta")
	page.route = f"pages/{frappe.generate_hash(length=20)}"
	page.blocks = json.dumps(blocks)
	page.page_name = f"page-{frappe.generate_hash(length=5)}"
	page.save(ignore_permissions=True)
	page.page_title = "My Page"
	page.save(ignore_permissions=True)
	return page