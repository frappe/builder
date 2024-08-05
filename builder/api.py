import json

import frappe
from frappe.integrations.utils import make_post_request
from frappe.utils.telemetry import POSTHOG_HOST_FIELD, POSTHOG_PROJECT_FIELD


@frappe.whitelist()
def get_blocks(prompt):
	API_KEY = frappe.conf.openai_api_key
	if not API_KEY:
		frappe.throw("OpenAI API Key not set in site config.")

	messages = [
		{
			"role": "system",
			"content": "You are a website developer. You respond only with HTML code WITHOUT any EXPLANATION. You use any publicly available images in the webpage. You can use any font from fonts.google.com. Do not use any external css file or font files. DO NOT ADD <style> TAG AT ALL! You should use tailwindcss for styling the page. Use images from pixabay.com or unsplash.com",
		},
		{"role": "user", "content": prompt},
	]

	response = make_post_request(
		"https://api.openai.com/v1/chat/completions",
		headers={"Content-Type": "application/json", "Authorization": f"Bearer {API_KEY}"},
		data=json.dumps(
			{
				"model": "gpt-3.5-turbo",
				"messages": messages,
			}
		),
	)
	return response["choices"][0]["message"]["content"]


@frappe.whitelist()
def get_posthog_settings():
	can_record_session = False
	if start_time := frappe.db.get_default("session_recording_start"):
		start_datetime = frappe.utils.data.str_to_datetime(start_time)
		now = frappe.utils.data.now_datetime()
		can_record_session = frappe.utils.data.get_minute_diff(now, start_datetime) < 120

	return {
		"posthog_project_id": frappe.conf.get(POSTHOG_PROJECT_FIELD),
		"posthog_host": frappe.conf.get(POSTHOG_HOST_FIELD),
		"enable_telemetry": frappe.get_system_settings("enable_telemetry"),
		"telemetry_site_age": frappe.utils.telemetry.site_age(),
		"record_session": can_record_session,
		"posthog_identifier": frappe.local.site,
	}
