"""Protect user-selected subtrees and their inherited layout from Bob edits."""

from builder.ai.revisions import digest


def locked_paths(root, parents=()):
	if not isinstance(root, dict):
		return []
	path = (*parents, root)
	locked = [path] if (root.get("editorConfig") or {}).get("aiLocked") else []
	return locked + [found for child in root.get("children") or [] for found in locked_paths(child, path)]


def preserve_locked(before, after):
	from builder.ai.agent.selectors import find_block

	for path in locked_paths(before):
		locked = path[-1]
		if digest(find_block(after, locked.get("blockId"))) != digest(locked):
			raise ValueError(
				"This section is protected from Bob edits. Unlock it in the editor before changing it."
			)
		for index, ancestor in enumerate(path[:-1]):
			updated = find_block(after, ancestor.get("blockId"))

			def clean(block):
				return {key: value for key, value in (block or {}).items() if key != "children"}

			child_id = path[index + 1].get("blockId")
			same_parent = any(
				child.get("blockId") == child_id for child in (updated or {}).get("children", [])
			)
			if not same_parent or digest(clean(ancestor)) != digest(clean(updated)):
				raise ValueError("This change would alter the inherited layout of a protected section.")
