import frappe
from frappe.core.api.file import create_new_folder

from builder.ai.presets import sync_site_provider
from builder.export_import_standard_page import sync_standard_builder_pages
from builder.utils import (
	add_composite_index_to_web_page_view,
	sync_block_templates,
	sync_builder_tokens,
	sync_page_templates,
)

WEBSITE_SIDEBAR_ITEM = {
	"type": "Link",
	"label": "Builder",
	"link_type": "URL",
	"url": "/api/method/builder.api.open_editor",
	"icon": "layout-template",
}


def after_install():
	create_new_folder("Builder Uploads", "Home")
	create_new_folder("Fonts", "Home/Builder Uploads")
	sync_page_templates()
	sync_block_templates()
	sync_builder_tokens()
	add_composite_index_to_web_page_view()
	sync_standard_builder_pages()
	sync_site_provider()
	add_builder_to_website_sidebar()


def after_migrate():
	sync_page_templates()
	sync_block_templates()
	sync_builder_tokens()
	sync_standard_builder_pages()
	sync_site_provider()
	add_builder_to_website_sidebar()


def after_app_install(app_name=None):
	sync_standard_builder_pages(app_name)


def before_uninstall():
	remove_builder_from_website_sidebar()


def has_sidebar_layers() -> bool:
	return bool(frappe.db.exists("DocType", "Custom Sidebar"))


def add_builder_to_website_sidebar():
	if not has_sidebar_layers():
		return

	from frappe.desk.doctype.custom_sidebar.custom_sidebar import add_site_sidebar_item

	add_site_sidebar_item("Website", WEBSITE_SIDEBAR_ITEM)


def remove_builder_from_website_sidebar():
	if not has_sidebar_layers():
		return

	from frappe.desk.doctype.custom_sidebar.custom_sidebar import get_customization

	layer = get_customization("Website", None)
	if not layer:
		return

	layer = frappe.get_doc("Custom Sidebar", layer.name)
	layer.set("sidebar_items", [row for row in layer.sidebar_items if row.url != WEBSITE_SIDEBAR_ITEM["url"]])
	layer.save(ignore_permissions=True)
