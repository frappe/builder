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


def render_full_page(
	html: str, width: int = 1280, height: int = 900, max_height: int = 8000, regions: list | None = None
) -> bytes:
	"""Capture document pixels and optional section bounds in the same browser render."""
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
		capture_height = min(max_height, content["height"])
		if regions is not None:
			regions.extend(preview_regions(page, width, capture_height))
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
					"height": capture_height,
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


def preview_regions(page, width: int, height: int) -> list[dict]:
	result, error = page.send(
		"Runtime.evaluate",
		{
			"returnByValue": True,
			"expression": """(() => {
				const regions = [], included = [];
				for (const node of [...document.querySelectorAll('header, nav, section, footer, form')].slice(0, 100)) {
					if (included.some(parent => parent.contains(node))) continue;
					const box = node.getBoundingClientRect();
					if (box.width < 120 || box.height < 40) continue;
					const heading = node.querySelector('h1, h2, h3');
					const label = heading?.textContent?.trim() ||
						({HEADER: 'Header', NAV: 'Navigation', FOOTER: 'Footer', FORM: 'Form'})[node.tagName] ||
						`Section ${regions.length + 1}`;
					regions.push({label: label.slice(0, 60), x: box.x + scrollX, y: box.y + scrollY,
						width: box.width, height: box.height});
					included.push(node);
				}
				return regions;
			})()""",
		},
	)
	if error or result.get("exceptionDetails"):
		return []
	regions = []
	for region in result.get("result", {}).get("value", []):
		x, y = max(0, int(region["x"])), max(0, int(region["y"]))
		right = min(width, int(region["x"] + region["width"]))
		bottom = min(height, int(region["y"] + region["height"]))
		if right - x >= 120 and bottom - y >= 40 and (right - x) * (bottom - y) < width * height * 0.95:
			regions.append({"label": region["label"], "box": (x, y, right, bottom)})
	return regions[:4]
