"""Server-side YAML → blocks apply path for headless page generation.

The interactive editor turns generation YAML into a page's block tree in the
BROWSER (frontend/src/components/ai/{yaml.ts, toolDispatch.ts, normalizeStyles.ts}).
Fan-out sub-agents run on RQ workers with no browser attached, so this module is a
faithful server-side port of that path: parse the YAML, expand it to the editor's
serialized Block shape, build the repeater data-script shim, and persist it to
`draft_blocks` on the page.

Keep in lockstep with convertYAMLtoBlock / normalizeStyles / buildRepeaterDataScript
in the frontend — a fixture round-trip test guards the two against drift.
"""

import json
import re

import frappe
import yaml

from builder.ai.block_codec import BlockCodec
from builder.utils import compact_json

# --- style normalization — port of frontend/src/components/ai/normalizeStyles.ts ---

# The model camelCases keyword VALUES too (justifyContent: 'spaceBetween'); map back.
KEYWORD_VALUE_FIX = {
	"spaceBetween": "space-between",
	"spaceAround": "space-around",
	"spaceEvenly": "space-evenly",
	"flexStart": "flex-start",
	"flexEnd": "flex-end",
	"rowReverse": "row-reverse",
	"columnReverse": "column-reverse",
	"wrapReverse": "wrap-reverse",
	"preWrap": "pre-wrap",
	"preLine": "pre-line",
	"noWrap": "nowrap",
}

# Length props: a bare number gets 'px'. Whitelist so unitless props (lineHeight,
# fontWeight, opacity, zIndex, flex*) are never touched.
LENGTH_PROPS = {
	"padding",
	"paddingTop",
	"paddingRight",
	"paddingBottom",
	"paddingLeft",
	"margin",
	"marginTop",
	"marginRight",
	"marginBottom",
	"marginLeft",
	"top",
	"right",
	"bottom",
	"left",
	"inset",
	"width",
	"height",
	"minWidth",
	"maxWidth",
	"minHeight",
	"maxHeight",
	"fontSize",
	"gap",
	"rowGap",
	"columnGap",
	"borderRadius",
	"borderWidth",
	"letterSpacing",
	"wordSpacing",
	"textIndent",
	"outlineWidth",
	"flexBasis",
}

# Props where a leading/trailing quote is meaningful CSS — don't strip it.
QUOTE_MEANINGFUL = {"content", "quotes"}

BARE_NUMBER = re.compile(r"^-?\d+(\.\d+)?$")


def kebab_to_camel(text: str) -> str:
	return re.sub(r"-([a-z])", lambda m: m.group(1).upper(), text)


def normalize_value(prop: str, value):
	if prop == "fontFamily" and isinstance(value, str):
		# Bare family name only — strip quotes and any fallback stack.
		return value.split(",")[0].replace("'", "").replace('"', "").strip()
	if isinstance(value, str):
		v = value.strip()
		if prop not in QUOTE_MEANINGFUL:
			v = re.sub(r"^['\"]+", "", v)
			v = re.sub(r"['\"]+$", "", v).strip()
		if v in KEYWORD_VALUE_FIX:
			return KEYWORD_VALUE_FIX[v]
		if prop in LENGTH_PROPS and BARE_NUMBER.match(v) and v != "0":
			return f"{v}px"
		return v
	if isinstance(value, (int, float)) and not isinstance(value, bool):
		if prop in LENGTH_PROPS and value != 0:
			return f"{value}px"
	return value


def normalize_styles(styles) -> dict:
	if not isinstance(styles, dict):
		return {}
	out = {}
	for raw_key, value in styles.items():
		if value is None:
			continue
		# Custom properties (--brand) are arbitrary — pass through untouched.
		if raw_key.startswith("--"):
			out[raw_key] = value
			continue
		# State-prefixed keys (hover:boxShadow) keep the prefix; only the name after
		# the colon is a CSS property to normalize.
		colon = raw_key.find(":")
		prefix = "" if colon == -1 else raw_key[: colon + 1]
		prop = kebab_to_camel(raw_key if colon == -1 else raw_key[colon + 1 :])
		# A gradient belongs in backgroundImage, never the `background` shorthand.
		if prop == "background" and isinstance(value, str) and "gradient(" in value:
			prop = "backgroundImage"
		out[prefix + prop] = normalize_value(prop, value)
	return out


# --- YAML block → serialized editor Block — port of convertYAMLtoBlock/convertIconBlock ---

# Defaults the editor injects on an icon svg wrapper (frontend convertIconBlock).
ICON_WRAPPER_DEFAULTS = {
	"display": "inline-flex",
	"alignItems": "center",
	"justifyContent": "center",
	"lineHeight": "0",
	"flexShrink": 0,
}


def new_block_id() -> str:
	# Mirrors the frontend generateId() (a short random handle). The editor reassigns
	# ids on open, but a stable id lets the headless renderer/preview key off it.
	return frappe.generate_hash(length=9)


def convert_icon_block(node: dict) -> dict:
	name = str(node.get("icon")).strip()
	style = normalize_styles(node.get("style"))
	raw_size = node.get("size") or "24px"
	size = f"{int(raw_size)}px" if re.match(r"^\d+$", str(raw_size)) else str(raw_size)
	base = {**ICON_WRAPPER_DEFAULTS, "width": size, "height": size, **style}
	block = {
		"blockId": new_block_id(),
		"element": "svg",
		"blockName": node.get("name") or f"Icon: {name}",
		"baseStyles": base,
		# The Lucide SVG set lives in the frontend; the server records only the name and
		# the renderer bakes the svg from data-lucide. innerHTML stays empty here.
		"customAttributes": {"data-lucide": name},
		"children": [],
	}
	if isinstance(node.get("attrs"), dict):
		block["attributes"] = node["attrs"]
	mob = normalize_styles(node.get("m_style"))
	if mob:
		block["mobileStyles"] = mob
	tab = normalize_styles(node.get("t_style"))
	if tab:
		block["tabletStyles"] = tab
	if isinstance(node.get("classes"), list) and node["classes"]:
		block["classes"] = node["classes"]
	return block


def convert_yaml_block(node, is_root: bool = False) -> dict:
	if not isinstance(node, dict):
		return node
	# Icon reference → inline-svg wrapper (see convert_icon_block).
	if node.get("icon"):
		return convert_icon_block(node)

	block = {
		"blockId": "root" if is_root else new_block_id(),
		"element": node.get("el") or "div",
	}
	if node.get("name"):
		block["blockName"] = node["name"]
	if is_root:
		block["originalElement"] = "body"

	base = normalize_styles(node.get("style"))
	if base:
		block["baseStyles"] = base
	mob = normalize_styles(node.get("m_style"))
	if mob:
		block["mobileStyles"] = mob
	tab = normalize_styles(node.get("t_style"))
	if tab:
		block["tabletStyles"] = tab
	# Generation dumps every attr into `attributes` (the standard/custom split is a
	# tool-edit concern, not a generation one — matches convertYAMLtoBlock).
	if isinstance(node.get("attrs"), dict) and node["attrs"]:
		block["attributes"] = node["attrs"]
	if isinstance(node.get("classes"), list) and node["classes"]:
		block["classes"] = node["classes"]
	if node.get("text"):
		block["innerHTML"] = node["text"]
	if node.get("component"):
		block["extendedFromComponent"] = node["component"]
	if node.get("child_of"):
		block["isChildOfComponent"] = node["child_of"]

	# `bind` maps a template field → loop-item key. innerHTML/text bind by content;
	# anything else binds an HTML attribute (href, src, …).
	bind = node.get("bind")
	if isinstance(bind, dict) and bind:
		block["dynamicValues"] = [
			{"key": str(field), "property": "innerHTML", "type": "key"}
			if prop in ("innerHTML", "text")
			else {"key": str(field), "property": prop, "type": "attribute"}
			for prop, field in bind.items()
		]

	children = node.get("c")
	child_blocks = (
		[convert_yaml_block(c) for c in children if isinstance(c, dict)] if isinstance(children, list) else []
	)

	# `repeat` = a static repeater: ONE template child + JSON data. The data array is
	# NOT stored on the block — it lands in the page_data_script shim (build_repeater_
	# data_script); the block keeps only the loop wiring + template child.
	repeat = node.get("repeat")
	if isinstance(repeat, dict) and repeat.get("item"):
		block["isRepeaterBlock"] = True
		block["dataKey"] = {"key": str(repeat.get("data") or ""), "property": "innerHTML", "type": "key"}
		child_blocks = [convert_yaml_block(repeat["item"])]

	if child_blocks:
		block["children"] = child_blocks
	return block


# --- repeater data shim — port of collectRepeaterData + buildRepeaterDataScript ---


def collect_repeater_data(node, out: dict) -> None:
	if isinstance(node, list):
		for n in node:
			collect_repeater_data(n, out)
		return
	if not isinstance(node, dict):
		return
	rep = node.get("repeat")
	if isinstance(rep, dict) and rep.get("data") and isinstance(rep.get("items"), list):
		out[str(rep["data"])] = rep["items"]
		collect_repeater_data(rep.get("item"), out)  # a template may nest a repeater
	if isinstance(node.get("c"), list):
		for n in node["c"]:
			collect_repeater_data(n, out)


def build_repeater_data_script(parsed) -> str:
	out: dict = {}
	collect_repeater_data(parsed, out)
	return "\n".join(f"data.{key} = {json.dumps(items, separators=(',', ':'))}" for key, items in out.items())


# --- top level ---


def parse_generation_yaml(yaml_text: str):
	"""Parse a full (non-streaming) generation YAML document, tolerating fences."""
	try:
		return yaml.safe_load(BlockCodec.strip_fences(yaml_text or ""))
	except yaml.YAMLError:
		return None


def expand_page_yaml(yaml_text: str) -> tuple[list, str]:
	"""Return ([root_block_dict], page_data_script). Empty ([], "") if unparseable."""
	parsed = parse_generation_yaml(yaml_text)
	if parsed is None:
		return [], ""
	root = parsed[0] if isinstance(parsed, list) and parsed else parsed
	if not isinstance(root, dict) or not root.get("el"):
		return [], ""
	block = convert_yaml_block(root, is_root=True)
	data_script = build_repeater_data_script(parsed)
	return [block], data_script


def persist_page(page_id: str, yaml_text: str, page_fields: dict | None = None) -> bool:
	"""Expand generation YAML and write it to a Builder Page's draft_blocks (+ the
	repeater data shim). The page stays a DRAFT (published=0). Returns False if the
	YAML produced no blocks."""
	blocks, data_script = expand_page_yaml(yaml_text)
	if not blocks:
		return False

	doc = frappe.get_doc("Builder Page", page_id)
	doc.draft_blocks = compact_json(blocks)
	if data_script:
		doc.page_data_script = data_script
	for key, value in (page_fields or {}).items():
		if value is not None:
			doc.set(key, value)
	doc.save(ignore_permissions=True)
	return True
