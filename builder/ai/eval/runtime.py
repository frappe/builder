"""Does an interactive page actually work: the built page loaded in a real browser, its
largest canvas checked for drawing, then dragged across to see whether it answers. A
screenshot can't tell a live 3D scene from a blank box; this can."""

import io
import os
from urllib.parse import urlparse

import frappe

# Playwright's browser download can lag its version; any recent headless shell drives it
BROWSER = os.environ.get("BOB_EVAL_BROWSER") or None
ORIGIN = "http://eval.local"
SETTLE_MS = 3000


class RuntimeCheck:
	def __init__(self, page_id: str, image_prefix: str):
		self.page_id = page_id
		self.image_prefix = image_prefix
		# resolved here: Playwright calls serve() from a greenlet where frappe.local is empty
		self.site = frappe.local.site
		self.roots = (
			("/files/", frappe.get_site_path("public", "files")),
			("/assets/", frappe.get_site_path("..", "assets")),
		)

	def run(self) -> dict:
		from playwright.sync_api import sync_playwright

		html = frappe.get_doc("Builder Page", self.page_id).get_preview_html()
		with sync_playwright() as p:
			browser = p.chromium.launch(
				executable_path=BROWSER, args=["--use-angle=swiftshader", "--enable-unsafe-swiftshader"]
			)
			try:
				return self.inspect(browser.new_page(viewport={"width": 1280, "height": 800}), html)
			finally:
				browser.close()

	def inspect(self, page, html: str) -> dict:
		errors = []
		page.on("pageerror", lambda e: errors.append(str(e)[:300]))
		page.on("console", lambda m: m.type == "error" and errors.append(m.text[:300]))
		# the console's "Failed to load resource" never names the resource
		page.on("response", lambda r: r.status >= 400 and errors.append(f"{r.status} {r.url[:200]}"))
		page.route("**/*", self.serve)
		page.goto(f"{ORIGIN}/")
		page.set_content(html, wait_until="load")
		page.wait_for_timeout(SETTLE_MS)
		canvas = self.largest_canvas(page)
		result = {"errors": errors[:5], "canvases": len(page.query_selector_all("canvas"))}
		if canvas is None:
			return result
		canvas.scroll_into_view_if_needed()
		box = canvas.bounding_box()
		first = canvas.screenshot()
		page.wait_for_timeout(700)
		idle = canvas.screenshot()
		x, y = box["x"] + box["width"] / 2, box["y"] + box["height"] / 2
		page.mouse.move(x, y)
		page.mouse.down()
		page.mouse.move(x + 220, y + 60, steps=12)
		page.mouse.up()
		page.wait_for_timeout(500)
		dragged = canvas.screenshot()
		for name, image in (("before", idle), ("after-drag", dragged)):
			with open(f"{self.image_prefix}-{name}.png", "wb") as f:  # nosemgrep
				f.write(image)
		return result | {
			"canvas_size": [round(box["width"]), round(box["height"])],
			"drawn": round(spread(first), 1),
			"idle_change": round(change(first, idle), 4),
			"drag_change": round(change(idle, dragged), 4),
		}

	def largest_canvas(self, page):
		sized = [(c, c.bounding_box()) for c in page.query_selector_all("canvas")]
		sized = [(c, b) for c, b in sized if b and b["width"] * b["height"] > 10000]
		return max(sized, key=lambda cb: cb[1]["width"] * cb[1]["height"])[0] if sized else None

	def serve(self, route):
		url = urlparse(route.request.url)
		if local := self.local_file(url.path):
			return route.fulfill(path=local)
		if url.netloc == "eval.local":
			return route.fulfill(status=200, content_type="text/html", body="<!doctype html><html></html>")
		if url.hostname in (self.site, "localhost", "127.0.0.1"):
			return route.fulfill(status=404, body="")
		return route.continue_()

	def local_file(self, path: str) -> str | None:
		for prefix, root in self.roots:
			if path.startswith(prefix):
				candidate = os.path.join(root, path[len(prefix) :])
				return candidate if os.path.isfile(candidate) else None
		return None


def spread(png: bytes) -> float:
	"""How much the image varies: near 0 for a blank or single-colour canvas."""
	from PIL import Image, ImageStat

	return sum(ImageStat.Stat(Image.open(io.BytesIO(png)).convert("RGB")).stddev) / 3


def change(a: bytes, b: bytes) -> float:
	"""The share of the image that changed between two frames, 0 to 1."""
	from PIL import Image, ImageChops, ImageStat

	first, second = (Image.open(io.BytesIO(x)).convert("RGB") for x in (a, b))
	if first.size != second.size:
		return 1.0
	return sum(ImageStat.Stat(ImageChops.difference(first, second)).mean) / (3 * 255)
