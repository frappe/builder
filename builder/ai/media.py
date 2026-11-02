"""Budgeted raster artwork, licensed originals and reusable image renditions."""

import base64
import io
import json
from decimal import Decimal
from urllib.parse import urlsplit

import frappe
import requests
from PIL import Image, ImageOps

from builder.ai.artifacts import Artifact
from builder.ai.brief import DesignBrief
from builder.ai.revisions import digest
from builder.public_fetch import public_session

MAX_DOWNLOAD_BYTES = 20 * 1024 * 1024


def raster(content: bytes):
	if len(content) > MAX_DOWNLOAD_BYTES:
		raise ValueError("Image exceeds 20 MB")
	image = Image.open(io.BytesIO(content))
	if image.format not in ("PNG", "JPEG", "WEBP") or image.width * image.height > 40_000_000:
		raise ValueError("Use a PNG, JPEG or WebP image under 40 megapixels")
	image.load()
	return ImageOps.exif_transpose(image).convert("RGB")


def download_image(url: str) -> bytes:
	with public_session() as session, session.get(url, timeout=(10, 40), stream=True) as response:
		response.raise_for_status()
		data = bytearray()
		for chunk in response.iter_content(65536):
			data.extend(chunk)
			if len(data) > MAX_DOWNLOAD_BYTES:
				raise ValueError("Image download exceeds 20 MB")
		raster(bytes(data))
		return bytes(data)


def asset_content(asset: dict) -> bytes:
	url = asset.get("url") or ""
	if asset.get("preview_only") or asset.get("requires_acquisition"):
		raise ValueError("Acquire the original before transforming it")
	if url.startswith(("/files/", "/private/files/")):
		file = frappe.get_doc("File", {"file_url": url})
		file.check_permission("read")
		return file.get_content()
	if asset.get("provider") == "Unsplash":
		raise ValueError("Keep Unsplash hotlinks; use object-position for its focal point")
	return download_image(url)


def save_raster(page: str, content: bytes, identity: str, private=False) -> dict:
	from frappe.utils.file_manager import save_file

	image = raster(content)
	image.thumbnail((2560, 2560))
	buffer = io.BytesIO()
	image.save(buffer, "WEBP", quality=88)
	file = save_file(
		f"bob-image-{identity[:24]}.webp", buffer.getvalue(), "Builder Page", page, is_private=int(private)
	)
	return {
		"url": file.file_url,
		"thumb": file.file_url,
		"size": f"{image.width}x{image.height}",
		"width": image.width,
		"height": image.height,
	}


def selected_asset(page: str, identity: str) -> dict:
	asset = next(
		(a for a in DesignBrief(page).read().get("assets", []) if DesignBrief.asset_key(a) == identity), None
	)
	if not asset or not asset.get("selected"):
		raise ValueError("Select an asset from this project's library first")
	return asset


class MediaRequest:
	def __init__(self, page, kind, spec, ceiling):
		self.page, self.kind, self.spec = page, kind, spec
		self.ceiling = Decimal(str(ceiling or 0))
		self.key = digest({"kind": kind, "spec": spec})
		self.name = Artifact.key(page, "media_request", self.key)

	def cached(self):
		frappe.get_doc("Builder Page", self.page).check_permission("write")
		if frappe.db.exists("Builder AI Artifact", self.name):
			doc, value = Artifact.get(self.name, self.page, "media_request")
			if doc.status == "complete":
				return value["asset"]
		return None

	def reserve(self):
		frappe.get_doc("Builder Page", self.page).check_permission("write")
		frappe.db.get_value("DocType", "Builder Settings", "name", for_update=True)
		frappe.db.get_value("Builder Page", self.page, "name", for_update=True)
		if frappe.db.exists("Builder AI Artifact", self.name):
			doc, value = Artifact.get(self.name, self.page, "media_request")
			if doc.status == "complete":
				return value["asset"]
			if (
				doc.status != "reconciled"
				or (value.get("reconciliation") or {}).get("outcome") != "not_charged"
			):
				raise ValueError(
					"This media request needs reconciliation before retrying; it may already have been charged"
				)
			self.prior_reconciliations = [*value.get("prior_reconciliations", []), value["reconciliation"]]
		budget = Decimal(str(frappe.conf.get("bob_media_budget_usd") or 0))
		if not self.ceiling.is_finite() or self.ceiling <= 0 or not budget.is_finite():
			raise ValueError(
				"Configure a conservative per-request cost ceiling and project media budget first"
			)
		rows = frappe.get_all(
			"Builder AI Artifact", filters={"page": self.page, "kind": "media_request"}, pluck="payload_json"
		)
		spent = sum(Decimal(str(json.loads(row).get("reserved_usd", 0))) for row in rows)
		if spent + self.ceiling > budget:
			raise ValueError(
				"This project's media budget is exhausted. Reuse an image or raise its configured budget."
			)
		daily_budget = Decimal(str(frappe.conf.get("bob_media_daily_budget_usd") or budget))
		today = frappe.utils.nowdate()
		daily = frappe.get_all(
			"Builder AI Artifact",
			filters={"kind": "media_request", "modified": [">=", today]},
			pluck="payload_json",
		)
		if (
			not daily_budget.is_finite()
			or sum(Decimal(str(json.loads(row).get("reserved_usd", 0))) for row in daily) + self.ceiling
			> daily_budget
		):
			raise ValueError("The site's daily media reservation budget is exhausted")
		self.value = {
			"label": self.kind,
			"spec": self.spec,
			"reserved_usd": str(self.ceiling),
			"usage": None,
			"actual_cost_usd": None,
			"prior_reconciliations": getattr(self, "prior_reconciliations", []),
		}
		Artifact.save(self.page, "media_request", self.value, identity=self.key, status="pending")
		frappe.db.commit()
		return None

	def finish(self, asset, usage=None, evidence=None):
		frappe.db.get_value("Builder Page", self.page, "name", for_update=True)
		doc, _ = Artifact.get(self.name, self.page, "media_request")
		if doc.status != "pending":
			raise ValueError(
				"This request was reconciled while the provider was responding. Check the receipt before retrying."
			)
		self.value.update({"asset": asset, "usage": usage, "evidence": evidence})
		Artifact.save(self.page, "media_request", self.value, identity=self.key, status="complete")
		# Acquired originals replace preview records; ordinary search merging deliberately does not.
		brief = DesignBrief(self.page)
		frappe.db.get_value("Builder Page", self.page, "name", for_update=True)
		state = brief.read()
		state["assets"] = [asset] + [a for a in state.get("assets", []) if a.get("id") != asset["id"]]
		brief.save(state)
		return asset


def generate_image(page: str, prompt: str, purpose="artwork", source_asset=None):
	model = frappe.conf.get("bob_image_model")
	key = frappe.conf.get("bob_image_api_key")
	if not model or not key:
		raise ValueError(
			"Image generation is not configured. Use uploaded or stock imagery, or rendered layout previews."
		)
	if purpose not in ("artwork", "concept") or not isinstance(prompt, str) or not 1 <= len(prompt) <= 8000:
		raise ValueError("Supply an artwork/concept prompt under 8000 characters")
	spec = {
		"model": model,
		"prompt": prompt,
		"purpose": purpose,
		"source_asset": source_asset,
		"quality": "low",
		"size": "1024x1024",
	}
	source = selected_asset(page, source_asset) if source_asset else None
	if source:
		spec["source_url"] = source.get("url")
	request = MediaRequest(page, "generated_image", spec, frappe.conf.get("bob_image_max_cost_usd"))
	if cached := request.cached():
		return cached
	original = asset_content(source) if source else None
	if original:
		buffer = io.BytesIO()
		raster(original).save(buffer, "WEBP", quality=90)
		original = buffer.getvalue()
	if cached := request.reserve():
		return cached
	params = {key: spec[key] for key in ("model", "prompt", "quality", "size")}
	params.update(n=1, output_format="webp")
	kwargs = (
		{"data": params, "files": {"image": ("reference.webp", original, "image/webp")}}
		if original
		else {"json": params}
	)
	response = requests.post(
		"https://api.openai.com/v1/images/" + ("edits" if original else "generations"),
		headers={"Authorization": f"Bearer {key}"},
		timeout=(15, 180),
		**kwargs,
	)
	response.raise_for_status()
	result = response.json()
	content = base64.b64decode(result["data"][0]["b64_json"], validate=True)
	asset = {
		"id": f"generated:{request.key}",
		"provider": "Generated",
		"description": prompt[:120],
		"credit": "AI-generated artwork",
		"selected": True,
		"preview_only": purpose == "concept",
		"requires_acquisition": False,
		"purpose": purpose,
		"receipt": request.name,
		**save_raster(page, content, request.key, private=purpose == "concept"),
	}
	return request.finish(
		asset,
		usage=result.get("usage"),
		evidence={"request_id": response.headers.get("x-request-id"), "model": model},
	)


def acquire_paid_asset(payload: dict):
	page, identity = payload["page_id"], payload["asset_id"]
	asset = selected_asset(page, identity)
	entitlement = frappe.conf.get("bob_stock_entitlement") or {}
	if not (
		frappe.conf.get("magnific_api_key")
		and entitlement.get("approved")
		and entitlement.get("license_url")
		and entitlement.get("account_reference")
	):
		raise ValueError(
			"Configure your Magnific API entitlement, license reference and cost ceiling before acquiring originals"
		)
	if asset.get("provider") != "Magnific" or not identity.removeprefix("magnific:").isdigit():
		raise ValueError("This acquisition path accepts Magnific photographs only")
	request = MediaRequest(
		page, "stock_download", {"asset_id": identity}, entitlement.get("max_download_cost_usd")
	)
	if cached := request.reserve():
		return f"Already acquired: {cached['url']}"
	response = requests.get(
		f"https://api.magnific.com/v1/resources/{identity.split(':')[1]}/download",
		params={"image_size": "original"},
		headers={"x-magnific-api-key": frappe.conf.magnific_api_key},
		timeout=(10, 30),
		allow_redirects=False,
	)
	response.raise_for_status()
	if response.status_code != 200:
		raise ValueError("The provider did not confirm acquisition")
	data = response.json()["data"]
	# signed_url is a preview in the provider's schema. Only data.url is the original.
	content = download_image(data["url"])
	original = {
		**asset,
		**save_raster(page, content, request.key),
		"preview_only": False,
		"requires_acquisition": False,
		"license_status": "configured_account_entitlement",
		"receipt": request.name,
	}
	request.finish(
		original,
		evidence={
			"provider_response": data,
			"entitlement": entitlement,
			"acquired_on": str(frappe.utils.now_datetime()),
		},
	)
	return f"Acquired the original under the configured account entitlement: {original['url']}. Preserve its credit and license reference."


def crop_asset(page, identity, width, height, focal_x=0.5, focal_y=0.5):
	asset = selected_asset(page, identity)
	if "nd" in (asset.get("license") or "").lower().split("-"):
		raise ValueError("This license does not permit derivatives")
	width, height = int(width), int(height)
	if not (64 <= width <= 2560 and 64 <= height <= 2560 and 0 <= focal_x <= 1 and 0 <= focal_y <= 1):
		raise ValueError("Use dimensions 64–2560 and focal coordinates 0–1")
	key = digest(
		{"asset": identity, "url": asset["url"], "size": [width, height], "focus": [focal_x, focal_y]}
	)
	name = Artifact.key(page, "rendition", key)
	if frappe.db.exists("Builder AI Artifact", name):
		return Artifact.get(name, page, "rendition")[1]
	image = ImageOps.fit(raster(asset_content(asset)), (width, height), centering=(focal_x, focal_y))
	buffer = io.BytesIO()
	image.save(buffer, "WEBP", quality=88)
	rendered = {
		**asset,
		**save_raster(page, buffer.getvalue(), key),
		"id": f"rendition:{key}",
		"original_id": identity,
		"focal_point": [focal_x, focal_y],
	}
	Artifact.save(page, "rendition", rendered, identity=key)
	DesignBrief(page).remember_assets([rendered])
	return rendered


@frappe.whitelist(methods=["POST"])
def reconcile_request(
	page_id: str, request_id: str, outcome: str, evidence: str, file_url: str | None = None
):
	"""Resolve an ambiguous charge from provider evidence, never automatically retry it."""
	frappe.only_for("System Manager")
	frappe.db.get_value("Builder Page", page_id, "name", for_update=True)
	doc, value = Artifact.get(request_id, page_id, "media_request")
	if doc.status != "pending" or outcome not in ("not_charged", "acquired", "charged_without_asset"):
		raise ValueError("Choose a valid reconciliation outcome for a pending request")
	if frappe.utils.time_diff_in_seconds(frappe.utils.now_datetime(), doc.modified) < 300:
		raise ValueError(
			"The provider request may still be running. Wait five minutes before reconciling it."
		)
	if not isinstance(evidence, str) or not 10 <= len(evidence) <= 2000:
		raise ValueError("Record the provider receipt or support confirmation")
	value["reconciliation"] = {
		"outcome": outcome,
		"evidence": evidence,
		"by": frappe.session.user,
		"on": str(frappe.utils.now_datetime()),
	}
	if outcome == "not_charged":
		value["reserved_usd"] = "0"
	elif outcome == "acquired":
		file = frappe.get_doc("File", {"file_url": file_url})
		file.check_permission("read")
		if file.attached_to_doctype != "Builder Page" or file.attached_to_name != page_id:
			raise ValueError("Upload the recovered original to this page first")
		raster(file.get_content())
		value["asset"] = {
			"id": f"recovered:{request_id}",
			"url": file.file_url,
			"thumb": file.file_url,
			"provider": "Recovered",
			"selected": True,
			"receipt": request_id,
			"preview_only": False,
		}
		DesignBrief(page_id).remember_assets([value["asset"]])
	doc.payload_json = json.dumps(value)
	doc.status = "complete" if outcome == "acquired" else "reconciled"
	doc.save(ignore_permissions=True)
	return {"status": doc.status, "outcome": outcome}
