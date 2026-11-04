"""Server-side markup -> blocks apply path, the authoritative one for ALL turns.

Generated markup (builder/ai/markup.py) is expanded to the editor's serialized
Block shape and persisted to `draft_blocks` here; the editor canvas receives the
expanded tree (same block ids) and only renders it. While a page is still being
written, the generation step parses the partial markup here too and streams the
expanded tree as the live preview, so the frontend carries no parser of its own.
"""

import json
import re

import frappe

from builder.ai.block_codec import BlockCodec
from builder.ai.lucide import lucide_svg
from builder.utils import compact_json

logger = frappe.logger("builder.ai.page_writer")

# --- style normalization (frontend twin: components/ai/normalizeStyles.ts) ---

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
		v = value.replace("'", "").replace('"', "").strip()
		# A font TOKEN handle: return var(--id) clean. Never split on comma first —
		# the model sometimes bakes a fallback INSIDE the parens (var(--id, Inter)),
		# and splitting there truncates the var() and drops its closing ) (invalid
		# CSS → the family silently falls back to serif on the published page).
		if match := re.search(r"var\(\s*(--[A-Za-z0-9_-]+)", v):
			return f"var({match.group(1)})"
		# Literal family: bare name only — strip any fallback stack.
		return v.split(",")[0].strip()
	if isinstance(value, str):
		v = value.strip()
		if prop not in QUOTE_MEANINGFUL:
			v = re.sub(r"^['\"]+", "", v)
			v = re.sub(r"['\"]+$", "", v).strip()
		if v in KEYWORD_VALUE_FIX:
			return KEYWORD_VALUE_FIX[v]
		if prop in LENGTH_PROPS and BARE_NUMBER.match(v) and v != "0":
			return f"{v}px"
		# A cut-off value (`var(--x, #hex` with its tail lost) arrives unclosed:
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


# --- markup node -> serialized editor Block ---

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
		# Bake the SVG here: this tree is authoritative (the canvas reloads it and
		# the published page renders it); data-lucide stays the round-trip hint.
		"customAttributes": {"data-lucide": name},
		"innerHTML": lucide_svg(name, node.get("stroke") or 2),
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


# Key prefixes that SELECT a binding source: a component instance's props, or the
# component data script's output. Anything else resolves against page data.
BINDING_SOURCES = {"props.": "props", "component.": "componentData"}


def binding_entry(prop: str, field) -> dict:
	key = str(field or "").strip()
	comes_from = None
	for prefix, source in BINDING_SOURCES.items():
		if key.startswith(prefix):
			key = key[len(prefix) :]
			comes_from = source
			break
	else:
		key = strip_binding_prefix(key)
	entry = (
		{"key": key, "property": "innerHTML", "type": "key"}
		if prop in ("innerHTML", "text")
		else {"key": key, "property": prop, "type": "attribute"}
	)
	if comes_from:
		entry["comesFrom"] = comes_from
	return entry


def visibility_condition(field) -> dict:
	"""A `bind.visible` key → the block's visibilityCondition (rendered only when truthy)."""
	entry = binding_entry("visible", field)
	return {"key": entry["key"], "comesFrom": entry.get("comesFrom", "dataScript")}


def bind_to_dynamic_values(bind: dict) -> list:
	"""{property: item_key} → dynamicValues entries (the editor's binding shape).
	innerHTML/text bind by content ("key"); anything else binds an HTML attribute.
	'props.<name>' / 'component.<key>' keys bind to those sources instead of page
	data — a props binding resolves live in the editor canvas too."""
	return [binding_entry(prop, field) for prop, field in bind.items()]


def convert_node(node, is_root: bool = False) -> dict | None:
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
	# tool-edit concern, not a generation one).
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
		bind = dict(bind)
		if (visible := bind.pop("visible", None)) is not None:
			block["visibilityCondition"] = visibility_condition(visible)
		if bind:
			block["dynamicValues"] = bind_to_dynamic_values(bind)

	children = node.get("c")
	child_blocks = (
		[b for c in children if isinstance(c, dict) and (b := convert_node(c))]
		if isinstance(children, list)
		else []
	)

	# `repeat` = a static repeater: ONE template child + JSON data. The data array is
	# NOT stored on the block — it lands in the page_data_script shim (build_repeater_
	# data_script); the block keeps only the loop wiring + template child.
	repeat = node.get("repeat")
	if isinstance(repeat, dict) and repeat.get("item"):
		item = convert_node(repeat["item"])
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
	if needs_border_box(block):
		block["baseStyles"]["boxSizing"] = "border-box"
	return block


FULL_WIDTH = frozenset({"100%", "100vw"})
SIDE_LONGHANDS = ("paddingLeft", "paddingRight", "paddingInline", "borderLeft", "borderRight")
ZERO = frozenset({"0", "0px", "none"})


def needs_border_box(block: dict) -> bool:
	"""A full-width block with side padding or a side border is wider than its parent
	under Builder's content-box sizing; centred in a column it overflows both edges and
	its padding vanishes. border-box is what width:100% with padding means."""
	base = block.get("baseStyles") or {}
	if str(base.get("width")) not in FULL_WIDTH or base.get("boxSizing"):
		return False
	devices = (base, block.get("tabletStyles") or {}, block.get("mobileStyles") or {})
	return any(has_side_space(styles) for styles in devices)


def has_side_space(styles: dict) -> bool:
	if any(str(styles.get(key) or "0") not in ZERO for key in SIDE_LONGHANDS):
		return True
	for key in ("padding", "borderWidth"):
		parts = str(styles.get(key) or "0").split()
		sides = parts[1::2] if len(parts) > 1 else parts
		if any(side not in ZERO for side in sides):
			return True
	border = str(styles.get("border") or "none").split()
	return bool(border) and border[0] not in ZERO


def normalize_component_instances(root: dict | None) -> dict | None:
	"""Repair childless component instances anywhere in a tree. The editor and the
	published renderer both render an instance through the PAGE block's children
	(matched to the component via referenceBlockId) — an instance with no children
	shows NOTHING. add_block and generation attach the skeleton at conversion, but
	The model can hand-build `{extendedFromComponent: id}` dicts, so
	every tree that reaches the WorkingTree passes through here. Mutates in place."""
	if not isinstance(root, dict):
		return root
	stack = [root]
	while stack:
		block = stack.pop()
		# Weaker models sometimes carry text in a bare
		# `text` field — the format generate_page/add_block use — but Builder renders
		# from innerHTML, so the block would show empty. Promote it here (the one path
		# every hand-built tree passes through) rather than in each edit tool.
		if isinstance(block.get("text"), str) and not block.get("innerHTML"):
			block["innerHTML"] = block.pop("text")
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


ROOT_STYLE = {"display": "flex", "flexDirection": "column", "alignItems": "center", "width": "100%"}


def expand_page_markup(text: str, is_root: bool = True, errors: list | None = None) -> tuple[list, str]:
	"""Return ([root_block_dict], page_data_script); ([], "") when nothing parses.
	A bad line costs that line, never the page: a 30k-character generation is
	paid-for work. Several top-level blocks are wrapped in one root.

	`is_root=True` marks the block as the page <body> (root); pass False when
	expanding a reusable component's block tree (it is not a page body)."""
	from builder.ai import markup

	quiet = errors is not None
	errors = [] if errors is None else errors
	roots = markup.load(BlockCodec.strip_fences(text or ""), errors=errors)
	if errors and not quiet:
		logger.warning("page markup: dropped %d bad line(s), first: %s", len(errors), errors[0])
	if not roots:
		return [], ""
	root = roots[0] if len(roots) == 1 else {"el": "div", "name": "body", "style": ROOT_STYLE, "c": roots}
	block = convert_node(root, is_root=is_root)
	if not block:
		return [], ""
	return [block], build_repeater_data_script(roots)


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
	writes). Used by the headless loop after each round of applied block ops; the
	round's checkpoint commit is what makes a cancelled or crashed turn keep it."""
	frappe.db.set_value(
		"Builder Page", page_id, "draft_blocks", compact_json([root_block]), update_modified=True
	)


def persist_page(page_id: str, text: str, errors: list | None = None) -> tuple[dict | None, str]:
	"""Expand generated markup and write it to a Builder Page's draft_blocks (+ the
	repeater data shim). The page stays a DRAFT (published=0). Returns the expanded
	root block and data script, (None, "") if the markup produced no blocks. Lines
	that did not parse go to `errors` when given."""
	blocks, data_script = expand_page_markup(text, errors=errors)
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
	return blocks[0], data_script
