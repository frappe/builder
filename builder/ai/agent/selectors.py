"""Tree helpers for the agent: walk, resolve a ref, digest a page's design.
They walk the native block dict (element / blockId / children / …), the shape
`BlockCodec` operates on."""

from collections.abc import Iterator


def walk_blocks(root: dict, depth: int = 0) -> Iterator[tuple[dict, int]]:
	"""Yield (block, depth) for the root and every descendant, depth-first."""
	if not isinstance(root, dict):
		return
	yield root, depth
	for child in root.get("children") or []:
		if isinstance(child, dict):
			yield from walk_blocks(child, depth + 1)


MIN_PREFIX = 4


def find_block(root: dict, block_id: str) -> dict | None:
	"""The block with this blockId, else the only block whose id starts with it: the
	short `@ref` markup shows (a leading @ is fine). None when absent or ambiguous."""
	ref = str(block_id or "").lstrip("@")
	if not ref:
		return None
	matches = []
	for block, _depth in walk_blocks(root):
		current = block.get("blockId") or ""
		if current == ref:
			return block
		if len(ref) >= MIN_PREFIX and current.startswith(ref):
			matches.append(block)
	return matches[0] if len(matches) == 1 else None


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
