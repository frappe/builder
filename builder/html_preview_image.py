import html as html_parser

import frappe
import requests

# TODO: Find better alternative
# Note: while working locally, "preview.frappe.cloud" won't be able to generate preview properly since it can't access local server for assets
# So, for local development, better to use local server for preview generation
# (https://github.com/frappe/preview_generator)
PREVIEW_GENERATOR_URL = (
	frappe.conf.preview_generator_url
	or "https://preview.frappe.cloud/api/method/preview_generator.api.generate_preview"
)


def generate_preview(html, output_path):
	escaped_html = html_parser.escape(html)
	response = requests.post(PREVIEW_GENERATOR_URL, json={"html": escaped_html, "format": "webp"})
	if response.status_code == 200:
		with open(output_path, "wb") as f:
			f.write(response.content)
	else:
		try:
			exception = response.json().get("exc")
			parsed = frappe.parse_json(exception) if exception else None
			message = (
				parsed[0]
				if parsed
				else response.text or f"Preview generation failed (HTTP {response.status_code})"
			)
		except Exception:
			message = response.text or f"Preview generation failed (HTTP {response.status_code})"
		raise Exception(message)
