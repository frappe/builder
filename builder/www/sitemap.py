from urllib import robotparser
from urllib.parse import quote

import frappe
from frappe.utils import get_url
from frappe.website.router import get_pages
from frappe.www.sitemap import get_public_pages_from_doctypes, is_dynamic_route

no_cache = 1


def get_context(context):
	"""Overrides frappe's www/sitemap, which lists every published Builder Page regardless of
	its indexing, access, home page and canonical settings"""
	lastmod_by_route = get_static_routes() | get_document_routes() | get_builder_page_routes()
	return {
		"links": [
			{"loc": get_url(quote(route.encode("utf-8"))), "lastmod": lastmod}
			for route, lastmod in lastmod_by_route.items()
		]
	}


def get_static_routes() -> dict:
	"""www pages have no reliable change date, so they go without a lastmod"""
	return {route: None for route, page in get_pages().items() if page.sitemap}


def get_document_routes() -> dict:
	return {
		route: f"{page['modified']:%Y-%m-%d}"
		for route, page in get_public_pages_from_doctypes().items()
		if page["doctype"] != "Builder Page"
	}


def get_builder_page_routes() -> dict:
	home_page = frappe.get_cached_value("Builder Settings", "Builder Settings", "home_page")
	robots = get_robots_parser()
	routes = {}
	for page in get_indexable_pages():
		route = "" if page.route == home_page else page.route
		if is_dynamic_route(route) or has_other_canonical(page, route):
			continue
		if robots.can_fetch("*", f"/{route}"):
			routes.setdefault(route, f"{page.published_at or page.modified:%Y-%m-%d}")
	return routes


def get_indexable_pages() -> list[dict]:
	return frappe.get_all(
		"Builder Page",
		fields=["route", "canonical_url", "published_at", "modified"],
		filters={
			"published": 1,
			"disable_indexing": 0,
			"authenticated_access": 0,
			"route": ["not in", ["", "404"]],
		},
		# same precedence as the renderer, so a shared route lists the page it serves
		order_by="published_at desc, creation desc",
	)


def has_other_canonical(page: dict, route: str) -> bool:
	"""The home page is always canonical at the site root, whatever its canonical_url says"""
	if not route or not page.canonical_url:
		return False
	return get_url(page.canonical_url).rstrip("/") != get_url(route)


def get_robots_parser() -> robotparser.RobotFileParser:
	parser = robotparser.RobotFileParser()
	parser.parse((frappe.get_single_value("Website Settings", "robots_txt") or "").splitlines())
	return parser
