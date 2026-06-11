import html as html_parser

import frappe
from frappe.utils import cint


def generate_preview(html, output_path):
	image = _render(html)
	with open(output_path, "wb") as f:
		f.write(image)


def _render(html: str) -> bytes:
	# Frappe v16+ ships a built-in headless-Chromium screenshot generator, so we
	# render previews in-process — no external service, and local assets resolve.
	# Builder still supports v15, where that helper doesn't exist; fall back to
	# the preview_generator HTTP service there.
	if cint(frappe.__version__.split(".")[0]) >= 16:
		from frappe.utils.preview import get_preview_from_html

		return get_preview_from_html(html, format="webp")

	return _render_via_service(html)


def _render_via_service(html: str) -> bytes:
	# Note: while working locally, "preview.frappe.cloud" can't reach the local
	# server for assets, so set `preview_generator_url` to a local/self-hosted
	# preview_generator (https://github.com/frappe/preview_generator).
	import requests

	url = (
		frappe.conf.preview_generator_url
		or "https://preview.frappe.cloud/api/method/preview_generator.api.generate_preview"
	)
	response = requests.post(url, json={"html": html_parser.escape(html), "format": "webp"})
	if response.status_code != 200:
		raise Exception(frappe.parse_json(response.json().get("exc"))[0])
	return response.content
