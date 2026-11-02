"""Deterministic browser diagnostics; reports evidence and unverified boundaries."""

import base64
import json
from pathlib import Path

import frappe

from builder.ai.artifacts import Artifact
from builder.ai.revisions import page_revision


class BrowserPage:
	def __enter__(self):
		from frappe.utils.chromium import CDPSocketClient, ChromiumManager, Page

		self.generator, self.browser_id = ChromiumManager.acquire()
		self.session = self.page = None
		try:
			if not self.generator._devtools_url:
				self.generator._set_devtools_url()
			self.session = CDPSocketClient(self.generator._devtools_url)
			self.session.connect()
			context, error = self.session.send("Target.createBrowserContext", {"disposeOnDetach": True})
			if error:
				raise RuntimeError("Could not create verification browser")
			self.page = Page(self.session, context["browserContextId"], "bob-verification")
			self.page.is_print_designer = False
			self.page.set_media_emulation("screen")
			return self
		except Exception:
			self.__exit__(None, None, None)
			raise

	def __exit__(self, *args):
		from frappe.utils.preview import safe_execute

		safe_execute(self.page and self.page.close)
		safe_execute(self.session and self.session.disconnect)
		self.generator.remove_browser(self.browser_id)

	def evaluate(self, script):
		result, error = self.page.send(
			"Runtime.evaluate", {"expression": script, "returnByValue": True, "awaitPromise": True}
		)
		if error or result.get("exceptionDetails"):
			raise ValueError("Browser diagnostic script failed")
		return result["result"].get("value")

	def screenshot(self, width=1280, max_height=1800, y=0):
		metrics, error = self.page.send("Page.getLayoutMetrics")
		if error:
			raise RuntimeError("Could not measure page")
		height = (metrics.get("cssContentSize") or metrics["contentSize"])["height"]
		result, error = self.page.send(
			"Page.captureScreenshot",
			{
				"format": "webp",
				"quality": 80,
				"captureBeyondViewport": True,
				"clip": {"x": 0, "y": y, "width": width, "height": min(max_height, height - y), "scale": 1},
			},
		)
		if error:
			raise RuntimeError("Could not capture page")
		return base64.b64decode(result["data"]), height


def check_page(page_id, viewports=None, color_scheme="light", steps=None):
	from frappe.utils.pdf import get_host_url

	doc = frappe.get_doc("Builder Page", page_id)
	doc.check_permission("read")
	steps = validate_interactions(steps or [])
	viewports = viewports or [390, 768, 1280]
	if (
		not isinstance(viewports, list)
		or not 1 <= len(viewports) <= 3
		or any(width not in (320, 390, 768, 1280) for width in viewports)
	):
		raise ValueError("Choose up to three supported viewport widths")
	script = Path(__file__).with_name("browser").joinpath("checks.js").read_text()
	markup = doc.get_preview_html(color_scheme=color_scheme)
	if steps:
		markup = markup.replace(
			"<head>",
			"<head><meta http-equiv=\"Content-Security-Policy\" content=\"connect-src 'none'; form-action 'none'; frame-src 'none'; object-src 'none'\">",
			1,
		)
	probe = "<script>window.__bobErrors=[];addEventListener('error',e=>window.__bobErrors.push(String(e.message).slice(0,300)));addEventListener('unhandledrejection',e=>window.__bobErrors.push(String(e.reason).slice(0,300)));</script>"
	markup = markup.replace("<head>", "<head>" + probe, 1)
	report = {"revision": page_revision(page_id), "views": [], "status": "checked"}
	for width in viewports:
		with BrowserPage() as browser:
			browser.page.set_device_metrics(width, 844 if width < 768 else 900)
			browser.page.set_tab_url(get_host_url())
			browser.page.wait_for_navigate()
			browser.page.set_content(markup, wait_for=["load", "DOMContentLoaded", "networkIdle"])
			browser.page.wait_for_set_content()
			browser.evaluate("document.fonts.ready.then(() => true)")
			initial = browser.evaluate(script)
			initial["interactions"] = perform_interactions(browser, steps)
			initial["runtimeErrors"] = browser.evaluate("(window.__bobErrors || []).slice(0, 10)")
			# Visit the footer even when a page is taller than the screenshot budget.
			browser.evaluate("window.scrollTo(0, document.documentElement.scrollHeight); true")
			browser.evaluate(
				"new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(() => resolve(true))))"
			)
			initial["footer"] = browser.evaluate(
				"({bottom: scrollY+innerHeight, height: document.documentElement.scrollHeight, footerVisible: !!document.querySelector('footer')?.getClientRects().length})"
			)
			browser.page.send(
				"Emulation.setEmulatedMedia",
				{"media": "screen", "features": [{"name": "prefers-reduced-motion", "value": "reduce"}]},
			)
			initial["reducedMotionIssues"] = browser.evaluate(script)["issues"]
			initial["keyboard"] = check_keyboard(browser)
			report["views"].append(initial)
	if any(
		view["runtimeErrors"]
		or any(issue["severity"] == "error" for issue in view["issues"])
		or any(not step["passed"] for step in view["interactions"])
		for view in report["views"]
	):
		report["status"] = "issues_found"
	artifact = Artifact.save(page_id, "verification", report)
	return {"artifact_id": artifact.name, **report}


KEYS = {
	"Tab": 9,
	"Enter": 13,
	"Space": 32,
	"Escape": 27,
	"Home": 36,
	"End": 35,
	"ArrowLeft": 37,
	"ArrowUp": 38,
	"ArrowRight": 39,
	"ArrowDown": 40,
}


def validate_interactions(steps):
	if not isinstance(steps, list) or len(steps) > 16:
		raise ValueError("Supply up to 16 ordered interaction steps")
	for step in steps:
		if not isinstance(step, dict) or step.get("action") not in ("click", "fill", "press", "assert"):
			raise ValueError("Choose click, fill, press or assert")
		if not isinstance(step.get("selector"), str) or not 1 <= len(step["selector"]) <= 300:
			raise ValueError("Each step needs a bounded, unique CSS selector")
		if step["action"] == "press" and step.get("key") not in KEYS:
			raise ValueError("Choose a supported navigation key")
		if step["action"] == "assert" and step.get("state") not in (
			"visible",
			"hidden",
			"focused",
			"checked",
			"text",
			"value",
			"attribute",
		):
			raise ValueError("Choose a supported assertion state")
		if step.get("state") == "attribute" and not isinstance(step.get("attribute"), str):
			raise ValueError("Attribute assertions need an attribute name")
		if step["action"] == "fill" or step.get("state") in ("text", "value", "attribute"):
			if not isinstance(step.get("value"), str) or len(step["value"]) > 1000:
				raise ValueError("Supply a string value under 1000 characters")
	return steps


def perform_interactions(browser, steps):
	script = Path(__file__).with_name("browser").joinpath("interactions.js").read_text()
	results = []
	for step in steps:
		try:
			result = browser.evaluate(f"{script}({json.dumps(step)})")
			if step["action"] == "press" and result["passed"]:
				key = step["key"]
				for kind in ("keyDown", "keyUp"):
					browser.page.send(
						"Input.dispatchKeyEvent",
						{
							"type": kind,
							"key": " " if key == "Space" else key,
							"code": key,
							"windowsVirtualKeyCode": KEYS[key],
						},
					)
				browser.evaluate(
					"new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(() => resolve(true))))"
				)
		except Exception:
			result = {"passed": False, "detail": "Target or interaction could not be evaluated"}
		results.append({**step, **result})
		if not result["passed"]:
			break
	return results


def check_keyboard(browser):
	sequence = []
	for _ in range(12):
		browser.page.send(
			"Input.dispatchKeyEvent",
			{"type": "keyDown", "key": "Tab", "code": "Tab", "windowsVirtualKeyCode": 9},
		)
		browser.page.send(
			"Input.dispatchKeyEvent",
			{"type": "keyUp", "key": "Tab", "code": "Tab", "windowsVirtualKeyCode": 9},
		)
		sequence.append(
			browser.evaluate(
				"(() => { const e=document.activeElement, s=getComputedStyle(e); return {tag:e.tagName,id:e.id,label:(e.getAttribute('aria-label')||e.textContent||'').slice(0,60), focusVisible:e.matches(':focus-visible'),outline:s.outlineStyle,boxShadow:s.boxShadow}; })()"
			)
		)
	return {"first12TabStops": sequence, "complete": False}
