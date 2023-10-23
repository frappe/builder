import json

import frappe
from frappe.integrations.utils import make_post_request

@frappe.whitelist()
def get_blocks(prompt):
	API_KEY = frappe.conf.openai_api_key
	if not API_KEY:
		frappe.throw("OpenAI API Key not set in site config.")

	messages = [
		{"role": "system", "content": "You are a website developer. You respond only with HTML code WITHOUT any EXPLANATION. You use any publicly available images in the webpage. You can use any font from fonts.google.com. Do not use any external css file or font files. DO NOT ADD <style> TAG AT ALL! You should use tailwindcss for styling the page. Use images from pixabay.com or unsplash.com"},
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
