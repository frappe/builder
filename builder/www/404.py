import frappe

from builder.builder.doctype.builder_page.builder_page import find_page_with_path


def get_context(context):
	"""Render a published Builder Page with route `404` as the site's not-found page.

	Frappe's NotFoundPage always renders the `404` template, bypassing custom page
	renderers, so this is the seam Builder uses to make the not-found page editable.
	Falls back to the default 404.html template when no such page exists.
	"""
	page_name = find_page_with_path("404")
	if not page_name:
		return

	doc = frappe.get_cached_doc("Builder Page", page_name)
	# BuilderPage.get_context does `del context.favicon`, which assumes the key exists.
	context.setdefault("favicon", None)
	doc.get_context(context)
	context.template = "templates/generators/webpage.html"
