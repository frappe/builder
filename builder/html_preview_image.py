import base64
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


def render_full_page(html: str, width: int = 1280, height: int = 900, max_height: int = 8000) -> bytes:
	"""Capture document pixels without changing the viewport used by vh/media queries."""
	from frappe.utils.chromium import CDPSocketClient, ChromiumManager, Page
	from frappe.utils.pdf import get_host_url
	from frappe.utils.preview import safe_execute

	generator, browser_id = ChromiumManager.acquire()
	session = page = None
	try:
		if not generator._devtools_url:
			generator._set_devtools_url()
		session = CDPSocketClient(generator._devtools_url)
		session.connect()
		context, error = session.send("Target.createBrowserContext", {"disposeOnDetach": True})
		if error:
			raise RuntimeError(f"Could not create screenshot context: {error}")
		page = Page(session, context["browserContextId"], "screenshot")
		page.is_print_designer = False
		page.set_media_emulation("screen")
		page.set_device_metrics(width, height)
		page.set_tab_url(get_host_url())
		page.wait_for_navigate()
		page.set_content(html, wait_for=["load", "DOMContentLoaded", "networkIdle"])
		page.wait_for_set_content()
		metrics, error = page.send("Page.getLayoutMetrics")
		if error:
			raise RuntimeError("Could not measure screenshot document")
		content = metrics.get("cssContentSize") or metrics["contentSize"]
		result, error = page.send(
			"Page.captureScreenshot",
			{
				"format": "webp",
				"quality": 80,
				"captureBeyondViewport": True,
				"clip": {
					"x": 0,
					"y": 0,
					"width": width,
					"height": min(max_height, content["height"]),
					"scale": 1,
				},
			},
		)
		if error:
			raise RuntimeError("Could not capture screenshot")
		return base64.b64decode(result["data"])
	finally:
		safe_execute(page and page.close)
		safe_execute(session and session.disconnect)
		generator.remove_browser(browser_id)
