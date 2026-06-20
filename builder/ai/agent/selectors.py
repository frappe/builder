"""Tree helpers for the agent's selector tools.

The server already holds the full page tree (the frontend ships it as
`page_context`), so block selection and inspection are answered here without a
frontend round-trip. These walk the native block dict (element / blockId /
children / …) — the same shape `BlockCodec` operates on.
"""

from collections.abc import Iterator


def walk_blocks(root: dict, depth: int = 0) -> Iterator[tuple[dict, int]]:
	"""Yield (block, depth) for the root and every descendant, depth-first."""
	if not isinstance(root, dict):
		return
	yield root, depth
	for child in root.get("children") or []:
		if isinstance(child, dict):
			yield from walk_blocks(child, depth + 1)


def find_block(root: dict, block_id: str) -> dict | None:
	"""Return the block with this blockId, or None."""
	for block, _depth in walk_blocks(root):
		if block.get("blockId") == block_id:
			return block
	return None


def block_text(block: dict) -> str:
	"""The block's own text content (innerHTML), stripped. Empty for containers."""
	return (block.get("innerHTML") or "").strip()


def render_skeleton(root: dict, max_text: int = 60) -> str:
	"""A compact one-line-per-block outline: indent shows nesting, then the block's
	ref, element, optional name, and a short text preview. Styles and attributes are
	omitted — the model pulls those with read_block when it actually needs them. Text
	is previewed only; query_blocks returns it in full for bulk edits."""
	lines: list[str] = []
	for block, depth in walk_blocks(root):
		ref = block.get("blockId") or "?"
		el = block.get("element") or "div"
		parts = [f"{'  ' * depth}{ref} {el}"]
		if name := block.get("blockName"):
			parts.append(f"({name})")
		if text := block_text(block):
			preview = text if len(text) <= max_text else text[: max_text - 1] + "…"
			parts.append(f'"{preview}"')
		lines.append(" ".join(parts))
	return "\n".join(lines)


def is_text_block(block: dict) -> bool:
	"""A leaf block that carries user-visible copy. Defined by SHAPE, not a tag
	whitelist: non-empty innerHTML and no block children — so it catches text in
	non-semantic containers too (a div/td/dd with direct text), which is common on
	imported/replicated pages and is exactly what a translate-everything must reach.
	Excludes raw SVG/markup blobs (decorative illustrations live in a div's innerHTML)
	— that is not copy to translate."""
	text = block_text(block)
	if not text or block.get("children"):
		return False
	return not text.lstrip().lower().startswith("<svg")


def match_block(
	block: dict,
	*,
	element: str | None = None,
	text_only: bool = False,
	contains: str | None = None,
	class_name: str | None = None,
) -> bool:
	"""Does this block satisfy every supplied filter? Filters AND together."""
	if element and (block.get("element") or "").lower() != element.lower():
		return False
	if text_only and not is_text_block(block):
		return False
	if contains and contains.lower() not in block_text(block).lower():
		return False
	if class_name and class_name not in (block.get("classes") or []):
		return False
	return True
