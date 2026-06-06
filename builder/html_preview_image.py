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
		exception = response.json().get("exc")
		raise Exception(frappe.parse_json(exception)[0])
