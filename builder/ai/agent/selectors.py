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


def design_digest(root: dict) -> str:
	"""A page's design language in a few lines: fonts with their ROLES (elements +
	sizes, not just counts — a bare 'x1' reads like half of a pairing and gets
	promoted to every heading), colours and radii with use counts, section rhythm."""
	from collections import Counter

	fonts: dict[str, dict] = {}
	colors, radii = Counter(), Counter()
	for block, _depth in walk_blocks(root):
		styles = block.get("baseStyles") or {}
		if family := styles.get("fontFamily"):
			usage = fonts.setdefault(family, {"count": 0, "els": [], "sizes": []})
			usage["count"] += 1
			if (el := block.get("element") or "div") not in usage["els"]:
				usage["els"].append(el)
			if (size := styles.get("fontSize")) and size not in usage["sizes"]:
				usage["sizes"].append(size)
		for prop in ("color", "backgroundColor"):
			if value := styles.get(prop):
				colors[value] += 1
		if radius := styles.get("borderRadius"):
			radii[radius] += 1
	sections = []
	for child in root.get("children") or []:
		if isinstance(child, dict):
			el = child.get("element") or "div"
			sections.append(f"{el}({child['blockName']})" if child.get("blockName") else el)
	lines = []
	if fonts:
		lines.append(
			"fonts: "
			+ ", ".join(
				font_role(family, usage)
				for family, usage in sorted(fonts.items(), key=lambda kv: -kv[1]["count"])
			)
		)
	if colors:
		lines.append("colors: " + ", ".join(f"{c} x{n}" for c, n in colors.most_common(14)))
	if radii:
		lines.append("radii: " + ", ".join(f"{r} x{n}" for r, n in radii.most_common(6)))
	if len(sections) > 40:
		sections = [*sections[:40], f"+{len(sections) - 40} more"]
	if sections:
		lines.append("sections: " + " > ".join(sections))
	return "\n".join(lines) or "(no styles set)"


def font_role(family: str, usage: dict) -> str:
	"""'Inter Variable x13 (p/h2/span at 11px, 17px, 20px)' — the count says how
	dominant a font is, the elements and sizes say what it is FOR."""
	where = "/".join(usage["els"][:4])
	if sizes := ", ".join(usage["sizes"][:4]):
		where += f" at {sizes}"
	return f"{family} x{usage['count']} ({where})"


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
