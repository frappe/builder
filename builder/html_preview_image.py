import html as html_parser

import frappe


def generate_preview(html, output_path, width: int = 1280, height: int = 720):
	image = render(html, width=width, height=height)
	with open(output_path, "wb") as f:
		f.write(image)


def render(html: str, width: int = 1280, height: int = 720) -> bytes:
	# Newer Frappe versions ship a built-in headless-Chromium screenshot generator,
	# so we render previews in-process — no external service, and local assets
	# resolve. Older versions don't have this helper; fall back to the
	# preview_generator HTTP service there (which renders at its own fixed size).
	try:
		from frappe.utils.preview import capture_screenshot
	except ImportError:
		return render_via_service(html)

	return capture_screenshot("webp", html=html, width=width, height=height)


def render_via_service(html: str) -> bytes:
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
