"""Tree helpers for the agent's selector tools.

The server already holds the full page tree (the frontend ships it as
`page_context`), so block selection and inspection are answered here without a
frontend round-trip. These walk the native block dict (element / blockId /
children / …) — the same shape `BlockCodec` operates on.
"""

from collections.abc import Iterator

# Elements that carry user-visible copy — the set "translate the page" / "rewrite
# all text" must touch. Used by query_blocks(text_only=True).
TEXT_ELEMENTS = frozenset(
	{
		"h1",
		"h2",
		"h3",
		"h4",
		"h5",
		"h6",
		"p",
		"span",
		"a",
		"button",
		"li",
		"label",
		"blockquote",
		"figcaption",
		"small",
		"strong",
		"em",
	}
)


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


def is_text_block(block: dict) -> bool:
	"""A block that carries its own copy — a text element with non-empty innerHTML."""
	return bool(block_text(block)) and (block.get("element") or "") in TEXT_ELEMENTS


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
