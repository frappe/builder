"""A read-only snapshot of a published page, for the sandboxed editor demo.

The demo editor runs entirely against this snapshot in the visitor's browser.
It never talks to the server, so it only carries what the published page
already renders and serves publicly, never drafts, the data script or other site data.
"""

from glob import glob

import frappe

from builder.builder.component_versions import resolve_component, walk_blocks

CACHE_SECONDS = 300

# The editor loads from the site but may not open a single connection back to it,
# even for a signed-in visitor whose cookies ride along.
CONTENT_SECURITY_POLICY = "; ".join(
	[
		"default-src 'self'",
		# block client scripts run in the canvas through new Function
		"script-src 'self' 'unsafe-inline' 'unsafe-eval'",
		"style-src 'self' 'unsafe-inline' https:",
		"img-src * data: blob:",
		"media-src * data: blob:",
		"font-src * data:",
		# the font picker reads glyph subsets from Google Fonts
		"connect-src https://fonts.googleapis.com",
		"frame-src https:",
		"form-action 'none'",
		"base-uri 'none'",
		"object-src 'none'",
		"frame-ancestors 'self'",
	]
)

PAGE_FIELDS = ["name", "page_name", "page_title", "route", "blocks", "favicon", "modified"]
TOKEN_FIELDS = ["name", "token_name", "value", "type", "is_standard", "dark_value", "group"]


class EditorDemo:
	def __init__(self, page: frappe._dict):
		self.page = page

	@classmethod
	def from_app_path(cls, app_path: str | None) -> "EditorDemo | None":
		prefix, _, page_name = (app_path or "").partition("/")
		if prefix != "demo":
			return None
		page = frappe.db.get_value(
			"Builder Page",
			{"name": page_name, "published": 1, "authenticated_access": 0},
			PAGE_FIELDS,
			as_dict=True,
		)
		if not page or not is_demo_page(page_name):
			# a cached 404 would outlive the page being opted in later
			frappe.local.no_cache = 1
			raise frappe.PageDoesNotExistError
		return cls(page)

	def set_context(self, context):
		# every value the shell reads, so none falls through to the signed-in session
		context.update(
			{
				"editor_demo": self.get_payload(),
				"csrf_token": "",
				"site_name": frappe.local.site,
				"builder_version": "",
				"is_developer_mode": 0,
				"is_fc_site": 0,
				"is_read_only_mode": 0,
			}
		)
		frappe.local.response_headers.update(
			{
				"Content-Security-Policy": CONTENT_SECURITY_POLICY,
				"Referrer-Policy": "same-origin",
				"X-Content-Type-Options": "nosniff",
				"X-Robots-Tag": "noindex",
			}
		)

	def get_payload(self) -> dict:
		cache_key = f"builder_editor_demo:{self.page.name}:{self.page.modified}"
		payload = frappe.cache.get_value(cache_key)
		if not payload:
			payload = self.build_payload()
			frappe.cache.set_value(cache_key, payload, expires_in_sec=CACHE_SECONDS)
		return payload

	def build_payload(self) -> dict:
		components, versions = collect_components(frappe.parse_json(self.page.blocks) or [])
		used = frappe.as_json([self.page.blocks, components, versions])
		fonts = frappe.get_all("User Font", fields=["name", "font_name", "font_file"])
		tokens = frappe.get_all("Builder Token", fields=TOKEN_FIELDS, order_by="creation desc")
		templates = frappe.get_module_path("builder", "builder_block_template")
		return {
			"page": {**self.page, "modified": str(self.page.modified), "published": 1},
			"components": components,
			"componentVersions": versions,
			# only what the page uses, referenced in its styles as var(--<token name>)
			"tokens": [token for token in tokens if token.name in used],
			"fonts": [font for font in fonts if font.font_name in used],
			# the block templates Builder ships, read from the app rather than the site
			"blockTemplates": [frappe.get_file_json(file) for file in sorted(glob(f"{templates}/*/*.json"))],
			# already public: the published page links each of them as a file
			"scripts": frappe.get_all(
				"Builder Page Client Script",
				filters={"parent": self.page.name, "parenttype": "Builder Page"},
				fields=["builder_script.script_type as script_type", "builder_script.script as script"],
				order_by="idx",
			),
		}


def is_demo_page(page_name: str) -> bool:
	"""Pages opt in from the site config, e.g. `"builder_demo_pages": ["page-1a2b3c4d"]`."""
	return page_name in (frappe.conf.builder_demo_pages or [])


def collect_components(blocks: list) -> tuple[dict, dict]:
	"""Live and pinned versions of every component the blocks use, nested ones included."""
	components, versions = {}, {}
	pending = [blocks]

	def visit(block):
		component_id = block.get("extendedFromComponent")
		if component_id and component_id not in components:
			components[component_id] = get_component(component_id)
			pending.append(components[component_id])
		version = block.get("componentVersion")
		if component_id and version and version not in versions:
			versions[version] = get_component(component_id, version)
			pending.append(versions[version])

	while pending:
		source = pending.pop()
		walk_blocks(frappe.parse_json(source["block"]) if isinstance(source, dict) else source, visit)
	return {k: v for k, v in components.items() if v}, {k: v for k, v in versions.items() if v}


def get_component(component_id: str, version: str | None = None) -> dict | None:
	if resolved := resolve_component(component_id, version):
		name = frappe.get_cached_value("Builder Component", component_id, "component_name")
		# the block alone: the data script is server code
		return {
			"name": component_id,
			"component_id": component_id,
			"component_name": name,
			"block": resolved["block"],
		}
