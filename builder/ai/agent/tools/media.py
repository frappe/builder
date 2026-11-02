import json

from builder.ai.agent.registry import Tool


def generate_artwork(ctx, args):
	from builder.ai.media import generate_image

	asset = generate_image(
		ctx.page_id, args["prompt"], args.get("purpose", "artwork"), args.get("source_asset")
	)
	ctx.found_images.insert(0, asset)
	return json.dumps(asset)


def transform_asset(ctx, args):
	from builder.ai.media import crop_asset

	asset = crop_asset(
		ctx.page_id,
		args["asset_id"],
		args["width"],
		args["height"],
		args.get("focal_x", 0.5),
		args.get("focal_y", 0.5),
	)
	ctx.found_images.insert(0, asset)
	return json.dumps(asset)


def prepare_upload(ctx, args):
	from builder.ai.workspace import classify_asset, prepare_upload

	classify_asset(ctx.page_id, args["asset_id"], args["role"])
	state = prepare_upload(ctx.page_id, args["asset_id"])
	return json.dumps(next(asset for asset in state["assets"] if asset["id"] == args["asset_id"]))


def request_stock(ctx, args):
	import frappe

	from builder.ai.agent.pending import request_confirmation
	from builder.ai.media import selected_asset

	asset = selected_asset(ctx.page_id, args["asset_id"])
	ceiling = (frappe.conf.get("bob_stock_entitlement") or {}).get("max_download_cost_usd")
	if not ceiling:
		return "FAILED: no paid-stock entitlement or cost ceiling configured. Offer a free library or upload."
	return request_confirmation(
		ctx,
		"acquire_paid_asset",
		f"Acquire this {asset['provider']} original? Up to ${ceiling} will be reserved from this project's media budget.",
		{"page_id": ctx.page_id, "asset_id": asset["id"]},
	)


def contact_sheet(ctx, args):
	import base64
	import io

	from PIL import Image, ImageDraw

	from builder.ai.media import download_image, raster, save_raster
	from builder.ai.revisions import digest

	identities = args["asset_ids"]
	assets = [asset for asset in ctx.found_images if asset.get("id") in identities]
	if not 1 <= len(assets) <= 6:
		return "FAILED: choose one to six known assets."
	image = Image.new("RGB", (900, ((len(assets) + 2) // 3) * 250), "#f6f6f6")
	draw = ImageDraw.Draw(image)
	for i, asset in enumerate(assets):
		url = asset.get("thumb") or asset.get("url")
		if url.startswith("/"):
			import frappe

			file = frappe.get_doc("File", {"file_url": url})
			file.check_permission("read")
			photo = raster(file.get_content())
		else:
			photo = raster(download_image(url))
		photo.thumbnail((284, 210))
		x, y = (i % 3) * 300 + 8, (i // 3) * 250 + 8
		image.paste(photo, (x, y))
		draw.text(
			(x, y + 214), f"{i + 1}. {asset['provider']} {asset.get('provider_id', '')}", fill="#242424"
		)
	buffer = io.BytesIO()
	image.save(buffer, "WEBP", quality=80)
	content = buffer.getvalue()
	value = save_raster(ctx.page_id, content, digest(identities), private=True)
	ctx.pending_images.append(
		{
			"caption": "Asset contact sheet, numbered in this order: "
			+ ", ".join(asset["id"] for asset in assets),
			"data_url": "data:image/webp;base64," + base64.b64encode(content).decode(),
		}
	)
	return json.dumps({**value, "preview_only": True, "asset_ids": [asset["id"] for asset in assets]})


TOOLS = [
	Tool(
		name="prepare_uploaded_asset",
		side="server",
		handler=prepare_upload,
		description="Use an uploaded raster original on the published site only when the user intended it as content, logo, product or team photography. Preserves the original bytes and identity; creates a public page asset. Do not use for reference screenshots or confidential images. The user can correct roles in the Assets workspace.",
		parameters={
			"type": "object",
			"properties": {
				"asset_id": {"type": "string"},
				"role": {"enum": ["content", "logo", "product", "team"]},
			},
			"required": ["asset_id", "role"],
		},
	),
	Tool(
		name="generate_artwork",
		side="server",
		handler=generate_artwork,
		description="Generate one cached raster artwork or explicitly labelled design concept, or edit an acquired reference. Requires configured image provider and budget; uses a low-quality draft first. Use only when original imagery helps the brief. Rendered native direction previews are cheaper and editable. Never put a concept screenshot on the final page.",
		parameters={
			"type": "object",
			"properties": {
				"prompt": {"type": "string", "maxLength": 8000},
				"purpose": {"enum": ["artwork", "concept"]},
				"source_asset": {"type": "string"},
			},
			"required": ["prompt"],
		},
	),
	Tool(
		name="transform_asset",
		side="server",
		handler=transform_asset,
		description="Create a cached WebP crop from a selected acquired/uploaded original. Supply a focal point for mobile art direction. Keeps the original and its attribution. Cannot transform previews or no-derivatives imagery.",
		parameters={
			"type": "object",
			"properties": {
				"asset_id": {"type": "string"},
				"width": {"type": "integer", "minimum": 64, "maximum": 2560},
				"height": {"type": "integer", "minimum": 64, "maximum": 2560},
				"focal_x": {"type": "number", "minimum": 0, "maximum": 1},
				"focal_y": {"type": "number", "minimum": 0, "maximum": 1},
			},
			"required": ["asset_id", "width", "height"],
		},
	),
	Tool(
		name="acquire_paid_asset",
		side="terminal",
		handler=request_stock,
		description="Ask the user to acquire a selected Magnific stock original using the site's configured API entitlement and budget. Persists an acquisition receipt and downloads the actual raster original only after Apply. Never licenses search previews silently.",
		parameters={
			"type": "object",
			"properties": {"asset_id": {"type": "string"}},
			"required": ["asset_id"],
		},
	),
	Tool(
		name="asset_contact_sheet",
		side="server",
		handler=contact_sheet,
		description="Compare up to six known images together in one raster contact sheet for coherent subject, light, palette and framing. It is a private preview, never a final-page asset.",
		parameters={
			"type": "object",
			"properties": {
				"asset_ids": {"type": "array", "items": {"type": "string"}, "minItems": 1, "maxItems": 6}
			},
			"required": ["asset_ids"],
		},
	),
]
