"""Block tree helpers: parsing, walking, component instances and prop values."""

from __future__ import annotations

import copy
import json
import secrets

STANDARD_ATTRS = {"src", "darkSrc", "alt", "href", "title", "value", "type", "placeholder", "target", "rel"}
FIXED_FIELDS = {
	"blockId",
	"referenceBlockId",
	"isChildOfComponent",
	"extendedFromComponent",
	"children",
	"props",
}


def parse_blocks(raw) -> list:
	value = json.loads(raw) if isinstance(raw, str) else raw
	if isinstance(value, dict):
		value = [value]
	return value or []


def walk(node, visit):
	if isinstance(node, list):
		for item in node:
			walk(item, visit)
	elif isinstance(node, dict):
		visit(node)
		walk(node.get("children"), visit)


def block_ids(tree) -> set[str]:
	found = set()
	walk(tree, lambda node: found.add(node["blockId"]) if node.get("blockId") else None)
	return found


def new_id() -> str:
	return secrets.token_hex(4)


def encode_value(declaration: dict, value):
	"""The instance value in the shape the editor stores: JSON strings for arrays and
	objects, real booleans and numbers, plain strings for the rest."""
	kind = declaration["propOptions"]["type"]
	if kind in ("array", "object"):
		return value if isinstance(value, str) else json.dumps(value)
	if kind == "boolean":
		return value if isinstance(value, bool) else str(value).strip().lower() in ("true", "1", "yes")
	if kind == "number":
		return value if isinstance(value, (int, float)) else float(value)
	return "" if value is None else str(value)


class InstanceBuilder:
	"""Builds a page-side instance of a component: root, skeleton refs, prop values and
	per-instance overrides of the definition's blocks."""

	def __init__(self, load_definition):
		self.load_definition = load_definition

	def build(self, component_id: str, props: dict | None = None, overrides: dict | None = None) -> dict:
		definition = self.load_definition(component_id)
		declared = definition.get("props") or {}
		unknown = sorted(set(props or {}) - set(declared))
		if unknown:
			raise KeyError(f"{component_id} declares no prop(s) {unknown}; declared: {sorted(declared)}")
		root = {
			"blockId": new_id(),
			"element": definition.get("element") or "div",
			"blockName": definition.get("blockName") or component_id,
			"extendedFromComponent": component_id,
			"children": self.skeleton(definition.get("children"), component_id),
		}
		if props:
			root["props"] = {key: self.with_value(declared[key], value) for key, value in props.items()}
		for key, fields in (overrides or {}).items():
			self.override(root, definition, key, fields)
		return root

	def override(self, root: dict, definition: dict, key: str, fields: dict):
		fixed = sorted(FIXED_FIELDS & set(fields))
		if fixed:
			raise KeyError(f"{key}: an override can't set {fixed}")
		targets = {definition.get("blockId"): root, **self.own_refs(root)}
		targets[self.resolve(definition, key)].update(fields)

	@staticmethod
	def own_refs(root: dict) -> dict:
		refs, owner = {}, root["extendedFromComponent"]
		walk(
			root["children"],
			lambda ref: ref["isChildOfComponent"] == owner and refs.setdefault(ref["referenceBlockId"], ref),
		)
		return refs

	@staticmethod
	def resolve(definition: dict, key: str) -> str:
		"""The definition blockId a blockId or a blockName refers to, among the component's
		own blocks (not those of a component nested in it)."""
		own = []
		walk(definition, lambda block: None if block.get("isChildOfComponent") else own.append(block))
		matches = [block["blockId"] for block in own if key in (block.get("blockId"), block.get("blockName"))]
		if len(matches) == 1:
			return matches[0]
		names = sorted({block.get("blockName") or block.get("blockId") for block in own})
		if matches:
			raise KeyError(f"blockName '{key}' is on several blocks; use a blockId: {matches}")
		raise KeyError(f"the component has no block '{key}'; its blocks: {names}")

	def skeleton(self, children: list | None, owner: str) -> list:
		refs = []
		for child in children or []:
			if not isinstance(child, dict):
				continue
			ref = {"blockId": new_id(), "referenceBlockId": child.get("blockId"), "isChildOfComponent": owner}
			if child.get("isRepeaterBlock"):
				ref["isRepeaterBlock"] = True
			nested = child.get("extendedFromComponent")
			if nested:
				ref["extendedFromComponent"] = nested
				ref["children"] = self.skeleton(self.load_definition(nested).get("children"), nested)
			else:
				ref["children"] = self.skeleton(child.get("children"), owner)
			refs.append(ref)
		return refs

	@staticmethod
	def with_value(declaration: dict, value) -> dict:
		entry = copy.deepcopy(declaration)
		entry["value"] = encode_value(declaration, value)
		return entry
