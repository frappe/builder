"""Image search — real photos for pages instead of drawn SVGs.

Providers, best first: Pexels (site_config `pexels_api_key`), Unsplash
(site_config `unsplash_access_key`), then keyless Openverse as the
zero-config fallback. Each result carries a full-size `url` (for page
blocks / generation briefs) and a `thumb` (for present_ui image options).
"""

import frappe
import requests

from builder.ai.agent.registry import Tool

SEARCH_TIMEOUT = 10
MAX_RESULTS = 6
ORIENTATIONS = ("landscape", "portrait", "square")


def search_pexels(query: str, orientation: str | None, key: str) -> list[dict]:
	params = {"query": query, "per_page": MAX_RESULTS}
	if orientation:
		params["orientation"] = orientation
	r = requests.get(
		"https://api.pexels.com/v1/search",
		params=params,
		headers={"Authorization": key},
		timeout=SEARCH_TIMEOUT,
	)
	r.raise_for_status()
	return [
		{
			"url": p["src"]["large2x"],
			"thumb": p["src"]["medium"],
			"description": p.get("alt") or "",
			"credit": p.get("photographer") or "Pexels",
			"size": f"{p.get('width')}x{p.get('height')}",
		}
		for p in r.json().get("photos", [])
	]


def search_unsplash(query: str, orientation: str | None, key: str) -> list[dict]:
	params = {"query": query, "per_page": MAX_RESULTS}
	if orientation:
		params["orientation"] = "squarish" if orientation == "square" else orientation
	r = requests.get(
		"https://api.unsplash.com/search/photos",
		params=params,
		headers={"Authorization": f"Client-ID {key}"},
		timeout=SEARCH_TIMEOUT,
	)
	r.raise_for_status()
	return [
		{
			"url": p["urls"]["regular"],
			"thumb": p["urls"]["small"],
			"description": p.get("alt_description") or "",
			"credit": (p.get("user") or {}).get("name") or "Unsplash",
			"size": f"{p.get('width')}x{p.get('height')}",
		}
		for p in r.json().get("results", [])
	]


def search_openverse(query: str, orientation: str | None) -> list[dict]:
	params = {"q": query, "page_size": MAX_RESULTS, "license_type": "commercial"}
	if orientation:
		params["aspect_ratio"] = (
			"wide" if orientation == "landscape" else ("tall" if orientation == "portrait" else "square")
		)
	r = requests.get("https://api.openverse.org/v1/images/", params=params, timeout=SEARCH_TIMEOUT)
	r.raise_for_status()
	return [
		{
			"url": p.get("url") or "",
			"thumb": p.get("thumbnail") or p.get("url") or "",
			"description": p.get("title") or "",
			"credit": p.get("creator") or "Openverse",
			"size": f"{p.get('width')}x{p.get('height')}",
		}
		for p in r.json().get("results", [])
		if p.get("url")
	]


def providers() -> list[tuple[str, callable]]:
	out: list[tuple[str, callable]] = []
	if frappe.conf.pexels_api_key:
		out.append(("Pexels", lambda q, o: search_pexels(q, o, frappe.conf.pexels_api_key)))
	if frappe.conf.unsplash_access_key:
		out.append(("Unsplash", lambda q, o: search_unsplash(q, o, frappe.conf.unsplash_access_key)))
	out.append(("Openverse", search_openverse))
	return out


def run_search_images(ctx, args: dict) -> str:
	query = (args.get("query") or "").strip()
	if not query:
		return "query is required."
	orientation = args.get("orientation") if args.get("orientation") in ORIENTATIONS else None
	for name, search in providers():
		try:
			results = search(query, orientation)
		except Exception as e:
			frappe.logger("builder.ai").warning(f"search_images via {name} failed: {e}")
			continue
		if results:
			return render_results(name, results)
	return (
		f"No images found for '{query}'. Try a simpler, more visual query (subject + setting, "
		"e.g. 'running shoe studio'), or fall back to a CSS composition."
	)


def render_results(provider: str, results: list[dict]) -> str:
	lines = [f"{provider} results — `url` goes in page blocks/briefs, `thumb` in present_ui image options:"]
	for i, p in enumerate(results, 1):
		desc = p["description"][:120] or "(no description)"
		lines.append(
			f"{i}. {desc} — by {p['credit']}, {p['size']}\n   url: {p['url']}\n   thumb: {p['thumb']}"
		)
	return "\n".join(lines)


search_images = Tool(
	name="search_images",
	side="server",
	handler=run_search_images,
	description=(
		"Search stock photo libraries for REAL photographs (products, food, people, places, "
		"textures). Use this instead of drawing real-world subjects as SVG. Returns direct "
		"image URLs: put `url` in blocks/briefs (img src, meta_image), and `thumb` on "
		"present_ui choices options (option.image) when offering the user a pick. Search "
		"with a concrete visual query (subject + setting + mood), not a brand name."
	),
	parameters={
		"type": "object",
		"properties": {
			"query": {
				"type": "string",
				"description": "Visual description, e.g. 'white running shoe on dark background'.",
			},
			"orientation": {"type": "string", "enum": list(ORIENTATIONS)},
		},
		"required": ["query"],
	},
)

TOOLS = [search_images]
