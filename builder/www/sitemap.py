import re
from contextlib import suppress
from urllib import robotparser
from urllib.parse import quote

import frappe
from frappe.utils import get_url
from frappe.website.router import get_pages
from frappe.www.sitemap import get_public_pages_from_doctypes, is_dynamic_route

no_cache = 1

REGEX_CHARS = frozenset(".^$*+?{}[]\\|()")


def get_context(context):
	"""Overrides frappe's www/sitemap, which lists routes that redirect, and every published
	Builder Page regardless of its indexing, access, home page and canonical settings"""
	lastmod_by_route = get_static_routes() | get_document_routes() | get_builder_page_routes()
	redirects = RedirectSources()
	base_url = get_url().rstrip("/")
	return {
		"links": [
			{"loc": f"{base_url}/{quote(route.encode('utf-8'))}".rstrip("/"), "lastmod": lastmod}
			for route, lastmod in lastmod_by_route.items()
			if not redirects.match(route)
		]
	}


class RedirectSources:
	"""Matches routes the way frappe's resolve_redirect matches a path, without its redis lookup
	per route. Plain paths are compared directly, as a regex per source per route dominated the
	sitemap's render time"""

	def __init__(self):
		rules = frappe.get_hooks("website_redirects") + (frappe.get_website_settings("route_redirects") or [])
		sources = [rule.get("source").strip("/ ") for rule in rules]
		self.paths = {source for source in sources if not REGEX_CHARS & set(source)}
		self.patterns = []
		for source in sources:
			if source not in self.paths:
				with suppress(re.error):
					self.patterns.append(re.compile(source + "$"))

	def match(self, route: str) -> bool:
		return route in self.paths or any(pattern.match(route) for pattern in self.patterns)


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
	for page in get_served_pages():
		route = "" if page.route == home_page else page.route
		if is_indexable(page, route) and robots.can_fetch("*", f"/{route}"):
			routes[route] = f"{page.published_at or page.modified:%Y-%m-%d}"
	return routes


def get_served_pages() -> list[dict]:
	"""The live page served at each route, so a shared route is judged by the page visitors get"""
	pages = frappe.get_all(
		"Builder Page",
		fields=[
			"route",
			"canonical_url",
			"disable_indexing",
			"authenticated_access",
			"published_at",
			"modified",
		],
		filters={"published": 1, "route": ["not in", ["", "404"]]},
		order_by="published_at desc, creation desc",
	)
	served = {}
	for page in pages:
		served.setdefault(page.route, page)
	return list(served.values())


def is_indexable(page: dict, route: str) -> bool:
	return not (
		page.disable_indexing
		or page.authenticated_access
		or is_dynamic_route(route)
		or has_other_canonical(page, route)
	)


def has_other_canonical(page: dict, route: str) -> bool:
	"""The home page is always canonical at the site root, whatever its canonical_url says.
	A templated canonical_url needs the page's data to resolve, so the page stays listed and
	crawlers read the rendered canonical from the page itself"""
	if not route or not page.canonical_url or "{" in page.canonical_url:
		return False
	return get_url(page.canonical_url).rstrip("/") != get_url(route)


def get_robots_parser() -> robotparser.RobotFileParser:
	parser = robotparser.RobotFileParser()
	parser.parse((frappe.get_single_value("Website Settings", "robots_txt") or "").splitlines())
	return parser
