import re
from contextlib import suppress
from urllib import robotparser
from urllib.parse import quote

import frappe
from frappe.utils import get_url, getdate
from frappe.website.router import get_pages
from frappe.www.sitemap import get_public_pages_from_doctypes, is_dynamic_route

from builder.utils import execute_script

no_cache = 1

REGEX_CHARS = frozenset(".^$*+?{}[]\\|()")
ROUTE_VARIABLE = re.compile(r":(\w+)|<(?:\w+:)?(\w+)>")


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
		page_route = "" if page.route == home_page else page.route
		for route, lastmod in get_listed_routes(page, page_route):
			if is_indexable(page, route) and robots.can_fetch("*", f"/{route}"):
				routes[route] = lastmod
	return routes


def get_listed_routes(page: dict, route: str) -> list[tuple[str, str | None]]:
	"""A dynamic route stands for the routes its sitemap script lists"""
	lastmod = format_date(page.published_at or page.modified)
	if not is_dynamic_route(route):
		return [(route, lastmod)]
	return [
		(filled_route, format_date(variables.get("lastmod")) or lastmod)
		for variables in run_sitemap_script(page)
		if (filled_route := fill_route(route, variables))
	]


def run_sitemap_script(page: dict) -> list[dict]:
	if not page.sitemap_script:
		return []
	_locals = {"routes": []}
	try:
		execute_script(page.sitemap_script, _locals, page.name)
	except Exception:
		# one page's broken script shouldn't take the whole sitemap down
		frappe.log_error(f"Sitemap script failed for Builder Page {page.name}")
		return []
	return [variables for variables in _locals["routes"] if isinstance(variables, dict)]


def fill_route(route: str, variables: dict) -> str | None:
	parts = [fill_route_part(part, variables) for part in route.split("/")]
	return None if None in parts else "/".join(parts)


def fill_route_part(part: str, variables: dict) -> str | None:
	variable = ROUTE_VARIABLE.fullmatch(part)
	if not variable:
		return part
	value = str(variables.get(variable.group(1) or variable.group(2)) or "").strip()
	# a value with a slash would fill more than its own segment of the route
	return value if value and "/" not in value else None


def format_date(value) -> str | None:
	with suppress(Exception):
		return f"{getdate(value):%Y-%m-%d}" if value else None


def get_served_pages() -> list[dict]:
	"""The live page served at each route, so a shared route is judged by the page visitors get"""
	pages = frappe.get_all(
		"Builder Page",
		fields=[
			"name",
			"route",
			"sitemap_script",
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
