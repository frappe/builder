"""Keep required asset attribution in the editable page, not only in chat metadata."""

import html
import json

from builder.ai.revisions import digest


def add_asset_credits(root, assets):
	if not isinstance(root, dict) or root.get("element") in ("img", "input", "video"):
		return
	content = json.dumps(root)
	for asset in assets:
		if not asset.get("url") or asset["url"] not in content or asset.get("preview_only"):
			continue
		if asset.get("provider") not in ("Unsplash", "Openverse", "Magnific") and not asset.get(
			"attribution_required"
		):
			continue
		identity = "bob-credit-" + digest(asset.get("original_id") or asset.get("id") or asset["url"])[:12]
		if identity in content:
			continue
		links = []
		for label, url in [
			(
				asset.get("credit") or asset.get("provider"),
				asset.get("credit_url") or asset.get("source_url"),
			),
			(asset.get("license") or "License", asset.get("license_url")),
		]:
			if not url or not url.startswith(("https://", "http://")):
				continue
			links.append(
				f'<a href="{html.escape(url, quote=True)}" rel="noopener noreferrer">{html.escape(str(label))}</a>'
			)
		label = html.escape(asset.get("description") or "Image")
		credit = "; ".join(links) or html.escape(asset.get("credit") or asset.get("provider") or "")
		root.setdefault("children", []).append(
			{
				"blockId": identity,
				"element": "p",
				"blockName": "Image credit",
				"innerHTML": f"{label} — {credit}" + (" (cropped)" if asset.get("original_id") else ""),
				"baseStyles": {"fontSize": "14px", "lineHeight": "1.5", "padding": "8px 24px"},
			}
		)
