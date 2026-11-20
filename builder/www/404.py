import frappe

from builder.builder.doctype.builder_page.builder_page import db_lookup, find_page_with_path
from builder.utils import can_serve_page


def get_context(context):
	"""Render a published Builder Page with route `404` as the site's not-found page.

	Frappe's NotFoundPage always renders the `404` template, bypassing custom page
	renderers, so this is the seam Builder uses to make the not-found page editable.
	Falls back to the default 404.html template when no such page exists, or when a hosting app
	refuses to serve it here (builder_can_serve_page).
	"""
	# a schema that lags the code (a deploy before its migrate) must not turn every not-found into a 500
	page_name = db_lookup(find_page_with_path, "404")
	if not page_name or not can_serve_page(page_name, "404"):
		return

	doc = frappe.get_cached_doc("Builder Page", page_name)
	# BuilderPage.get_context does `del context.favicon`, which assumes the key exists.
	context.setdefault("favicon", None)
	doc.get_context(context)
	context.template = "templates/generators/webpage.html"
