import json
import re
from typing import ClassVar

import frappe
import yaml
from frappe import _

from builder.utils import to_compact_yaml

STANDARD_ATTRS = {"src", "alt", "href", "title", "value", "type", "placeholder"}


class BlockCodec:
	# The generation prompt's block vocabulary, in display order: (codec key, gloss).
	# Single source for the field list shown in the prompt (via fields_doc), which
	# used to be a hand-typed sentence. This is the GENERATION vocabulary, so it
	# intentionally omits keys compress() emits only when showing an existing page
	# — ref (the editor handle, documented separately) and component/child_of (the
	# model never authors those). Keep it in sync with compress()/expand() by hand.
	# A gloss of None means the key is self-explanatory.
	FIELD_DOCS = (
		("el", "semantic HTML tag"),
		("name", None),
		("style", "CSS-in-JS"),
		("m_style", "mobile overrides"),
		("t_style", "tablet overrides"),
		("attrs", "HTML attrs; HTML id goes in attrs.id"),
		("text", None),
		("c", "children"),
		("classes", None),
		("icon", "a Lucide icon name — see Icons"),
	)

	# Defaults the client injects on an icon svg — noise for the model, stripped on re-collapse.
	ICON_STYLE_DEFAULTS: ClassVar[dict[str, str | int]] = {
		"display": "inline-flex",
		"alignItems": "center",
		"justifyContent": "center",
		"lineHeight": "0",
		"flexShrink": 0,
	}

	@classmethod
	def fields_doc(cls) -> str:
		"""Comma-joined field list for the prompt, e.g. `el (semantic HTML tag), name, ...`."""
		return ", ".join(f"{key} ({gloss})" if gloss else key for key, gloss in cls.FIELD_DOCS)

	@staticmethod
	def compress(block: dict, depth: int = 0, task_tier: str = "complex") -> dict:
		if not isinstance(block, dict):
			return block

		# Re-collapse a baked Lucide icon back to `icon: <name>` so editing an
		# existing page never ships the full SVG to the model. The rendered SVG
		# lives in innerHTML; data-lucide is the round-trip hint.
		custom = block.get("customAttributes") or {}
		if custom.get("data-lucide"):
			icon = {"icon": custom["data-lucide"]}
			if block.get("blockName"):
				icon["name"] = block["blockName"]
			style = {
				k: v
				for k, v in (block.get("baseStyles") or {}).items()
				if BlockCodec.ICON_STYLE_DEFAULTS.get(k) != v
			}
			if style:
				icon["style"] = style
			return icon

		out = {}
		if block.get("element"):
			out["el"] = block["element"]
		if block.get("blockId"):
			# Editor handle, surfaced as `ref` (NOT `id`) so the model never mistakes
			# it for an HTML id / DOM selector. It is what the edit tools take as block_id.
			out["ref"] = block["blockId"]
		if block.get("blockName"):
			out["name"] = block["blockName"]

		base_styles = block.get("baseStyles") or {}
		if base_styles:
			out["style"] = base_styles

		attrs = block.get("attributes") or {}
		if attrs:
			out["attrs"] = attrs

		custom_attrs = block.get("customAttributes") or {}
		if custom_attrs:
			out["attrs"] = {**out.get("attrs", {}), **custom_attrs}

		if block.get("extendedFromComponent"):
			out["component"] = block["extendedFromComponent"]
		if block.get("isChildOfComponent"):
			out["child_of"] = block["isChildOfComponent"]
		if block.get("classes"):
			out["classes"] = block["classes"]
		if block.get("innerHTML"):
			out["text"] = block["innerHTML"]

		mob = block.get("mobileStyles") or {}
		if mob:
			out["m_style"] = mob

		tab = block.get("tabletStyles") or {}
		if tab and (task_tier == "complex" or depth <= 1):
			out["t_style"] = tab

		children = [
			BlockCodec.compress(c, depth + 1, task_tier)
			for c in block.get("children", [])
			if isinstance(c, dict)
		]
		if children:
			out["c"] = children

		return out

	@staticmethod
	def expand(node: dict) -> dict:
		if not isinstance(node, dict):
			return node

		# Icon ref. The authoritative SVG is baked client-side (frontend has the
		# Lucide set); the server only records the name so the block round-trips.
		if node.get("icon"):
			return {
				"element": "svg",
				"blockName": node.get("name") or f"Icon: {node['icon']}",
				"baseStyles": node.get("style", {}),
				"attributes": {},
				"customAttributes": {"data-lucide": node["icon"]},
				"children": [],
				"innerHTML": "",
			}

		attrs = node.get("attrs", {})
		standard_attrs = {k: v for k, v in attrs.items() if k in STANDARD_ATTRS}
		custom_attrs = {k: v for k, v in attrs.items() if k not in STANDARD_ATTRS}

		block = {
			"element": node.get("el", "div"),
			"blockName": node.get("name", ""),
			"baseStyles": node.get("style", {}),
			"attributes": standard_attrs,
			"customAttributes": custom_attrs,
			"children": [BlockCodec.expand(c) for c in node.get("c", []) if isinstance(c, dict)],
		}
		for yaml_key, block_key in [
			("id", "blockId"),
			("text", "innerHTML"),
			("m_style", "mobileStyles"),
			("t_style", "tabletStyles"),
			("classes", "classes"),
			("component", "extendedFromComponent"),
			("child_of", "isChildOfComponent"),
		]:
			if yaml_key in node:
				block[block_key] = node[yaml_key]

		return block

	@staticmethod
	def extract_block_id(block_context: str) -> str | None:
		try:
			data = json.loads(block_context)
			if isinstance(data, list):
				data = data[0] if data else {}
			return data.get("blockId") if isinstance(data, dict) else None
		except Exception:
			return None

	@staticmethod
	def strip_context(block_context: str, task_tier: str, task_type: str | None = None) -> str:
		try:
			data = json.loads(block_context)
		except (json.JSONDecodeError, TypeError):
			return block_context

		if isinstance(data, list):
			data = data[0] if data else {}
		if not isinstance(data, dict):
			return block_context

		if task_type == "rewrite_text":
			return data.get("innerHTML") or data.get("innerText") or ""
		if task_type == "replace_image":
			attrs = data.get("attributes", {})
			return to_compact_yaml({"src": attrs.get("src", ""), "alt": attrs.get("alt", "")})
		return to_compact_yaml([BlockCodec.compress(data, 0, task_tier)])

	@staticmethod
	def parse_blocks(content: str) -> dict:
		parsed = yaml.safe_load(BlockCodec.strip_fences(content))
		if isinstance(parsed, dict):
			block = parsed
		elif isinstance(parsed, list):
			block = parsed[0] if parsed else {}
		else:
			raise ValueError("Not a valid block object")

		if not block:
			raise ValueError("No valid blocks in response")

		if isinstance(block, dict) and not block.get("id"):
			block["id"] = "root"

		return BlockCodec.expand(block)

	@staticmethod
	def strip_fences(text: str) -> str:
		text = re.sub(r"^```(?:yaml|json)?\s*\n?", "", text.strip())
		return re.sub(r"\n?```\s*$", "", text).strip()

	@staticmethod
	def validate_image_data(image_data: str) -> str:
		if not image_data.startswith("data:image/"):
			frappe.throw(_("Invalid image data: must be a base64-encoded image data URL"))
		if ";base64," not in image_data:
			frappe.throw(_("Invalid image data: must be a base64-encoded data URL"))
		if len(image_data) > 7 * 1024 * 1024:
			frappe.throw(_("Image is too large. Please use an image smaller than 5 MB."))
		return image_data

	@staticmethod
	def truncate_for_log(value: str, limit: int = 1200) -> str:
		if not value:
			return ""
		if len(value) <= limit:
			return value
		return f"{value[:limit]}... [truncated {len(value) - limit} chars]"
