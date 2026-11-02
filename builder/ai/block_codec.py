import json
import re
from copy import deepcopy
from typing import ClassVar

import frappe
import yaml
from frappe import _

from builder.utils import to_compact_yaml

STANDARD_ATTRS = {"src", "darkSrc", "alt", "href", "title", "value", "type", "placeholder"}
PRESERVED_FIELDS = (
	"dataKey",
	"dynamicValues",
	"visibilityCondition",
	"editorConfig",
	"componentVersion",
	"originalElement",
	"elementBeforeConversion",
	"draggable",
	"blockClientScript",
	"isRepeaterBlock",
)


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
		icon = custom.get("data-lucide")
		out = {"icon": icon} if icon else {}
		if block.get("element") and not icon:
			out["el"] = block["element"]
		if block.get("blockId"):
			# Editor handle, surfaced as `ref` (NOT `id`) so the model never mistakes
			# it for an HTML id / DOM selector. It is what the edit tools take as block_id.
			out["ref"] = block["blockId"]
		if block.get("blockName"):
			out["name"] = block["blockName"]

		base_styles = block.get("baseStyles") or {}
		if icon:
			base_styles = {k: v for k, v in base_styles.items() if BlockCodec.ICON_STYLE_DEFAULTS.get(k) != v}
			# Explicit unsets prevent expansion from restoring deleted icon defaults.
			for key in (*BlockCodec.ICON_STYLE_DEFAULTS, "width", "height"):
				if key not in (block.get("baseStyles") or {}):
					base_styles[key] = None
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
			out["props"] = deepcopy(block["props"])
		if metadata := {key: deepcopy(block[key]) for key in PRESERVED_FIELDS if key in block}:
			out["meta"] = metadata
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
		if block.get("classes"):
			out["classes"] = block["classes"]
		if block.get("innerHTML") and not icon:
			out["text"] = block["innerHTML"]

		mob = block.get("mobileStyles") or {}
		if mob:
			out["m_style"] = mob

		tab = block.get("tabletStyles") or {}
		if tab and (icon or task_tier == "complex" or depth <= 1):
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
	def expand(node: dict) -> dict:
		if not isinstance(node, dict):
			return node

		# Icon ref: one expansion path — page_writer owns the wrapper defaults and
		# the baked SVG (lazy import; page_writer imports this module at top level).
		if node.get("icon"):
			from builder.ai.page_writer import convert_icon_block

			block = convert_icon_block(node)
		else:
			attrs = node.get("attrs") or {}
			block = {
				"element": node.get("el", "div"),
				"blockName": node.get("name", ""),
				"baseStyles": node.get("style", {}),
				"attributes": {k: v for k, v in attrs.items() if k in STANDARD_ATTRS},
				"customAttributes": {k: v for k, v in attrs.items() if k not in STANDARD_ATTRS},
			}
		block["children"] = [BlockCodec.expand(c) for c in node.get("c") or [] if isinstance(c, dict)]
		for yaml_key, block_key in [
			("id", "blockId"),
			("ref", "blockId"),
			("text", "innerHTML"),
			("m_style", "mobileStyles"),
			("t_style", "tabletStyles"),
			("classes", "classes"),
			("component", "extendedFromComponent"),
			("child_of", "isChildOfComponent"),
			("of", "referenceBlockId"),
			("client_script", "clientScript"),
			("props", "props"),
		]:
			if yaml_key in node:
				block[block_key] = node[yaml_key]
		from builder.ai.page_writer import bind_to_dynamic_values, repeater_data_key

		if isinstance(node.get("bind"), dict):
			block["dynamicValues"] = bind_to_dynamic_values(node["bind"])
		if isinstance(node.get("repeat"), dict):
			repeat = node["repeat"]
			block["isRepeaterBlock"] = True
			block["dataKey"] = {
				"key": repeater_data_key(repeat.get("data")),
				"property": "innerHTML",
				"type": "key",
			}
			if isinstance(repeat.get("item"), dict):
				block["children"] = [BlockCodec.expand(repeat["item"])]

		BlockCodec.restore_metadata(node, block)
		return block

	@staticmethod
	def restore_metadata(node: dict, block: dict):
		metadata = node.get("meta") if isinstance(node.get("meta"), dict) else {}
		for key in PRESERVED_FIELDS:
			if key not in metadata:
				continue
			if key == "dynamicValues" and "bind" in node:
				old = {value.get("property"): value for value in metadata[key] if isinstance(value, dict)}
				for value in block.get(key, []):
					previous = old.get(value.get("property"), {})
					if all(previous.get(field) == value.get(field) for field in ("key", "comesFrom")):
						value.update(deepcopy(previous))
			elif key == "dataKey" and "repeat" in node:
				block[key] = {**deepcopy(metadata[key]), **block.get(key, {})}
			else:
				block[key] = deepcopy(metadata[key])

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

		if isinstance(block, dict) and not (block.get("ref") or block.get("id")):
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
