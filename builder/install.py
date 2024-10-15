import frappe
from frappe.core.api.file import create_new_folder

from builder.utils import sync_block_templates, sync_page_templates


def after_install():
	create_new_folder("Builder Uploads", "Home")
	create_new_folder("Fonts", "Home/Builder Uploads")
	sync_page_templates()
	sync_block_templates()


def after_migrate():
	sync_page_templates()
	sync_block_templates()
