import re
from typing import ClassVar

import frappe
from frappe import _

STANDARD_ATTRS = {"src", "darkSrc", "alt", "href", "title", "value", "type", "placeholder"}


class BlockCodec:
	# Defaults the client injects on an icon svg — noise for the model, stripped on re-collapse.
	ICON_STYLE_DEFAULTS: ClassVar[dict[str, str | int]] = {
		"display": "inline-flex",
		"alignItems": "center",
		"justifyContent": "center",
		"lineHeight": "0",
		"flexShrink": 0,
	}

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
			if block.get("blockId"):
				icon["ref"] = block["blockId"]
			if block.get("blockName"):
				icon["name"] = block["blockName"]
			style = {
				k: v
				for k, v in (block.get("baseStyles") or {}).items()
				if BlockCodec.ICON_STYLE_DEFAULTS.get(k) != v
			}
			if style:
				icon["style"] = style
			for key, field in (("mobileStyles", "m_style"), ("tabletStyles", "t_style")):
				if block.get(key):
					icon[field] = block[key]
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
		# `of` = which component-internal block this instance child mirrors; the join
		# key between a component's defaults and the page-side ref that overrides them.
		if block.get("referenceBlockId"):
			out["of"] = block["referenceBlockId"]
		# Behaviour/styles riding on the block itself: js runs per instance with
		# `this` = the block's element and (component_data, props) as arguments;
		# css is @scope'd to the block's subtree.
		client_script = block.get("clientScript") or {}
		if not client_script.get("js") and block.get("blockClientScript"):
			client_script = {"js": block["blockClientScript"]}
		if script := {k: v for k, v in client_script.items() if k in ("js", "css") and v}:
			out["client_script"] = script
		# Props compressed to name -> effective value (declarations on a definition,
		# per-page values on an instance).
		if isinstance(block.get("props"), dict) and block["props"]:
			from builder.builder.doctype.builder_component.builder_component import (
				get_component_prop_values,
			)

			out["props"] = get_component_prop_values(block)
		# Repeaters and bindings read back in the same vocabulary they're written in
		# (repeat/bind) — without them a data-driven block reads as a plain div and
		# its dynamic wiring is invisible.
		data_key = block.get("dataKey")
		if block.get("isRepeaterBlock") and isinstance(data_key, dict) and data_key.get("key"):
			out["repeat"] = {"data": data_key["key"]}
		if bind := {
			dv["property"]: (
				f"props.{dv['key']}"
				if dv.get("comesFrom") == "props"
				else f"component.{dv['key']}"
				if dv.get("comesFrom") == "componentData"
				else dv["key"]
			)
			for dv in block.get("dynamicValues") or []
			if isinstance(dv, dict) and dv.get("property") and dv.get("key")
		}:
			out["bind"] = bind
		if visible := BlockCodec.visible_key(block.get("visibilityCondition")):
			out["bind"] = {**out.get("bind", {}), "visible": visible}
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
			for c in block.get("children") or []
			if isinstance(c, dict)
		]
		if children:
			out["c"] = children

		return out

	@staticmethod
	def visible_key(condition) -> str | None:
		"""A visibilityCondition in the `bind` vocabulary: 'key', 'props.x' or 'component.x'."""
		if isinstance(condition, str):
			return condition or None
		if not isinstance(condition, dict) or not condition.get("key"):
			return None
		prefix = {"props": "props.", "componentData": "component."}.get(condition.get("comesFrom"), "")
		return prefix + condition["key"]

	@staticmethod
	def strip_fences(text: str) -> str:
		text = re.sub(r"^```[a-z]*\s*\n?", "", text.strip())
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
