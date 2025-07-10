import frappe
from frappe.core.api.file import create_new_folder

from builder.utils import (
	add_composite_index_to_web_page_view,
	sync_block_templates,
	sync_builder_variables,
	sync_page_templates,
)


def after_install():
	create_new_folder("Builder Uploads", "Home")
	create_new_folder("Fonts", "Home/Builder Uploads")
	sync_page_templates()
	sync_block_templates()
	sync_builder_variables()
	add_composite_index_to_web_page_view()


def after_migrate():
	sync_page_templates()
	sync_block_templates()
	sync_builder_variables()
