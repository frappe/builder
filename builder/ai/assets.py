"""Stock-provider contracts. Magnific discovery never acquires or licenses an asset."""

import re
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

import requests

SEARCH_TIMEOUT = 10
MAX_RESULTS = 6
ORIENTATIONS = ("landscape", "portrait", "square")
MAGNIFIC_LICENSE_URL = "https://www.magnific.com/legal/api-services"


class MagnificStock:
	def __init__(self, api_key: str):
		self.api_key = api_key

	def search(self, query: str, orientation: str | None) -> list[dict]:
		response = requests.get(
			"https://api.magnific.com/v1/resources",
			params=self.search_params(query, orientation),
			headers={"x-magnific-api-key": self.api_key},
			timeout=SEARCH_TIMEOUT,
			allow_redirects=False,
		)
		response.raise_for_status()
		if response.status_code != 200:
			raise ValueError("Unexpected Magnific search response")
		return [
			asset for item in response.json().get("data", [])[:MAX_RESULTS] if (asset := self.preview(item))
		]

	def search_params(self, query: str, orientation: str | None) -> dict:
		params = {
			"term": query,
			"limit": MAX_RESULTS,
			"order": "relevance",
			"filters[content_type][photo]": 1,
			"filters[ai-generated][excluded]": 1,
		}
		if orientation in ORIENTATIONS:
			params[f"filters[orientation][{orientation}]"] = 1
		return params

	def preview(self, resource: dict) -> dict | None:
		image = resource.get("image") or {}
		source = image.get("source") or {}
		resource_id = resource.get("id")
		if type(resource_id) is not int or resource_id < 1 or image.get("type") != "photo":
			return None
		if not self.library_url(resource.get("url")) or not https_url(source.get("url")):
			return None
		return {
			"id": f"magnific:{resource_id}",
			"provider_id": str(resource_id),
			"provider": "Magnific",
			"source_url": resource["url"],
			"license_url": MAGNIFIC_LICENSE_URL,
			"provider_licenses": resource.get("licenses") or [],
			"url": "",
			"thumb": source["url"],
			"preview_url": source["url"],
			"preview_only": True,
			"requires_acquisition": True,
			"license_status": "preview_only",
			"description": resource.get("title") or "",
			"credit": (resource.get("author") or {}).get("name") or "Magnific",
			"size": source.get("size") or "",
		}

	def library_url(self, url: str | None) -> bool:
		return https_url(url) and urlsplit(url).hostname in (
			"freepik.com",
			"www.freepik.com",
			"magnific.com",
			"www.magnific.com",
		)


def https_url(url: str | None) -> bool:
	try:
		parts = urlsplit(url or "")
		return parts.scheme == "https" and bool(parts.hostname) and not (parts.username or parts.password)
	except ValueError:
		return False


def unsplash_download_location(asset: dict) -> str:
	photo_id = asset.get("id", "").removeprefix("unsplash:")
	location = asset.get("download_location") or ""
	parts = urlsplit(location)
	if (
		not re.fullmatch(r"[A-Za-z0-9_-]+", photo_id)
		or parts.scheme != "https"
		or parts.netloc != "api.unsplash.com"
		or parts.path != f"/photos/{photo_id}/download"
		or parts.fragment
	):
		raise ValueError("Missing or invalid Unsplash download location; search for the original again.")
	return location


def unsplash_referral_url(url: str | None) -> str:
	if not url:
		return ""
	parts = urlsplit(url)
	params = dict(parse_qsl(parts.query))
	params.update(utm_source="frappe_builder", utm_medium="referral")
	return urlunsplit(parts._replace(query=urlencode(params)))


def track_unsplash_download(asset: dict, key: str) -> dict:
	response = requests.get(
		unsplash_download_location(asset),
		headers={"Authorization": f"Client-ID {key}", "Accept-Version": "v1"},
		timeout=SEARCH_TIMEOUT,
		allow_redirects=False,
	)
	response.raise_for_status()
	if response.status_code != 200:
		raise ValueError("Unsplash did not confirm the download event")
	# Keep photo.urls hotlinks, including ixid; the tracking response is not an image source.
	return {**asset, "download_tracked": True, "requires_acquisition": False}
