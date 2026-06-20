"""Server-side mirror of the canvas block tree for one agent turn.

The loop applies each client block op to this mirror as it emits it, so the
tool result handed back to the model is the truth — "applied to block X",
"3 of 12 not found", "parent not found" — instead of a blanket "Applied." that
hides a silently dropped edit (the frontend no-ops on a missing ref, and that
never travels back). A wrong ref then drives a self-correcting round.

The mirror tracks only what reference-validation needs: it resolves refs
against the live tree and keeps structure honest across rounds (remove detaches
the subtree, move reparents). Style/text changes are not mirrored — nothing
reads them back yet — and add_block does not assign a ref (that is Phase 2).
"""

from builder.ai.agent.selectors import find_block, walk_blocks


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
			return self.apply_update(args.get("block_id"))
		if tool_name == "update_blocks":
			return self.apply_update_blocks(args)
		if tool_name == "remove_block":
			return self.apply_remove(args.get("block_id"))
		if tool_name == "move_block":
			return self.apply_move(args)
		if tool_name == "add_block":
			return self.apply_add(args.get("parent_block_id"))
		# Non-block client tools (scripts) carry no ref to validate.
		return "Applied."

	def apply_update(self, block_id: str | None) -> str:
		block = self.resolve(block_id)
		if block is None:
			return f"FAILED: block_id '{block_id}' not found{self.id_hint(block_id)}"
		return f"Applied to block {block_id} (<{block.get('element') or 'div'}>)."

	def apply_update_blocks(self, args: dict) -> str:
		patches = args.get("patches")
		if isinstance(patches, list):
			ids = [p.get("block_id") for p in patches if isinstance(p, dict)]
		else:
			ids = args.get("block_ids") or []
		if not ids:
			return "FAILED: no block_ids or patches supplied — nothing to update."
		missing = [i for i in ids if self.resolve(i) is None]
		applied = len(ids) - len(missing)
		if missing:
			return (
				f"Applied to {applied} of {len(ids)} blocks. NOT FOUND: {missing}. "
				"Those refs don't exist — recheck them, don't reissue the same ids."
			)
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
		new_parent.setdefault("children", []).append(block)
		return f"Moved block {block_id} under {new_parent_id}."

	def apply_add(self, parent_id: str | None) -> str:
		if self.resolve(parent_id) is None:
			return f"FAILED: parent_block_id '{parent_id}' not found{self.id_hint(parent_id)}"
		return f"Added block under {parent_id}."
