"""Block tree helpers: parsing, walking, component instances and prop values."""

import copy
import json
import secrets

STANDARD_ATTRS = {"src", "darkSrc", "alt", "href", "title", "value", "type", "placeholder", "target", "rel"}


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
		return value if isinstance(value, int | float) else float(value)
	return "" if value is None else str(value)


class InstanceBuilder:
	"""Builds a page-side instance of a component: root, skeleton refs and prop values."""

	def __init__(self, load_definition):
		self.load_definition = load_definition

	def build(self, component_id: str, props: dict | None = None) -> dict:
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
		return root

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
