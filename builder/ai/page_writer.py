"""Server-side YAML → blocks apply path — the authoritative one for ALL turns.

Generation YAML is expanded to the editor's serialized Block shape and persisted
to `draft_blocks` here; the editor canvas receives the expanded tree (same block
ids) and only renders it. The frontend keeps a small port of the conversion
(frontend/src/components/ai/{yaml.ts, normalizeStyles.ts}) purely for the
live streaming PREVIEW while the YAML is still being written — the final apply
always comes from this module.
"""

import json
import re

import frappe
import yaml

from builder.ai.block_codec import BlockCodec
from builder.utils import compact_json

logger = frappe.logger("builder.ai.page_writer")

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
# gridTemplateAreas/gridTemplate: each row is a double-quoted string ("hero hero").
QUOTE_MEANINGFUL = {"content", "quotes", "gridTemplateAreas", "gridTemplate"}

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
		# Unquoted `var(--x, #hex)` in YAML loses everything from " #" on (comment):
		# the value arrives as "var(--x," — valid as a lenient inline style (the editor
		# looks right) but dropped by the compiled stylesheet (published page breaks).
		# Reclose the parens; the lost fallback is redundant (the token itself resolves).
		if "(" in v and v.count("(") > v.count(")"):
			v = v.rstrip(", ")
			v += ")" * (v.count("(") - v.count(")"))
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


# A value that is EXACTLY one moustache ("{{ item.city }}"). On the published page
# such text goes through Jinja and an undefined variable crashes the whole route —
# so generation absorbs these into real bindings instead of shipping them.
MOUSTACHE_BINDING = re.compile(r"^\s*\{\{\s*([A-Za-z_][A-Za-z0-9_.]*)\s*\}\}\s*$")

# Elements that never belong in a block tree: code (doesn't execute in the editor,
# bypasses the script system) and document plumbing. Dropped at conversion.
FORBIDDEN_ELEMENTS = frozenset({"style", "script", "link", "meta", "head", "title", "base", "noscript"})


def absorb_moustache_bindings(block: dict) -> None:
	"""Convert pure-moustache attribute/text values the model wrote into proper
	dynamicValues bindings (prefixes like item./data. normalized away)."""
	for key, value in list((block.get("attributes") or {}).items()):
		if isinstance(value, str) and (m := MOUSTACHE_BINDING.match(value)):
			block.setdefault("dynamicValues", []).append(
				{"key": strip_binding_prefix(m.group(1)), "property": key, "type": "attribute"}
			)
			block["attributes"][key] = ""
	text = block.get("innerHTML")
	if isinstance(text, str) and (m := MOUSTACHE_BINDING.match(text)):
		bound = {dv.get("property") for dv in block.get("dynamicValues") or []}
		if "innerHTML" not in bound:
			block.setdefault("dynamicValues", []).append(
				{"key": strip_binding_prefix(m.group(1)), "property": "innerHTML", "type": "key"}
			)
		block["innerHTML"] = ""


def strip_binding_prefix(key) -> str:
	"""Models habitually write 'item.image' or 'data.merch_items', but the renderer
	resolves binding keys RELATIVE to their context — the loop record inside a
	repeater, the page-data root elsewhere — so those prefixes silently break
	resolution. Normalize here, at the single point keys land, instead of hoping
	prompts prevent it."""
	key = str(key or "").strip()
	for prefix in ("data.", "item.", "row."):
		if key.startswith(prefix):
			return key[len(prefix) :]
	return key


def bind_to_dynamic_values(bind: dict) -> list:
	"""{property: item_key} → dynamicValues entries (the editor's binding shape).
	innerHTML/text bind by content ("key"); anything else binds an HTML attribute."""
	return [
		{"key": strip_binding_prefix(field), "property": "innerHTML", "type": "key"}
		if prop in ("innerHTML", "text")
		else {"key": strip_binding_prefix(field), "property": prop, "type": "attribute"}
		for prop, field in bind.items()
	]


def convert_yaml_block(node, is_root: bool = False) -> dict | None:
	if not isinstance(node, dict):
		return node
	# Icon reference → inline-svg wrapper (see convert_icon_block).
	if node.get("icon"):
		return convert_icon_block(node)
	# Code/document elements never belong in the block tree: scripts don't execute
	# in the editor, style blocks bypass the styling system (Google Fonts load from
	# fontFamily automatically). Drop them — the page script tools are the code path.
	if (node.get("el") or "").strip().lower() in FORBIDDEN_ELEMENTS:
		return None

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
		block["dynamicValues"] = bind_to_dynamic_values(bind)

	children = node.get("c")
	child_blocks = (
		[b for c in children if isinstance(c, dict) and (b := convert_yaml_block(c))]
		if isinstance(children, list)
		else []
	)

	# `repeat` = a static repeater: ONE template child + JSON data. The data array is
	# NOT stored on the block — it lands in the page_data_script shim (build_repeater_
	# data_script); the block keeps only the loop wiring + template child.
	repeat = node.get("repeat")
	if isinstance(repeat, dict) and repeat.get("item"):
		item = convert_yaml_block(repeat["item"])
		if item:
			block["isRepeaterBlock"] = True
			block["dataKey"] = {
				"key": strip_binding_prefix(repeat.get("data")),
				"property": "innerHTML",
				"type": "key",
			}
			child_blocks = [item]

	if child_blocks:
		block["children"] = child_blocks
	elif block.get("extendedFromComponent"):
		block["children"] = component_instance_children(block["extendedFromComponent"])
	absorb_moustache_bindings(block)
	return block


def normalize_component_instances(root: dict | None) -> dict | None:
	"""Repair childless component instances anywhere in a tree. The editor and the
	published renderer both render an instance through the PAGE block's children
	(matched to the component via referenceBlockId) — an instance with no children
	shows NOTHING. add_block and generation attach the skeleton at conversion, but
	run_python lets the model hand-build `{extendedFromComponent: id}` dicts, so
	every tree that reaches the WorkingTree passes through here. Mutates in place."""
	if not isinstance(root, dict):
		return root
	stack = [root]
	while stack:
		block = stack.pop()
		comp_id = block.get("extendedFromComponent")
		if comp_id and not block.get("children"):
			block["children"] = component_instance_children(comp_id)
		else:
			stack.extend(c for c in block.get("children") or [] if isinstance(c, dict))
	return root


def component_instance_children(component_id: str) -> list:
	"""Instance-side child skeletons for a component embed. The published renderer
	(extend_block) renders the PAGE block's children matched to component blocks
	via referenceBlockId — an instance with NO children publishes empty. The editor
	papers over that by syncing children on load, but headless-built pages can be
	published without ever passing through an editor, so embeds must carry the
	skeleton. Content, styles and element stay in the component; the skeleton
	carries linkage only, so component edits keep propagating."""
	raw = frappe.db.get_value("Builder Component", component_id, "block")
	if not raw:
		return []
	try:
		component = json.loads(raw)
	except (json.JSONDecodeError, TypeError):
		return []

	def walk(children) -> list:
		return [
			{
				"blockId": new_block_id(),
				"referenceBlockId": child.get("blockId"),
				"isChildOfComponent": component_id,
				"children": walk(child.get("children")),
			}
			for child in children or []
			if isinstance(child, dict)
		]

	return walk(component.get("children"))


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
	"""Parse a generation YAML document, tolerating fences and model slips —
	one bad line in a 30k-char page must not discard the whole (paid) generation.
	Salvage order: drop the offending line the parser points at (up to 8 times,
	losing a property or a block instead of the page), then fall back to trimming
	a truncated tail (a stream cut off by max_tokens still yields its valid prefix)."""
	text = BlockCodec.strip_fences(yaml_text or "")
	try:
		return yaml.safe_load(text)
	except yaml.YAMLError as exc:
		first_error = exc
		lines = text.split("\n")
		for attempt in range(8):
			mark = getattr(exc, "problem_mark", None)
			if mark is None or not (0 <= mark.line < len(lines)):
				break
			dropped = lines.pop(mark.line)
			try:
				parsed = yaml.safe_load("\n".join(lines))
			except yaml.YAMLError as next_exc:
				exc = next_exc
				continue
			logger.warning(
				"generation YAML salvaged by dropping %d line(s); first error: %s; last dropped: %r",
				attempt + 1,
				str(first_error).replace("\n", " "),
				dropped.strip()[:160],
			)
			return parsed
		logger.warning("generation YAML unsalvageable: %s", str(first_error).replace("\n", " "))
		lines = text.split("\n")
		for i in range(len(lines) - 1, max(0, len(lines) - 12), -1):
			try:
				if parsed := yaml.safe_load("\n".join(lines[:i])):
					return parsed
			except yaml.YAMLError:
				continue
	return None


def unwrap_root(parsed) -> dict | None:
	"""The root block of generated YAML, tolerating the wrappers models emit.
	Expected: the block itself (or a one-item list). Models sometimes wrap it in a
	mapping key — `root:` / `page:` — which used to cost a whole failed generation;
	unwrap one level when the inner value looks like a block."""
	root = parsed[0] if isinstance(parsed, list) and parsed else parsed
	if isinstance(root, dict) and not root.get("el"):
		for key in ("root", "page", "body"):
			inner = root.get(key)
			if isinstance(inner, dict) and inner.get("el"):
				return inner
		if len(root) == 1:
			inner = next(iter(root.values()))
			if isinstance(inner, dict) and inner.get("el"):
				return inner
	return root


def expand_page_yaml(yaml_text: str, is_root: bool = True) -> tuple[list, str]:
	"""Return ([root_block_dict], page_data_script). Empty ([], "") if unparseable.

	`is_root=True` marks the block as the page <body> (root); pass False when
	expanding a reusable component's block tree (it is not a page body)."""
	parsed = parse_generation_yaml(yaml_text)
	if parsed is None:
		return [], ""
	root = unwrap_root(parsed)
	if not isinstance(root, dict) or not root.get("el"):
		return [], ""
	block = convert_yaml_block(root, is_root=is_root)
	if not block:
		return [], ""
	data_script = build_repeater_data_script(parsed)
	return [block], data_script


def load_page_root(page_id: str) -> dict | None:
	"""The page's current root block dict — draft_blocks when present, else the
	published blocks. None when the page is empty or the JSON is invalid."""
	draft, published = frappe.db.get_value("Builder Page", page_id, ["draft_blocks", "blocks"])
	try:
		data = json.loads(draft or published or "")
	except (json.JSONDecodeError, TypeError):
		return None
	if isinstance(data, list):
		data = data[0] if data else None
	return data if isinstance(data, dict) else None


def save_draft_blocks(page_id: str, root_block: dict) -> None:
	"""Persist an edited block tree back to draft_blocks (same shape persist_page
	writes). Used by the headless loop after each round of applied block ops, so a
	cancelled or crashed turn keeps the work done so far."""
	frappe.db.set_value(
		"Builder Page", page_id, "draft_blocks", compact_json([root_block]), update_modified=True
	)
	frappe.db.commit()


def persist_page(page_id: str, yaml_text: str) -> tuple[dict | None, str]:
	"""Expand generation YAML and write it to a Builder Page's draft_blocks (+ the
	repeater data shim). The page stays a DRAFT (published=0). Returns the expanded
	root block and data script — (None, "") if the YAML produced no blocks."""
	blocks, data_script = expand_page_yaml(yaml_text)
	if not blocks:
		return None, ""
	updates = {"draft_blocks": compact_json(blocks)}
	if data_script:
		updates["page_data_script"] = data_script
	# set_value, NOT doc.save: the canvas autosaves the throwaway streamed preview
	# repeatedly throughout a generation, so a timestamp-checked save loses the race
	# arbitrarily often (a single retry was observed losing twice within 200ms). The
	# generated result is authoritative and must land regardless.
	frappe.db.set_value("Builder Page", page_id, updates, update_modified=True)
	frappe.db.commit()
	return blocks[0], data_script
