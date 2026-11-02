"""Image search — real photos for pages instead of drawn SVGs.

Opt-in Magnific discovery precedes Pexels, Unsplash and keyless Openverse.
Paid previews have no page URL; licensing and import are manual. Unsplash
requires an explicit selected-use download event, never an event on search.
"""

import frappe
import requests

from builder.ai.agent.registry import Tool
from builder.ai.assets import (
	MAX_RESULTS,
	ORIENTATIONS,
	SEARCH_TIMEOUT,
	MagnificStock,
	track_unsplash_download,
	unsplash_referral_url,
)


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
			"id": f"pexels:{p['id']}",
			"provider": "Pexels",
			"source_url": p.get("url"),
			"license_url": "https://www.pexels.com/license/",
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
			"id": f"unsplash:{p['id']}",
			"provider": "Unsplash",
			"source_url": unsplash_referral_url((p.get("links") or {}).get("html")),
			"download_location": (p.get("links") or {}).get("download_location"),
			"requires_acquisition": True,
			"license_url": "https://unsplash.com/license",
			"url": p["urls"]["regular"],
			"thumb": p["urls"]["small"],
			"description": p.get("alt_description") or "",
			"credit": (p.get("user") or {}).get("name") or "Unsplash",
			"credit_url": unsplash_referral_url(((p.get("user") or {}).get("links") or {}).get("html")),
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
			"id": f"openverse:{p['id']}",
			"provider": "Openverse",
			"source_url": p.get("foreign_landing_url"),
			"license_url": p.get("license_url"),
			"license": p.get("license"),
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
	if frappe.conf.get("bob_stock_provider") == "magnific" and frappe.conf.get("magnific_api_key"):
		out.append(("Magnific", MagnificStock(frappe.conf.magnific_api_key).search))
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
	provider = args.get("provider") or "auto"
	available = [(name, search) for name, search in providers() if provider in ("auto", name.lower())]
	if not available:
		return "Requested image provider is unavailable. Configure it on the site or choose another provider."
	for name, search in available:
		try:
			results = search(query, orientation)
		except Exception as e:
			frappe.logger("builder.ai").warning(f"search_images via {name} failed ({type(e).__name__})")
			if provider != "auto":
				return f"Image search via {name} failed. Try again or choose another provider."
			continue
		if results:
			# Hand the generator the results directly (see artifact.generate_page_yaml).
			# Copying urls into the brief by hand is how photos went missing — and how
			# one arrived with two digits transposed, 404ing the whole turn.
			results = remember_for_generation(ctx, query, results)
			return render_results(name, results)
	return (
		f"No images found for '{query}'. Try a simpler, more visual query (subject + setting, "
		"e.g. 'running shoe studio'), or fall back to a CSS composition."
	)


MAX_REMEMBERED_IMAGES = 24


def remember_for_generation(ctx, query: str, results: list[dict]) -> list[dict]:
	assets = [{**r, "query": query} for r in results]
	if getattr(ctx, "page_id", None):
		from builder.ai.brief import DesignBrief

		brief = DesignBrief(ctx.page_id)
		brief.remember_assets(assets)
		saved = {a.get("id") or a.get("url"): a for a in brief.read().get("assets", [])}
		assets = [saved.get(a.get("id") or a.get("url"), a) for a in assets]
	if (found := getattr(ctx, "found_images", None)) is not None:
		by_id = {a.get("id") or a.get("url"): a for a in [*found, *assets]}
		chosen = [a for a in by_id.values() if a.get("selected")]
		others = [a for a in by_id.values() if not a.get("selected")]
		remaining = max(0, MAX_REMEMBERED_IMAGES - len(chosen))
		found[:] = chosen[:MAX_REMEMBERED_IMAGES] + (others[-remaining:] if remaining else [])
	return assets


def render_results(provider: str, results: list[dict]) -> str:
	lines = [
		f"{provider} results — keep the exact id when offering a choice; thumb is for present_ui only. "
		"Use a page url only after any required acquisition. Preserve source, license and attribution."
	]
	for i, p in enumerate(results, 1):
		desc = p["description"][:120] or "(no description)"
		lines.append(
			f"{i}. {desc} — by {p['credit']}, {p['size']}\n   id: {p['id']}\n   {asset_usage(p)}"
			f"\n   thumb: {p['thumb']}"
			f"\n   source: {p.get('source_url') or ''}\n   license: {p.get('license_url') or ''}"
		)
		if p.get("credit_url"):
			lines.append(f"   photographer attribution link: {p['credit_url']}")
	return "\n".join(lines)


def asset_usage(asset: dict) -> str:
	if asset.get("preview_only"):
		return (
			"PREVIEW ONLY — not licensed for publishing; no page URL. Open the original source link, "
			"license/download there, then upload the licensed file manually. Never publish the thumbnail."
		)
	if asset.get("requires_acquisition"):
		return (
			f"Call acquire_asset with this id after the user selects it for use. Original url: {asset['url']}"
		)
	return f"url: {asset['url']}"


def run_acquire_asset(ctx, args: dict) -> str:
	from builder.ai.brief import DesignBrief

	if not getattr(ctx, "page_id", None):
		return "FAILED: A saved page and selected search result are required."
	frappe.get_doc("Builder Page", ctx.page_id).check_permission("write")
	frappe.db.get_value("Builder Page", ctx.page_id, "name", for_update=True)
	brief = DesignBrief(ctx.page_id)
	saved = brief.read()
	asset = next((a for a in saved.get("assets", []) if a.get("id") == args.get("asset_id")), None)
	if not asset or asset.get("selected") is not True:
		return "FAILED: Select this original asset from the saved search results before acquiring it."
	if asset.get("provider") == "Magnific":
		return (
			"PREVIEW ONLY — this call does not purchase or license the image. "
			"Use acquire_paid_asset for the selected original when account entitlement and a media budget "
			"are configured; otherwise license/download and upload manually. "
			f"Source: {asset.get('source_url', '')}"
		)
	if asset.get("preview_only"):
		return (
			"FAILED: "
			+ asset_usage({**asset, "preview_only": True})
			+ f" Source: {asset.get('source_url', '')}"
		)
	if asset.get("provider") != "Unsplash" or not asset.get("id", "").startswith("unsplash:"):
		return "FAILED: Automatic acquisition is supported only for selected Unsplash results."
	if not asset.get("download_tracked"):
		key = frappe.conf.get("unsplash_access_key")
		if not key:
			return "FAILED: Unsplash is not configured on this site."
		try:
			asset.update(track_unsplash_download(asset, key))
		except (requests.RequestException, ValueError):
			return "FAILED: Unsplash download tracking was not confirmed. Do not use the asset yet; retry."
		# Search merging deliberately preserves selected records; acquisition updates the locked record.
		brief.save(saved)
	if (found := getattr(ctx, "found_images", None)) is not None:
		found[:] = [a for a in found if a.get("id") != asset["id"]]
		found.insert(0, asset)
		del found[MAX_REMEMBERED_IMAGES:]
	return render_results(
		"Unsplash — selected use recorded; hotlink the original URL with attribution", [asset]
	)


search_images = Tool(
	name="search_images",
	side="server",
	handler=run_search_images,
	description=(
		"Search stock photo libraries for REAL photographs (products, food, people, places, "
		"textures). Returns original asset IDs, source/license links and thumbnails for "
		"present_ui choices (option.image). Magnific results are PREVIEW ONLY: manual "
		"licensing/download and upload are required; never put previews in a page. Unsplash "
		"requires acquire_asset after user selection for actual use. Other results expose a "
		"page url; preserve attribution and license terms. Use provider to choose a library "
		"or free alternatives to paid previews. Search "
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
			"provider": {"type": "string", "enum": ["auto", "magnific", "pexels", "unsplash", "openverse"]},
		},
		"required": ["query"],
	},
)

acquire_asset = Tool(
	name="acquire_asset",
	side="server",
	handler=run_acquire_asset,
	description=(
		"Record the required Unsplash download event for an original asset explicitly selected "
		"by the user for use on this page. Accepts only a selected id in the saved search inventory. "
		"Never call for search, browsing or displaying choices. Returns the original hotlink and "
		"attribution; does not download a file or buy a license. Magnific acquisition is manual."
	),
	parameters={
		"type": "object",
		"properties": {"asset_id": {"type": "string", "description": "Exact selected search result id."}},
		"required": ["asset_id"],
		"additionalProperties": False,
	},
)

TOOLS = [search_images, acquire_asset]
