"""Image and video search: real photos and footage for pages instead of drawn SVGs.

Photo providers, best first: Pexels (site_config `pexels_api_key`), Unsplash
(site_config `unsplash_access_key`), then keyless Openverse as the
zero-config fallback. Each result carries a full-size `url` (for page
blocks / generation briefs) and a `thumb` (for present_ui image options).
Video comes from Pexels alone, so search_videos is offered only with its key.
"""

import re

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


def search_pexels_videos(query: str, orientation: str | None, key: str) -> list[dict]:
	params = {"query": query, "per_page": MAX_RESULTS}
	if orientation:
		params["orientation"] = orientation
	r = requests.get(
		"https://api.pexels.com/v1/videos/search",
		params=params,
		headers={"Authorization": key},
		timeout=SEARCH_TIMEOUT,
	)
	r.raise_for_status()
	return [clip for video in r.json().get("videos", []) if (clip := pexels_clip(video))]


def pexels_clip(video: dict) -> dict | None:
	"""A Pexels video as its lightest HD mp4: a muted loop behind type needs no more,
	and every extra megabyte delays the page's first frame."""
	files = [
		f
		for f in video.get("video_files") or []
		if f.get("file_type") == "video/mp4" and min(f.get("width") or 0, f.get("height") or 0) >= 720
	]
	if not files:
		return None
	file = min(files, key=lambda f: f["width"] * f["height"])
	# Pexels gives a video no description; its page slug names the subject.
	slug = re.sub(r"-?\d+/?$", "", (video.get("url") or "").rstrip("/").rsplit("/", 1)[-1])
	return {
		"kind": "video",
		"url": file["link"],
		"thumb": video.get("image") or "",
		"poster": video.get("image") or "",
		"description": slug.replace("-", " "),
		"credit": (video.get("user") or {}).get("name") or "Pexels",
		"size": f"{file['width']}x{file['height']}",
		"seconds": video.get("duration"),
	}


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
			# Hand the generator the results directly (see artifact.generate_page_markup).
			# Copying urls into the brief by hand is how photos went missing — and how
			# one arrived with two digits transposed, 404ing the whole turn.
			remember_for_generation(ctx, query, results)
			return render_results(name, results)
	return (
		f"No images found for '{query}'. Try a simpler, more visual query (subject + setting, "
		"e.g. 'running shoe studio'), or fall back to a CSS composition."
	)


def run_search_videos(ctx, args: dict) -> str:
	query = (args.get("query") or "").strip()
	if not query:
		return "query is required."
	orientation = args.get("orientation") if args.get("orientation") in ORIENTATIONS else None
	try:
		results = search_pexels_videos(query, orientation, frappe.conf.pexels_api_key)
	except Exception as e:
		frappe.logger("builder.ai").warning(f"search_videos failed: {e}")
		return f"FAILED: the video search didn't answer ({e}). Go on with photos."
	if not results:
		return f"No videos found for '{query}'. Try a simpler subject + setting, or go on with photos."
	remember_for_generation(ctx, query, results)
	lines = ["Pexels videos (each reaches generate_page by itself; `thumb` goes on present_ui options):"]
	for i, v in enumerate(results, 1):
		lines.append(
			f"{i}. {v['description'] or '(no description)'}, {v['seconds']}s, {v['size']}, by {v['credit']}\n"
			f"   src: {v['url']}\n   poster: {v['poster']}"
		)
	return "\n".join(lines)


MAX_REMEMBERED_IMAGES = 24


def remember_for_generation(ctx, query: str, results: list[dict]) -> None:
	found = getattr(ctx, "found_images", None)
	if found is None:
		return
	for r in results:
		if len(found) >= MAX_REMEMBERED_IMAGES:
			return
		found.append({**r, "query": query})


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
		"with a concrete visual query (subject + setting + mood), not a brand name, and once "
		"per subject the page shows, all in one round. Every result reaches generate_page by "
		"itself: a brief names only an image a section must use (HERO IMAGE: <url>). For "
		"imagery that defines the page (the hero photo, a logo), let the user pick, unless they "
		"left the photos to you: 3-4 results as present_ui choices plus an upload option."
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
	available=lambda ctx: bool(frappe.conf.pexels_api_key),
	description=(
		"Search Pexels for short stock footage to loop silently in a page: surf at the café's "
		"door, hands centring clay, a peloton cresting a hill. Footage of the brand's world is the "
		"strongest hero there is. Query like search_images (subject + setting + mood); every "
		"result reaches generate_page by itself."
	),
	parameters={
		"type": "object",
		"properties": {
			"query": {
				"type": "string",
				"description": "Visual description, e.g. 'barista pouring latte art'.",
			},
			"orientation": {"type": "string", "enum": list(ORIENTATIONS)},
		},
		"required": ["query"],
	},
)

TOOLS = [search_images, search_videos]
