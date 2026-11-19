"""Run a markup edit script against a WorkingTree.

Each markup op compiles to the internal block ops the tree already applies
(update_block, add_block, remove_block, move_block) with full block ids, so every
guard in tree.py holds and the canvas mirrors the accepted ops unchanged.
"""

import re
from itertools import pairwise

from builder.ai import markup
from builder.ai.agent.selectors import walk_blocks

ADDED_LIMIT = 40


class EditScript:
	def __init__(self, tree, sets: dict | None = None):
		self.tree = tree
		self.sets = sets or {}
		self.accepted: list[dict] = []
		self.failures: list[str] = []
		self.added: list[str] = []
		self.count = 0

	def run(self, text: str) -> tuple[str, list[dict]]:
		"""Returns (the report for the model, the accepted internal ops in order)."""
		for op in markup.parse_ops(text, self.sets):
			self.count += 1
			if op.kind == "error":
				self.failures.append(op.error)
				continue
			getattr(self, f"run_{op.kind}")(op)
		return self.report(), self.accepted

	def fail(self, op: markup.Op, why: str) -> None:
		self.failures.append(f"line {op.number}: {why}")

	def resolve(self, op: markup.Op, ref: str | None) -> dict | None:
		block = self.tree.resolve(ref)
		if block is None:
			self.fail(op, f"@{ref} not found{self.tree.id_hint(ref)}")
		return block

	def apply(self, op: markup.Op, tool_name: str, args: dict) -> bool:
		result = self.tree.apply(tool_name, args)
		if result.startswith("FAILED"):
			self.fail(op, result.removeprefix("FAILED: "))
			return False
		self.accepted.append({"tool_name": tool_name, "args": args})
		return True

	def run_patch(self, op: markup.Op) -> None:
		from builder.ai.page_writer import needs_border_box

		for ref in op.refs:
			if not (block := self.resolve(op, ref)):
				continue
			args = {"block_id": block["blockId"], **patch_args(op.fields)}
			if self.apply(op, "update_block", args) and needs_border_box(block):
				# the mirrored args must carry what the tree now holds
				block["baseStyles"]["boxSizing"] = "border-box"
				args["base_styles"] = {**(args.get("base_styles") or {}), "boxSizing": "border-box"}

	def run_remove(self, op: markup.Op) -> None:
		for ref in op.refs:
			if (block := self.resolve(op, ref)) is not None:
				if block is self.tree.root:
					self.fail(op, "the page root can't be removed")
				else:
					self.apply(op, "remove_block", {"block_id": block["blockId"]})

	def run_move(self, op: markup.Op) -> None:
		block = self.resolve(op, op.refs[0])
		place = self.place(op, exclude=block)
		if block is None or place is None:
			return
		parent, index = place
		self.apply(
			op,
			"move_block",
			{"block_id": block["blockId"], "new_parent_block_id": parent["blockId"], "index": index},
		)

	def run_add(self, op: markup.Op) -> None:
		place = self.place(op)
		if place is None:
			return
		parent, index = place
		for offset, node in enumerate(op.body):
			self.insert(op, parent, None if index is None else index + offset, node)

	def run_replace(self, op: markup.Op) -> None:
		block = self.resolve(op, op.refs[0])
		if block is None:
			return
		parent = self.tree.parent_of(block["blockId"])
		if parent is None:
			self.fail(op, "the page root can't be replaced; replace its sections or `add` into it")
			return
		index = position(parent, block)
		if self.apply(op, "remove_block", {"block_id": block["blockId"]}):
			self.insert(op, parent, index, op.body[0])

	def insert(self, op: markup.Op, parent: dict, index: int | None, node: dict) -> None:
		extras = {key: node.pop(key) for key in ("props", "client_script") if key in node}
		args = {"parent_block_id": parent["blockId"], "block": node}
		if index is not None:
			args["index"] = index
		if not self.apply(op, "add_block", args):
			return
		block_id = args["block_json"]["blockId"]
		self.added.append(block_id)
		if extras:
			self.apply(op, "update_block", {"block_id": block_id, **extras})

	def place(self, op: markup.Op, exclude: dict | None = None) -> tuple[dict, int | None] | None:
		"""(parent, index) for `@parent [n]`, `after @ref` or `before @ref`; index None appends."""
		mode, ref, index = op.where
		target = self.resolve(op, ref)
		if target is None:
			return None
		if mode == "into":
			count = len(target.get("children") or [])
			return target, (count + 1 + index if index is not None and index < 0 else index)
		parent = self.tree.parent_of(target["blockId"])
		if parent is None:
			self.fail(op, f"@{ref} is the page root; `add @{ref}` puts blocks inside it")
			return None
		at = position(parent, target, exclude)
		return parent, at + 1 if mode == "after" else at

	def report(self) -> str:
		applied = self.count - len({f.split(":")[0] for f in self.failures})
		lines = [
			f"Applied {applied} of {self.count} op(s)." if self.failures else f"Applied {self.count} op(s)."
		]
		lines += [f"FAILED {failure}" for failure in self.failures]
		if self.added:
			lines.append("New blocks (refs for follow-up edits):")
			lines.append(self.added_outline())
		return "\n".join(lines)

	def added_outline(self) -> str:
		refs = markup.short_refs(self.tree.root)
		rows = []
		for block_id in self.added:
			block = self.tree.resolve(block_id)
			if block is None:
				continue
			for sub, depth in walk_blocks(block):
				rows.append(outline_row(sub, depth, refs))
		if len(rows) > ADDED_LIMIT:
			rows = [*rows[:ADDED_LIMIT], f"… {len(rows) - ADDED_LIMIT} more (read_page shows them)"]
		return "\n".join(rows)


POSITIONED = frozenset({"relative", "absolute", "fixed", "sticky"})
# Text tags that are never decoration: a span or a link may be a dot or an icon holder
BLANK_TEXT_TAGS = frozenset({"h1", "h2", "h3", "h4", "h5", "h6", "p", "li", "button", "label"})
SECTION_TAGS = frozenset({"section", "header", "footer", "main", "article"})
MEDIA_TAGS = frozenset({"img", "svg", "video", "iframe", "canvas"})
# what makes an empty section a visible band rather than nothing at all
ROOM_STYLES = ("padding", "height", "minHeight", "aspectRatio", "background", "border")


def composition_notes(root: dict) -> str:
	"""What a generated page gets wrong that the markup doesn't show at a glance, as
	refs to act on: absolute blocks pinned to the page instead of their section, small
	uppercase labels over headings past the one the page allows, sections that render
	blank, and text left blank."""
	refs = markup.short_refs(root)
	pinned, eyebrows = [], []
	empty = empty_sections(root)
	# a blank heading inside an empty copy is the copy's to lose, not text to write
	inside_empty = {b.get("blockId") for section in empty for b, _ in walk_blocks(section)}
	empty_refs = [f"@{refs.get(section.get('blockId'))}" for section in empty]
	blank = [
		f"@{refs.get(block.get('blockId'))}"
		for block, _ in walk_blocks(root)
		if is_blank_text(block) and block.get("blockId") not in inside_empty
	]
	for block, _ in walk_blocks(root):
		children = block.get("children") or []
		for child in children:
			if (child.get("baseStyles") or {}).get("position") == "absolute" and (
				(block.get("baseStyles") or {}).get("position") not in POSITIONED
			):
				pinned.append(f"@{refs.get(child.get('blockId'))}")
		eyebrows += [
			f"@{refs.get(first.get('blockId'))}"
			for first, second in pairwise(children)
			if is_micro_label(first) and second.get("element") in ("h1", "h2", "h3") and not is_hidden(first)
		]
	notes = []
	if pinned:
		notes.append(
			f"COMPOSITION CHECK: {', '.join(pinned[:8])} are position:absolute under a parent that is not "
			"positioned, so they pin to the page instead of their section. Move each into the section it "
			"belongs to, or give its parent position:relative."
		)
	if len(eyebrows) > 1:
		notes.append(
			f"AI TELL: {len(eyebrows)} headings carry a small uppercase label above them ({', '.join(eyebrows[:12])}); "
			"a page allows one at most. `remove` the rest (hiding leaves dead blocks), or fold what they say "
			"into the heading or its copy."
		)
	if empty:
		notes.append(
			f"EMPTY SECTION: {', '.join(empty_refs[:8])} "
			"render as blank bands, with nothing in them beyond small labels. A section written again "
			"to restyle an earlier one is an empty copy, not a stylesheet rule: move its declarations "
			"into m{} or t{} on the original's line and remove it. Otherwise give it its content."
		)
	if blank:
		notes.append(
			f"EMPTY TEXT: {', '.join(blank[:12])} are headings or paragraphs with no text, so their "
			"section renders blank. Write their copy in one edit_page script, or remove the ones the "
			"design doesn't need."
		)
	return "".join(f"\n{note}" for note in notes)


def empty_sections(root: dict) -> list[dict]:
	"""The outermost sections that render as blank bands."""
	found, covered = [], set()
	for block, _ in walk_blocks(root):
		if id(block) in covered or not is_empty_section(block):
			continue
		found.append(block)
		covered.update(id(b) for b, _ in walk_blocks(block))
	return found


def is_empty_section(block: dict) -> bool:
	"""A section with no text beyond small labels and nothing to see, that still takes up room."""
	if block.get("element") not in SECTION_TAGS or is_hidden(block):
		return False
	subtree = [b for b, _ in walk_blocks(block)]
	return not any(map(shows_content, subtree)) and any(map(takes_room, subtree))


def takes_room(block: dict) -> bool:
	return any(key.startswith(ROOM_STYLES) for key in block.get("baseStyles") or {})


def shows_content(block: dict) -> bool:
	html = str(block.get("innerHTML") or "")
	return bool(
		block.get("element") in MEDIA_TAGS
		or block.get("isRepeaterBlock")
		or block.get("dynamicValues")
		or block.get("extendedFromComponent")
		or "<svg" in html
		or "url(" in str((block.get("baseStyles") or {}).get("backgroundImage") or "")
		or (re.sub(r"<[^>]+>", " ", html).strip() and not is_micro_label(block))
	)


def is_blank_text(block: dict) -> bool:
	"""A heading or paragraph the generator left without words, nothing bound in their place."""
	return (
		block.get("element") in BLANK_TEXT_TAGS
		and not (block.get("innerHTML") or "").strip()
		and not block.get("children")
		and not block.get("dynamicValues")
		and not block.get("isChildOfComponent")
		and not is_hidden(block)
	)


def is_hidden(block: dict) -> bool:
	return (block.get("baseStyles") or {}).get("display") == "none"


def is_micro_label(block: dict) -> bool:
	styles = block.get("baseStyles") or {}
	if styles.get("textTransform") != "uppercase" or not (block.get("innerHTML") or "").strip():
		return False
	size = re.match(r"([\d.]+)px", str(styles.get("fontSize") or ""))
	return bool(styles.get("letterSpacing")) or (size is not None and float(size.group(1)) <= 14)


def outline_row(block: dict, depth: int, refs: dict) -> str:
	head = block.get("element") or "div"
	if classes := block.get("classes"):
		head += "".join(f".{c}" for c in classes)
	row = f"{'  ' * depth}@{refs.get(block.get('blockId'), block.get('blockId'))} {head}"
	if text := (block.get("innerHTML") or "").strip():
		row += " " + markup.quote(text if len(text) <= 40 else text[:39] + "…")
	if name := block.get("blockName"):
		row += f" // {name}"
	return row


def position(parent: dict, child: dict, exclude: dict | None = None) -> int:
	siblings = [c for c in parent.get("children") or [] if c is not exclude]
	return next((i for i, c in enumerate(siblings) if c is child), len(siblings))


PATCH_KEYS = {
	"style": "base_styles",
	"t_style": "tablet_styles",
	"m_style": "mobile_styles",
	"attrs": "attributes",
	"text": "inner_html",
	"el": "element",
	"classes": "classes",
	"bind": "bind",
	"props": "props",
	"client_script": "client_script",
	"name": "name",
}


STYLE_ARGS = ("base_styles", "tablet_styles", "mobile_styles")


def patch_args(fields: dict) -> dict:
	"""Markup patch fields -> update_block args (the vocabulary tree.py and the canvas
	share). Styles go out normalized, so the canvas mirrors exactly what the tree
	stores; a None value (a removal) passes through."""
	from builder.ai.page_writer import normalize_styles

	args = {PATCH_KEYS[key]: value for key, value in fields.items() if key in PATCH_KEYS}
	for key in STYLE_ARGS:
		if raw := args.get(key):
			args[key] = {**normalize_styles(raw), **{k: None for k, v in raw.items() if v is None}}
	if icon := fields.get("icon"):
		from builder.ai.lucide import lucide_svg

		args["inner_html"] = lucide_svg(icon, 2)
		args.setdefault("attributes", {})["data-lucide"] = icon
	return args
