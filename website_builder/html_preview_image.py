import frappe
from install_playwright import install
from playwright.sync_api import sync_playwright


def get_preview(html, output_path):
	with sync_playwright() as p:
		browser = p.chromium.launch()
		page = browser.new_page()
		page.set_content(html)
		page.wait_for_load_state('networkidle', timeout=2000)
		page.screenshot(path=output_path)
		browser.close()
