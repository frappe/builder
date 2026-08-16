"""Server-side working tree of the page's blocks for one agent turn.

The loop applies every client block op here FIRST — this tree is the source of
truth (loaded from draft_blocks, persisted back after each round). The tool
result handed to the model is therefore honest — "applied to block X", "3 of 12
not found", "parent not found" — and a wrong ref drives a self-correcting round.
Ops the tree accepts are then mirrored to the canvas (the editor's live view);
ops it rejects are never emitted, so the two sides can't diverge.

Kept in lockstep with the frontend applier (toolDispatch.applyBlockUpdate /
applyToolOperation), which replays the same accepted ops on the canvas.
"""

import re

from builder.ai.agent.selectors import find_block, walk_blocks
from builder.ai.block_codec import STANDARD_ATTRS

# A binding key is a PLAIN field/data key (dots allow nesting). Models sometimes try
# expressions ("'$' + item.price", "in_stock ? 'In Stock' : '…'") — those can never
# resolve; formatting belongs in the page data script or static text.
BIND_KEY_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_.]*$")


def bad_bind_keys(op: dict) -> list[str]:
	bind = op.get("bind")
	if not isinstance(bind, dict):
		return []
	from builder.ai.page_writer import strip_binding_prefix

	return [str(v) for v in bind.values() if v is not None and not BIND_KEY_RE.match(strip_binding_prefix(v))]


BAD_BIND_HINT = (
	"bind keys must be PLAIN field/data keys (e.g. 'price', 'image') — expressions can't "
	"resolve. Bind the raw field, and compute formatted/conditional text in the page data "
	"script instead (e.g. set price_display on each record in write_page_data_script)."
)

# bind maps PROPERTIES (innerHTML or an HTML attribute) to data keys — it cannot turn
# a block into a repeater.
REPEATER_BIND_PROPS = {"repeat", "data", "loop", "items", "datakey"}
REPEATER_BIND_HINT = (
	"a repeater cannot be created via bind. Build it with add_block: "
	"{el: div, repeat: {data: '<page-data key>', item: {…card template with bind…}}} — "
	"then remove_block the static copies."
)


def repeater_bind_props(op: dict) -> list[str]:
	bind = op.get("bind")
	if not isinstance(bind, dict):
		return []
	return [p for p in bind if p.lower() in REPEATER_BIND_PROPS]


# Attribute values and innerHTML go through Jinja on the PUBLISHED page — moustache
# text like data-city="{{ item.city }}" doesn't render literally there, it crashes the
# whole route with UndefinedError. Bindings are the only sanctioned dynamic mechanism.
MOUSTACHE_RE = re.compile(r"\{\{|\{%")
MOUSTACHE_HINT = (
	"'{{ … }}' Jinja/moustache text in content or attributes CRASHES the published page "
	"(undefined variable at render). Use bind for dynamic values instead — e.g. "
	"bind: {'data-city': 'city', innerHTML: 'title'}."
)


def moustache_fields(op: dict) -> list[str]:
	"""Fields of an update/add payload carrying moustache text."""
	hits = []
	for field in ("inner_text", "inner_html"):
		if MOUSTACHE_RE.search(str(op.get(field) or "")):
			hits.append(field)
	for key, value in (op.get("attributes") or {}).items() if isinstance(op.get("attributes"), dict) else []:
		if MOUSTACHE_RE.search(str(value or "")):
			hits.append(f"attributes.{key}")
	if "block" in op and MOUSTACHE_RE.search(json_dumps_safe(op.get("block"))):
		hits.append("block")
	return hits


def json_dumps_safe(value) -> str:
	import json

	try:
		return json.dumps(value, default=str)
	except (TypeError, ValueError):
		return str(value)


def merge_styles(block: dict, args: dict) -> None:
	from builder.ai.page_writer import normalize_styles

	for arg_key, block_key in (
		("base_styles", "baseStyles"),
		("mobile_styles", "mobileStyles"),
		("tablet_styles", "tabletStyles"),
	):
		if styles := normalize_styles(args.get(arg_key)):
			block.setdefault(block_key, {}).update(styles)


def merge_attributes(block: dict, attrs: dict) -> None:
	# Same standard/custom split the editor applies (toolDispatch.applyBlockUpdate).
	for key, value in attrs.items():
		target = "attributes" if key in STANDARD_ATTRS else "customAttributes"
		if value is None:
			block.get(target, {}).pop(key, None)
		else:
			block.setdefault(target, {})[key] = value


def merge_props(block: dict, props: dict, pinned: dict | None = None, live: dict | None = None) -> None:
	"""Per-instance prop values ({name: value}; None removes). Only `value` is
	touched; a FIRST override borrows the declaration's config (as the canvas twin
	does) so label/options survive in the authoritative draft. A prop the
	definition never declared gets DECLARED there too — a fresh embed must offer
	the same knob, not arrive bare. `pinned`/`live` accept schemas the caller
	already resolved (route_props), sparing repeat snapshot reads."""
	current = block.setdefault("props", {})
	undeclared = {}
	for name, value in props.items():
		if value is None:
			current.pop(name, None)
		elif isinstance(current.get(name), dict):
			current[name]["value"] = value
		else:
			if pinned is None:
				pinned = declared_props(block)
			config = dict(pinned.get(name) or prop_config(value))
			config["value"] = value
			current[name] = config
			if name not in pinned:
				undeclared[name] = config
	if undeclared and block.get("extendedFromComponent"):
		if live is None:
			live = live_declared_props(block["extendedFromComponent"])
		# Mirror only into a BARE live schema (the authoring flow); a live schema
		# with props already declared must never gain names from an instance.
		if not live:
			update_definition(
				block["extendedFromComponent"], lambda root: root.setdefault("props", {}).update(undeclared)
			)


def prop_config(value) -> dict:
	"""A fresh declaration typed from its first value, so the editor's props panel
	renders a proper input instead of an untyped entry."""
	if isinstance(value, bool):
		prop_type = "boolean"
	elif isinstance(value, (int, float)):
		prop_type = "number"
	elif isinstance(value, list):
		prop_type = "array"
	elif isinstance(value, dict):
		prop_type = "object"
	else:
		prop_type = "string"
	# isStandard is what the editor's Block Options section filters on — without
	# it a declared prop exists but never renders in the properties panel.
	return {
		"isDynamic": False,
		"isPassedDown": False,
		"comesFrom": None,
		"isStandard": True,
		"propOptions": {"type": prop_type},
	}


def declared_props(block: dict) -> dict:
	"""The declaration's prop configs, honouring the instance's pinned version."""
	component = block.get("extendedFromComponent")
	if not component:
		return {}
	return resolve_declared_props(component, block.get("componentVersion"))


def live_declared_props(component: str) -> dict:
	"""The LIVE definition's schema — the mutation target for declaration mirrors,
	so authoring-vs-strict is judged here, never against a pinned snapshot (a
	prop-less pinned version must not open the live schema to accidental props)."""
	return resolve_declared_props(component, None)


def resolve_declared_props(component: str, version) -> dict:
	import frappe

	from builder.builder.component_versions import resolve_component

	resolved = resolve_component(component, version)
	definition = frappe.parse_json((resolved or {}).get("block") or "{}")
	declared = definition.get("props") if isinstance(definition, dict) else None
	return declared if isinstance(declared, dict) else {}


CLIENT_SCRIPT_HINT = (
	"client_script belongs to COMPONENT blocks only (an instance root or a block inside "
	"one), where behaviour ships with every embed. For a plain page block use "
	"set_page_script: page scripts stay visible and manageable in the editor's panel."
)


def client_script_outside_component(block: dict, args: dict) -> bool:
	return isinstance(args.get("client_script"), dict) and not (
		block.get("extendedFromComponent") or block.get("isChildOfComponent")
	)


def merge_client_script(block: dict, script: dict) -> None:
	"""The block's own js/css ({js: ..., css: ...}; None clears a key). Mirrored
	into the component DEFINITION (root or the mirrored internal block): behaviour
	must ship with every embed, and the edit necessarily lands on instance blocks
	(the component exists by the time the script is written)."""
	apply_client_script(block, script)
	component = block.get("extendedFromComponent") or block.get("isChildOfComponent")
	if not component:
		return
	inner = None if block.get("extendedFromComponent") else (block.get("referenceBlockId") or "")

	def mirror(root: dict) -> None:
		target = root if inner is None else find_block(root, inner)
		if target is not None:
			apply_client_script(target, script)

	update_definition(component, mirror)


def apply_client_script(block: dict, script: dict) -> None:
	current = block.setdefault("clientScript", {})
	for kind in ("js", "css"):
		if kind not in script:
			continue
		if script[kind] is None:
			current.pop(kind, None)
		else:
			current[kind] = script[kind]


def update_definition(component: str, mutate) -> None:
	"""Apply a mutation to the Builder Component's live block JSON. Editors pick
	the change up when they next load the component; this page's instance already
	carries the same values as overrides."""
	import json

	import frappe

	if not frappe.db.exists("Builder Component", component):
		return
	definition = frappe.parse_json(frappe.db.get_value("Builder Component", component, "block") or "{}")
	if not isinstance(definition, dict):
		return
	mutate(definition)
	frappe.db.set_value("Builder Component", component, "block", json.dumps(definition), update_modified=True)


def merge_bindings(block: dict, bind: dict) -> None:
	"""Merge {property: item_key} bindings into dynamicValues — one entry per bound
	property (a re-bind replaces, a None value unbinds)."""
	from builder.ai.page_writer import bind_to_dynamic_values

	incoming = {prop: field for prop, field in bind.items() if field is not None}
	dropped = {("innerHTML" if p in ("innerHTML", "text") else p) for p in bind}
	kept = [dv for dv in block.get("dynamicValues") or [] if dv.get("property") not in dropped]
	block["dynamicValues"] = kept + bind_to_dynamic_values(incoming)


STYLE_INJECTION_MARKERS = (
	"createElement('style'",
	'createElement("style"',
	"createElement(`style`",
	"<style",
)


def validate_script(op: dict) -> str:
	"""Script ops are otherwise free-form; the one hard rule is separation: CSS lives
	in a script_type='CSS' script, never injected into the DOM from JavaScript."""
	if (op.get("script_type") or "JavaScript") == "JavaScript":
		src = op.get("script") or ""
		if any(marker in src for marker in STYLE_INJECTION_MARKERS):
			return (
				"FAILED: this JavaScript script injects CSS (a <style> tag). Split it into TWO "
				"set_page_script calls: the stylesheet content in its own script_type='CSS' "
				"script, and only the behaviour in the JavaScript one."
			)
	return "Applied."


def merge_block_update(block: dict, args: dict) -> None:
	"""One block's worth of changes (styles/attrs/text/element/classes/bindings) —
	the server twin of toolDispatch.applyBlockUpdate, shared by update_block and
	update_blocks."""
	merge_styles(block, args)
	if isinstance(args.get("attributes"), dict):
		merge_attributes(block, args["attributes"])
	if args.get("inner_text") is not None:
		block["innerHTML"] = args["inner_text"]
	if args.get("inner_html") is not None:  # html wins when both are given
		block["innerHTML"] = args["inner_html"]
	if args.get("element") is not None:
		from builder.ai.page_writer import FORBIDDEN_ELEMENTS

		# Silently keep the old element rather than fail the whole (multi-field)
		# update; code belongs in the script tools, not the block tree.
		if str(args["element"]).strip().lower() not in FORBIDDEN_ELEMENTS:
			block["element"] = args["element"]
	if args.get("classes") is not None:
		block["classes"] = args["classes"]
	if isinstance(args.get("bind"), dict):
		merge_bindings(block, args["bind"])
	# props never reach here: WorkingTree.route_props validates and applies them
	# on the owning instance root before this merge runs.
	if isinstance(args.get("client_script"), dict):
		merge_client_script(block, args["client_script"])


def insert_child(parent: dict, block: dict, after_block_id: str | None, index) -> None:
	children = parent.setdefault("children", [])
	if after_block_id:
		for i, child in enumerate(children):
			if isinstance(child, dict) and child.get("blockId") == after_block_id:
				children.insert(i + 1, block)
				return
	if isinstance(index, int) and 0 <= index <= len(children):
		children.insert(index, block)
		return
	children.append(block)


class WorkingTree:
	def __init__(self, root: dict | None):
		self.root = root

	def resolve(self, block_id: str | None) -> dict | None:
		return find_block(self.root, block_id) if (self.root and block_id) else None

	def parent_of(self, block_id: str) -> dict | None:
		for block, _ in walk_blocks(self.root):
			for child in block.get("children") or []:
				if isinstance(child, dict) and child.get("blockId") == block_id:
					return block
		return None

	def detach(self, block_id: str) -> None:
		if parent := self.parent_of(block_id):
			parent["children"] = [c for c in parent["children"] if c.get("blockId") != block_id]

	def id_hint(self, block_id: str | None) -> str:
		"""The model often passes a block's HTML id (attrs.id) instead of its editor
		ref — the most common miss. When the id matches a real block, name its ref."""
		for block, _ in walk_blocks(self.root or {}):
			attrs = {**(block.get("attributes") or {}), **(block.get("customAttributes") or {})}
			if block_id and attrs.get("id") == block_id:
				return f" — that's the HTML id; this block's ref is '{block.get('blockId')}'. Use the ref."
		return " — not a valid ref. Call query_blocks or re-read the page outline for real refs."

	def apply(self, tool_name: str, args: dict) -> str:
		args = args or {}
		if tool_name == "update_block":
			return self.apply_update(args.get("block_id"), args)
		if tool_name == "update_blocks":
			return self.apply_update_blocks(args)
		if tool_name == "remove_block":
			return self.apply_remove(args.get("block_id"))
		if tool_name == "move_block":
			return self.apply_move(args)
		if tool_name == "add_block":
			return self.apply_add(args)
		if tool_name in ("set_page_script", "update_script"):
			return validate_script(args)
		# Non-block client tools carry no ref to validate.
		return "Applied."

	def apply_update(self, block_id: str | None, args: dict) -> str:
		block = self.resolve(block_id)
		if block is None:
			return f"FAILED: block_id '{block_id}' not found{self.id_hint(block_id)}"
		args, failure = self.screen_patch(block, args)
		if failure:
			return failure
		merge_block_update(block, args)
		return f"Applied to block {block_id} (<{block.get('element') or 'div'}>)."

	def screen_patch(self, block: dict, args: dict) -> tuple[dict, str]:
		"""Every per-field guard, in one seam shared by the single and batch update
		paths. Returns (args ready to merge, "") or (args, "FAILED: …")."""
		if props := repeater_bind_props(args):
			return args, f"FAILED: bind {props} — {REPEATER_BIND_HINT}"
		if bad := bad_bind_keys(args):
			return args, f"FAILED: {bad} — {BAD_BIND_HINT}"
		if fields := moustache_fields(args):
			return args, f"FAILED: {fields} — {MOUSTACHE_HINT}"
		if client_script_outside_component(block, args):
			return args, f"FAILED: {CLIENT_SCRIPT_HINT}"
		return self.route_props(block, args)

	def route_props(self, block: dict, args: dict) -> tuple[dict, str]:
		"""Prop values live on the INSTANCE ROOT — the canvas routes a child-targeted
		write up via getPropsRoot(), and resolution only reads the root, so the server
		must land it in the same place or a reload silently restores the old value.
		Schemas resolve ONCE here (pinned = what this instance renders, live = the
		mirror target) and feed both validation and the merge. An unknown name on a
		declared live schema is almost always a typo — writing it through would
		mutate the shared component; a BARE live schema is the authoring flow.
		Returns (args stripped of props, "") or (args, failure)."""
		if not isinstance(args.get("props"), dict):
			return args, ""
		owner = self.props_owner(block)
		if owner is None:
			return args, (
				"FAILED: props apply to component instances — this block is not inside one. "
				"Style or text changes on a plain block go through the other update fields."
			)
		props = args["props"]
		pinned = declared_props(owner)
		live = live_declared_props(owner["extendedFromComponent"])
		if live and (
			unknown := [n for n in props if props[n] is not None and n not in pinned and n not in live]
		):
			declared = ", ".join(sorted(set(pinned) | set(live)))
			return args, (
				f"FAILED: props {unknown} — this component declares only: {declared}. Use a "
				"declared name; a genuinely new prop is added by editing the component itself, "
				"not through an instance."
			)
		merge_props(owner, props, pinned=pinned, live=live)
		return {k: v for k, v in args.items() if k != "props"}, ""

	def props_owner(self, block: dict) -> dict | None:
		"""The instance root a prop write belongs to: the block itself, or the nearest
		ancestor instance root when the target is a component-internal child."""
		if block.get("extendedFromComponent"):
			return block
		if not block.get("isChildOfComponent"):
			return None
		node = block
		while node is not None and not node.get("extendedFromComponent"):
			node = self.parent_of(node.get("blockId"))
		return node

	def apply_update_blocks(self, args: dict) -> str:
		patches = args.get("patches")
		if isinstance(patches, list):
			targets = [(p.get("block_id"), p) for p in patches if isinstance(p, dict)]
		else:
			targets = [(block_id, args) for block_id in args.get("block_ids") or []]
		if not targets:
			return "FAILED: no block_ids or patches supplied — nothing to update."
		missing, rejected = [], []
		for block_id, patch in targets:
			block = self.resolve(block_id)
			if block is None:
				missing.append(block_id)
				continue
			patch, failure = self.screen_patch(block, patch)
			if failure:
				# Each entry keeps ITS OWN reason — a props typo must not read as a
				# bad bind in the summary.
				rejected.append(f"{block_id}: {failure.removeprefix('FAILED: ')[:110]}")
			else:
				merge_block_update(block, patch)
		applied = len(targets) - len(missing) - len(rejected)
		problems = []
		if missing:
			problems.append(f"NOT FOUND: {missing} — those refs don't exist, recheck them.")
		if rejected:
			problems.append("REJECTED " + "; ".join(rejected))
		if problems:
			return f"Applied to {applied} of {len(targets)} blocks. " + " ".join(problems)
		return f"Applied to all {applied} block(s)."

	def apply_remove(self, block_id: str | None) -> str:
		block = self.resolve(block_id)
		if block is None:
			return f"FAILED: block_id '{block_id}' not found{self.id_hint(block_id)}"
		self.detach(block_id)
		return f"Removed block {block_id}."

	def apply_move(self, args: dict) -> str:
		block_id = args.get("block_id")
		new_parent_id = args.get("new_parent_block_id")
		block = self.resolve(block_id)
		if block is None:
			return f"FAILED: block_id '{block_id}' not found{self.id_hint(block_id)}"
		new_parent = self.resolve(new_parent_id)
		if new_parent is None:
			return f"FAILED: new_parent_block_id '{new_parent_id}' not found{self.id_hint(new_parent_id)}"
		# A block can't become a child of itself or its own descendant — that would
		# cycle the tree (and infinite-loop a later walk). Reject it like an invalid ref.
		if find_block(block, new_parent_id) is not None:
			return f"FAILED: can't move {block_id} into itself or its own descendant ({new_parent_id})."
		self.detach(block_id)
		insert_child(new_parent, block, args.get("after_block_id"), args.get("index"))
		return f"Moved block {block_id} under {new_parent_id}."

	def apply_add(self, args: dict) -> str:
		parent_id = args.get("parent_block_id")
		parent = self.resolve(parent_id)
		if parent is None:
			return f"FAILED: parent_block_id '{parent_id}' not found{self.id_hint(parent_id)}"
		if fields := moustache_fields(args):
			return f"FAILED: {fields} — {MOUSTACHE_HINT}"
		if not isinstance(args.get("block"), dict):
			return "FAILED: no block definition supplied."
		from builder.ai.page_writer import convert_yaml_block

		block = convert_yaml_block(args["block"], is_root=False)
		if not block:
			return (
				"FAILED: style/script/document elements are not blocks — JS/CSS goes through "
				"set_page_script; fonts load automatically from fontFamily."
			)
		insert_child(parent, block, args.get("after_block_id"), args.get("index"))
		# Ship the expanded block (with its assigned refs, children included) to the
		# canvas so both sides key the same ids, and name the new ref so the model can
		# chain edits onto the block it just added.
		args["block_json"] = block
		return f"Added block {block.get('blockId')} (<{block.get('element')}>) under {parent_id}."
