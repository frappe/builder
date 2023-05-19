import frappe


def after_install():
	frappe.utils.execute_in_shell("playwright install chromium")