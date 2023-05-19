import frappe


def after_install():
	frappe.utils.execute_in_shell("PLAYWRIGHT_BROWSERS_PATH=0 playwright install chromium")