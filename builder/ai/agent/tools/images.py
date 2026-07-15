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


def pick_video_file(files: list[dict]) -> str | None:
	"""A browser-friendly mp4, biggest quality that isn't a 4K monster. Pexels
	returns several renditions per clip (sd/hd/uhd); a hero-background loop wants
	~1080p, not a 30 MB 4K file that stalls the page."""
	mp4s = [f for f in files if f.get("file_type") == "video/mp4" and f.get("link")]
	if not mp4s:
		return None
	sane = [f for f in mp4s if (f.get("width") or 0) <= 1920] or mp4s
	return max(sane, key=lambda f: f.get("width") or 0)["link"]


def search_pexels_videos(query: str, orientation: str | None, key: str) -> list[dict]:
	params = {"query": query, "per_page": MAX_RESULTS}
	if orientation:
		params["orientation"] = orientation
	r = requests.get(
		"https://api.pexels.com/videos/search",
		params=params,
		headers={"Authorization": key},
		timeout=SEARCH_TIMEOUT,
	)
	r.raise_for_status()
	out = []
	for v in r.json().get("videos", []):
		link = pick_video_file(v.get("video_files") or [])
		if not link:
			continue
		out.append(
			{
				"url": link,
				"thumb": v.get("image") or "",
				"description": (v.get("user") or {}).get("name") and f"clip by {v['user']['name']}" or "",
				"credit": (v.get("user") or {}).get("name") or "Pexels",
				"size": f"{v.get('width')}x{v.get('height')}, {v.get('duration')}s",
			}
		)
	return out


def run_search_videos(ctx, args: dict) -> str:
	query = (args.get("query") or "").strip()
	if not query:
		return "query is required."
	key = frappe.conf.pexels_api_key
	if not key:
		return (
			"Stock video search is unavailable (no pexels_api_key configured). Fall back to a "
			"still photo (search_images) or a CSS-animated composition for motion."
		)
	orientation = args.get("orientation") if args.get("orientation") in ORIENTATIONS else None
	try:
		results = search_pexels_videos(query, orientation, key)
	except Exception as e:
		frappe.logger("builder.ai").warning(f"search_videos via Pexels failed: {e}")
		results = []
	if not results:
		return (
			f"No videos found for '{query}'. Try a simpler, more visual query (subject + setting, "
			"e.g. 'coffee pour slow motion'), or fall back to a still photo / CSS motion."
		)
	lines = ["Pexels video results — put `url` in a video block's src (attrs.src), `thumb` as its poster:"]
	for i, v in enumerate(results, 1):
		desc = v["description"][:120] or "(no description)"
		lines.append(
			f"{i}. {desc} — by {v['credit']}, {v['size']}\n   url: {v['url']}\n   thumb: {v['thumb']}"
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

search_videos = Tool(
	name="search_videos",
	side="server",
	handler=run_search_videos,
	description=(
		"Search stock video libraries for REAL footage (ambient hero loops, product motion, "
		"textures, b-roll). Use this when a page wants motion a still photo can't give — a "
		"muted, looping hero background or a section accent. Returns direct .mp4 URLs: put `url` "
		"in a video block's attrs.src and `thumb` as the poster. A video block is "
		"{el: 'video', attrs: {src: <url>, autoplay: '', muted: '', loop: '', playsinline: '', "
		"poster: <thumb>}, style: {objectFit: 'cover', width: '100%', height: '100%'}} — muted is "
		"REQUIRED for autoplay to work. Search with a concrete visual query (subject + motion + mood)."
	),
	parameters={
		"type": "object",
		"properties": {
			"query": {
				"type": "string",
				"description": "Visual description of the motion, e.g. 'slow motion coffee pour on dark counter'.",
			},
			"orientation": {"type": "string", "enum": list(ORIENTATIONS)},
		},
		"required": ["query"],
	},
)

TOOLS = [search_images, search_videos]
