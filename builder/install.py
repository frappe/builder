import frappe
from frappe.core.api.file import create_new_folder
from builder.utils import sync_page_template


def after_install():
	create_new_folder("Builder Uploads", "Home")
	sync_page_template()

def after_migrate():
	sync_page_template()
