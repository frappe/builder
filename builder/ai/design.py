"""Cached raster previews rendered from the same editable blocks that become the draft."""

import copy
import html
import json

import frappe
import yaml
from jinja2 import DictLoader
from jinja2.sandbox import SandboxedEnvironment

from builder.ai.artifacts import Artifact
from builder.ai.brief import TEXT_FIELDS, DesignBrief, validate_asset_usage
from builder.ai.design_recipes import compose_direction
from builder.ai.page_writer import (
	convert_yaml_block,
	expand_page_yaml,
	save_draft_blocks,
	validate_page_candidate,
)
from builder.ai.revisions import digest, page_revision, require_revision


def brief_revision(brief: dict) -> str:
	return digest(
		{
			"brief": {
				key: brief.get(key)
				for key in (*TEXT_FIELDS, "facts", "decisions")
				if key != "visual_direction"
			},
			"assets": [
				{
					key: asset.get(key)
					for key in (
						"id",
						"url",
						"selected",
						"preview_only",
						"requires_acquisition",
						"focal_point",
					)
				}
				for asset in brief.get("assets", [])
				if asset.get("selected")
			],
		}
	)


def candidate_markup(root: dict) -> str:
	from builder.builder.doctype.builder_page.builder_page import get_block_html, get_google_font_urls
	from builder.builder.doctype.builder_token.builder_token import get_variables_css
	from builder.utils import combine, to_safe_json
	from builder.utils import hash as style_hash

	content, style, fonts, _ = get_block_html(copy.deepcopy([root]))
	# Native blocks use Jinja for props; static previews must not inherit Frappe's DB helpers.
	environment = SandboxedEnvironment(loader=DictLoader({"templates/generators/webpage_scripts.html": ""}))
	environment.globals.clear()
	environment.filters.update(hash=style_hash, combine=combine, to_safe_json=to_safe_json)
	content = environment.from_string(content).render()
	style = environment.from_string(style).render()
	links = "".join(
		f'<link rel="stylesheet" href="{html.escape(url, quote=True)}">'
		for url in get_google_font_urls(fonts)
	)
	return f'<!doctype html><html lang="en" data-prefers-color-scheme="light"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><base href="{html.escape(frappe.utils.get_url(), quote=True)}/"><link rel="stylesheet" href="/assets/builder/reset.css">{links}<style>body{{margin:0}}{get_variables_css()}</style>{style}</head><body>{content}</body></html>'


def save_preview(page: str, root: dict, identity: str, viewport: str) -> str:
	from frappe.utils.file_manager import save_file

	from builder.html_preview_image import render_full_page

	width, height = (1280, 900) if viewport == "desktop" else (390, 844)
	image = render_full_page(candidate_markup(root), width=width, height=height, max_height=1800)
	return save_file(
		f"bob-direction-{identity}-{viewport}.webp", image, "Builder Page", page, is_private=1
	).file_url


def resolve_image(brief: dict, asset_id: str | None) -> str | None:
	if not asset_id:
		return None
	asset = next((a for a in brief.get("assets", []) if DesignBrief.asset_key(a) == asset_id), None)
	if not asset or asset.get("preview_only") or asset.get("requires_acquisition"):
		raise ValueError("Select an acquired or uploaded original before using it in a direction")
	return asset.get("url")


def create_direction(page: str, spec: dict, run: str | None = None) -> dict:
	frappe.get_doc("Builder Page", page).check_permission("write")
	brief = DesignBrief(page).read()
	key = digest(
		{"spec": spec, "brief": brief_revision(brief), "page_revision": page_revision(page), "renderer": 4}
	)
	identity = Artifact.key(page, "design", key)
	if frappe.db.exists("Builder AI Artifact", identity):
		_, saved = Artifact.get(identity, page, "design")
		return direction_option(identity, saved)
	if spec.get("yaml"):
		blocks, data_script = expand_page_yaml(spec["yaml"], strict=True)
		if data_script or not blocks:
			raise ValueError(
				"A direction is a static layout; use acquired assets and real copy, without data scripts"
			)
		root = blocks[0]
	else:
		root = convert_yaml_block(
			compose_direction(spec, brief, resolve_image(brief, spec.get("asset_id"))), is_root=True
		)
	from builder.ai.credits import add_asset_credits

	add_asset_credits(root, brief.get("assets", []))
	validate_page_candidate(root)
	validate_asset_usage(brief.get("assets", []), root)
	if any(
		word in json.dumps(root) for word in ('"clientScript"', '"element": "script"', '"element": "iframe"')
	):
		raise ValueError(
			"Design previews use static editable blocks; add behavior after choosing a direction"
		)
	value = {
		"label": str(spec.get("label") or "Direction")[:120],
		"rationale": str(spec.get("rationale") or "")[:500],
		"brief_revision": brief_revision(brief),
		"page_revision": page_revision(page),
		"blocks": root,
		"asset_ids": [spec["asset_id"]] if spec.get("asset_id") else [],
		"spec": spec,
		"desktop": save_preview(page, root, key[:12], "desktop"),
		"mobile": save_preview(page, root, key[:12], "mobile"),
		"preview_kind": "rendered_layout",
	}
	doc = Artifact.save(page, "design", value, identity=key, run=run)
	return direction_option(doc.name, value)


def direction_option(identity: str, value: dict) -> dict:
	return {
		"label": value["label"],
		"description": value.get("rationale", ""),
		"variant_id": identity,
		"image": value["desktop"],
		"mobile_image": value["mobile"],
		"preview_kind": value["preview_kind"],
	}


def apply_direction(ctx, identity: str) -> str:
	doc, value = Artifact.get(identity, ctx.page_id, "design")
	brief = DesignBrief(ctx.page_id)
	state = brief.read()
	if value["brief_revision"] != brief_revision(state):
		raise ValueError("The brief changed. Refresh the direction previews so the selected page matches it.")
	require_revision(ctx.page_id, value["page_revision"])
	validate_asset_usage(state.get("assets", []), value["blocks"])
	ctx.ensure_revert_snapshot()
	save_draft_blocks(ctx.page_id, value["blocks"])
	ctx.queue_client_op({"tool_name": "set_page_blocks", "args": {"blocks": value["blocks"]}})
	state.update({"selected_variant": identity, "stage": "build", "visual_direction": value["label"]})
	brief.save(state)
	doc.status = "selected"
	doc.save(ignore_permissions=True)
	return "Selected direction applied as editable blocks. Extend this design without replacing approved sections or assets."
