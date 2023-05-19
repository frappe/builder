from install_playwright import install
from playwright.sync_api import sync_playwright


def get_preview(html, output_path):
	with sync_playwright() as p:
		install(p.chromium)
		browser = p.chromium.launch()
		page = browser.new_page()
		page.set_content(html)
		page.screenshot(path=output_path)
		browser.close()
