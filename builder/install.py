import frappe
from frappe.core.api.file import create_new_folder

from builder.ai.models import DEFAULT_AI_MODEL
from builder.ai.presets import sync_site_provider
from builder.export_import_standard_page import sync_standard_builder_pages
from builder.utils import (
	add_composite_index_to_web_page_view,
	sync_block_templates,
	sync_builder_tokens,
	sync_page_templates,
)


def after_install():
	create_new_folder("Builder Uploads", "Home")
	create_new_folder("Fonts", "Home/Builder Uploads")
	sync_page_templates()
	sync_block_templates()
	sync_builder_tokens()
	add_composite_index_to_web_page_view()
	sync_standard_builder_pages()
	frappe.db.set_single_value("Builder Settings", "default_ai_model", DEFAULT_AI_MODEL)
	sync_site_provider()


def after_migrate():
	sync_page_templates()
	sync_block_templates()
	sync_builder_tokens()
	sync_standard_builder_pages()
	sync_site_provider()


def after_app_install(app_name=None):
	sync_standard_builder_pages(app_name)
