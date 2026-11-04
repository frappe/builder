"""Page markup: the line format Bob reads and writes block trees in.

One block per line, two-space indentation for nesting:

	$label {font-size:11px;letter-spacing:.1em;color:$brand-ink}
	@k3x9 section.hero [id=menu] {display:flex;gap:24px} m{padding:40px 16px} // Hero
	  p $label "Since 1994"
	  a [href=/menu] "Book a table" {color:$brand-ink} :hover{opacity:.8}

A block line is an optional @ref (an existing block), the tag with its .classes,
then segments in any order: $set uses, [attrs], "text" (innerHTML), {css} desktop,
t{css} tablet, m{css} mobile, a :state{css} group on any of those, and the calls
icon(name), use(component), of(block), bind(prop=key), if(key), repeat(key),
props(name=value). A trailing `// Name` labels the block. A `js |` or `css |`
line opens a client-script body indented below its block.

`$name {css} m{css}` on its own line defines a style set; `$name` on a block line
spreads it into that block (the block's own declarations win). Inside a value,
`$token` is `var(--token)`. Sets are a notation only: storage keeps each block's
full camelCase styles.

Lines parse into the codec node shape (BlockCodec.compress /
page_writer.convert_node), so the normalizers and guards on that path
apply to markup unchanged.
"""

import json
import re
from collections import Counter
from dataclasses import dataclass, field
from itertools import combinations

from builder.ai.page_writer import kebab_to_camel

INDENT = "  "
MIN_REF = 4
STATES = frozenset(
	{
		"hover",
		"focus",
		"active",
		"visited",
		"focus-visible",
		"focus-within",
		"disabled",
		"checked",
		"placeholder",
		"first-child",
		"last-child",
	}
)
CALLS = ("icon", "use", "of", "in", "bind", "if", "repeat", "props")
DEVICES = (("", "style"), ("t", "t_style"), ("m", "m_style"))
DEVICE_KEYS = dict(DEVICES)
STYLE_GROUP = re.compile(r"([tm])?(?::([a-z-]+))?\{")
WORD = re.compile(r"[A-Za-z_][\w-]*")
HEAD = re.compile(r"([a-z][a-z0-9-]*)?((?:\.[\w:/-]+)*)", re.I)
BARE_VALUE = re.compile(r"^[^\s\[\]{}()\"'=;]+$")
RAW_BLOCK = re.compile(r"^(js|css)\s*\|\s*$")
COMMENTS = ("```", "//", "#")
CSS_PROPERTY = re.compile(r"^(--[\w-]+|-?[A-Za-z][A-Za-z0-9-]*)$")
# Block fields a model sometimes writes inside {}: none is a CSS property, so each
# has one meaning and moves to where it belongs instead of landing as a dead style.
MISPLACED_TEXT = frozenset({"text", "innerHTML", "innerHtml", "html", "innerText"})
MISPLACED_ATTRS = frozenset(
	{"src", "href", "alt", "id", "title", "target", "rel", "placeholder", "type", "name", "value"}
)
MISPLACED_CLASSES = frozenset({"class", "classes", "className"})
VAR_TOKEN = re.compile(r"var\(\s*--([\w-]+)\s*\)")
DOLLAR_TOKEN = re.compile(r"(\"[^\"]*\"|'[^']*')|(?<![\w$])\$([\w-]+)")


class MarkupError(ValueError):
	pass


def camel_to_kebab(key: str) -> str:
	if key.startswith("--"):
		return key
	return re.sub(r"[A-Z]", lambda m: "-" + m.group(0).lower(), key)


def css_key(key: str) -> str:
	return key if key.startswith("--") else kebab_to_camel(key.strip())


def to_tokens(value) -> str:
	text = re.sub(r"\s*\n\s*", " ", str(value))
	for mark in "'\"":
		if text.count(mark) % 2:
			text = text.replace(mark, "")
	return VAR_TOKEN.sub(r"$\1", text)


def from_tokens(value: str) -> str:
	return DOLLAR_TOKEN.sub(lambda m: m.group(1) or f"var(--{m.group(2)})", value)


def split_state(key: str) -> tuple[str, str]:
	if ":" in key and not key.startswith("--"):
		state, _, prop = key.partition(":")
		return state, prop
	return "", key


# --- reading: block tree -> markup -------------------------------------------


def short_refs(root: dict) -> dict[str, str]:
	"""Each blockId's shortest unique prefix (git-style, at least MIN_REF chars)."""
	from builder.ai.agent.selectors import walk_blocks

	ids = sorted({b["blockId"] for b, _ in walk_blocks(root) if b.get("blockId")})
	refs = {}
	for i, block_id in enumerate(ids):
		neighbours = [ids[j] for j in (i - 1, i + 1) if 0 <= j < len(ids)]
		shared = max((common_prefix(block_id, other) for other in neighbours), default=0)
		refs[block_id] = block_id[: max(MIN_REF, shared + 1)]
	return refs


def common_prefix(a: str, b: str) -> int:
	n = 0
	while n < min(len(a), len(b)) and a[n] == b[n]:
		n += 1
	return n


def quote(text: str) -> str:
	return json.dumps(text, ensure_ascii=False)


def scalar(value) -> str:
	if isinstance(value, str):
		return value if BARE_VALUE.match(value) else quote(value)
	return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def pairs(mapping: dict) -> str:
	return " ".join(f"{k}={scalar(v)}" if v != "" else k for k, v in mapping.items())


def css_groups(styles: dict) -> list[str]:
	"""One device's styles as `{plain}` then one `:state{…}` group per state."""
	groups: dict[str, list[str]] = {}
	for key, value in styles.items():
		if value is None or value == "":
			continue
		state, prop = split_state(key)
		groups.setdefault(state, []).append(f"{camel_to_kebab(prop)}:{to_tokens(value)}")
	return [f"{':' + state if state else ''}{{{';'.join(decls)}}}" for state, decls in groups.items()]


def style_segments(node: dict) -> list[str]:
	return [device + group for device, key in DEVICES for group in css_groups(node.get(key) or {})]


def shorthand_of(a: str, b: str) -> bool:
	"""`border` vs `borderBottom`: declaring both makes their order significant."""
	return b.startswith(a) and len(b) > len(a) and b[len(a)].isupper()


class StyleSets:
	"""Factor declaration sets that repeat across blocks into named sets, the way a
	stylesheet factors classes. Greedy on bitset postings: each round takes the set
	whose sharing saves the most characters. A block only takes a set when none of
	its remaining declarations is a shorthand/longhand twin of one in the set, so
	the spread order can't change what renders."""

	MIN_GAIN = 40
	MAX_SETS = 48
	MAX_NODES = 800

	def __init__(self, nodes: list[dict], prefix: str = "s"):
		self.nodes = nodes
		self.prefix = prefix
		self.atoms: dict[tuple, int] = {}
		self.atom_list: list[tuple] = []
		self.sets_of: list[set[int]] = [self.atom_ids(node) for node in nodes]
		self.uses: dict[int, list[str]] = {}
		self.definitions: list[tuple[str, frozenset]] = []

	def atom_ids(self, node: dict) -> set[int]:
		ids = set()
		for device, key in DEVICES:
			for prop, value in (node.get(key) or {}).items():
				if value is None or value == "":
					continue
				atom = (device, prop, str(value))
				if atom not in self.atoms:
					self.atoms[atom] = len(self.atom_list)
					self.atom_list.append(atom)
				ids.add(self.atoms[atom])
		return ids

	def width(self, atom_id: int) -> int:
		device, prop, value = self.atom_list[atom_id]
		return len(device) + len(prop) + len(value) + 3

	def factor(self) -> "StyleSets":
		if len(self.nodes) > self.MAX_NODES:
			return self
		posting, pool, dead = self.postings(), self.candidates(), set()
		while len(self.definitions) < self.MAX_SETS and (best := self.best(pool, posting, dead)):
			members = self.compatible(best, self.members(best, posting))
			if self.gain(best, len(members)) < self.MIN_GAIN:
				dead.add(best)
			else:
				self.apply(best, members, posting)
		return self

	def postings(self) -> dict[int, int]:
		posting: dict[int, int] = {}
		for index, atoms in enumerate(self.sets_of):
			for atom in atoms:
				posting[atom] = posting.get(atom, 0) | (1 << index)
		return posting

	def candidates(self) -> set[frozenset]:
		rich = Counter(frozenset(s) for s in self.sets_of if len(s) >= 2)
		pool = {a & b for a, b in combinations(rich, 2)}
		pool |= {s for s, count in rich.items() if count > 1}
		return {s for s in pool if len(s) >= 2}

	def members(self, candidate: frozenset, posting: dict[int, int]) -> list[int]:
		mask = -1
		for atom in candidate:
			mask &= posting.get(atom, 0)
		return [i for i in range(len(self.nodes)) if mask >> i & 1] if mask > 0 else []

	def gain(self, candidate: frozenset, count: int) -> int:
		if count < 2:
			return 0
		cost = sum(self.width(a) for a in candidate)
		name = len(self.prefix) + len(str(len(self.definitions) + 1)) + 1
		return (count - 1) * cost - count * (name + 1) - name - 4

	def best(self, pool: set[frozenset], posting: dict[int, int], dead: set) -> frozenset | None:
		best, best_gain = None, self.MIN_GAIN
		for candidate in pool:
			if candidate in dead:
				continue
			mask = -1
			for atom in candidate:
				mask &= posting.get(atom, 0)
			gain = self.gain(candidate, mask.bit_count() if mask > 0 else 0)
			if gain > best_gain:
				best, best_gain = candidate, gain
		return best

	def compatible(self, candidate: frozenset, members: list[int]) -> list[int]:
		keyed = [self.atom_list[a] for a in candidate]
		return [i for i in members if not self.conflicts(keyed, self.sets_of[i] - candidate)]

	def conflicts(self, keyed: list[tuple], rest: set[int]) -> bool:
		for device, prop, _ in keyed:
			state, name = split_state(prop)
			for other in rest:
				o_device, o_prop, _ = self.atom_list[other]
				o_state, o_name = split_state(o_prop)
				if (
					device == o_device
					and state == o_state
					and (shorthand_of(name, o_name) or shorthand_of(o_name, name))
				):
					return True
		return False

	def apply(self, candidate: frozenset, members: list[int], posting: dict[int, int]) -> None:
		name = f"{self.prefix}{len(self.definitions) + 1}"
		self.definitions.append((name, candidate))
		mask = 0
		for i in members:
			self.sets_of[i] -= candidate
			self.uses.setdefault(i, []).append(name)
			mask |= 1 << i
		for atom in candidate:
			posting[atom] &= ~mask

	def remaining(self, index: int) -> dict:
		"""The node's styles minus everything its sets carry, in stored order."""
		node, keep = self.nodes[index], self.sets_of[index]
		out = {}
		for device, key in DEVICES:
			styles = {
				prop: value
				for prop, value in (node.get(key) or {}).items()
				if self.atoms.get((device, prop, str(value))) in keep
			}
			if styles:
				out[key] = styles
		return out

	def table(self) -> dict[str, dict]:
		"""name -> {style, t_style, m_style}: what `$name` spreads when an edit uses it."""
		out = {}
		for name, atoms in self.definitions:
			grouped: dict[str, dict] = {}
			for atom in sorted(atoms):
				device, prop, value = self.atom_list[atom]
				grouped.setdefault(DEVICE_KEYS[device], {})[prop] = value
			out[name] = grouped
		return out

	def definition_lines(self) -> list[str]:
		return [" ".join([f"${name}", *style_segments(styles)]) for name, styles in self.table().items()]


class Dumper:
	"""Codec nodes (BlockCodec.compress output) -> markup lines."""

	def __init__(
		self,
		refs: dict | None = None,
		styles: bool = True,
		max_text: int | None = None,
		set_prefix: str | None = "s",
	):
		self.refs = refs or {}
		self.styles = styles
		self.max_text = max_text
		self.set_prefix = set_prefix
		self.sets: StyleSets | None = None
		self.index: dict[int, int] = {}

	def dump(self, node: dict) -> str:
		lines: list[str] = []
		if self.styles and self.set_prefix:
			nodes = list(walk_nodes(node))
			self.index = {id(n): i for i, n in enumerate(nodes)}
			self.sets = StyleSets(nodes, self.set_prefix).factor()
			if defs := self.sets.definition_lines():
				lines.extend([*defs, ""])
		self.walk(node, 0, None, lines)
		return "\n".join(lines)

	def walk(self, node: dict, depth: int, parent_component: str | None, lines: list[str]) -> None:
		pad = INDENT * depth
		lines.append(pad + self.line(node, parent_component))
		for kind in ("js", "css"):
			if self.styles and (code := (node.get("client_script") or {}).get(kind)):
				lines.append(f"{pad}{INDENT}{kind} |")
				lines.extend(f"{pad}{INDENT * 2}{row}" if row else "" for row in code.split("\n"))
		owner = node.get("component") or node.get("child_of") or parent_component
		for child in node.get("c") or []:
			if isinstance(child, dict):
				self.walk(child, depth + 1, owner, lines)

	def line(self, node: dict, parent_component: str | None) -> str:
		parts = []
		if ref := node.get("ref"):
			parts.append("@" + self.refs.get(ref, ref))
		if head := self.head(node):
			parts.append(head)
		if self.styles:
			parts.extend(self.style_parts(node))
		if attrs := node.get("attrs"):
			parts.append(f"[{pairs(attrs)}]")
		if text := node.get("text"):
			parts.append(quote(self.clip(str(text))))
		if self.styles:
			parts.extend(style_segments(self.own_styles(node)))
		parts.extend(self.calls(node, parent_component))
		label = node.get("name")
		if label and label != f"Icon: {node.get('icon')}":
			parts.append("// " + re.sub(r"\s+", " ", str(label)))
		return " ".join(parts)

	def style_parts(self, node: dict) -> list[str]:
		index = self.index.get(id(node))
		return [f"${name}" for name in self.sets.uses.get(index, [])] if self.sets else []

	def own_styles(self, node: dict) -> dict:
		index = self.index.get(id(node))
		return self.sets.remaining(index) if self.sets and index is not None else node

	def head(self, node: dict) -> str:
		base = f"icon({node['icon']})" if node.get("icon") else node.get("el") or ""
		return base + "".join(f".{c}" for c in node.get("classes") or [])

	def calls(self, node: dict, parent_component: str | None) -> list[str]:
		out = []
		if component := node.get("component"):
			out.append(f"use({component})")
		if of := node.get("of"):
			out.append(f"of({of})")
		if (child_of := node.get("child_of")) and child_of != parent_component and not node.get("component"):
			out.append(f"in({child_of})")
		if props := node.get("props"):
			out.append(f"props({pairs(props)})")
		bind = dict(node.get("bind") or {})
		visible = bind.pop("visible", None)
		if bind:
			out.append(f"bind({pairs({('text' if k == 'innerHTML' else k): v for k, v in bind.items()})})")
		if visible:
			out.append(f"if({visible})")
		if repeat := node.get("repeat"):
			out.append(f"repeat({repeat.get('data')})")
		return out

	def clip(self, text: str) -> str:
		if self.max_text and len(text) > self.max_text:
			return text[: self.max_text - 1] + "…"
		return text

	def sets_table(self) -> dict[str, dict]:
		return self.sets.table() if self.sets else {}


def walk_nodes(node: dict):
	yield node
	for child in node.get("c") or []:
		if isinstance(child, dict):
			yield from walk_nodes(child)


def dump_block(
	block: dict,
	*,
	refs: dict | None = None,
	styles: bool = True,
	max_text: int | None = None,
	set_prefix: str | None = "s",
	sets: dict | None = None,
) -> str:
	"""A stored block (and its subtree) as markup. `sets`, when given, collects the
	style sets the text defines, so a later edit script can use them by name."""
	from builder.ai.block_codec import BlockCodec

	dumper = Dumper(refs, styles, max_text, set_prefix)
	text = dumper.dump(BlockCodec.compress(block))
	if sets is not None:
		sets.update(dumper.sets_table())
	return text


# --- writing: markup -> codec nodes ------------------------------------------


@dataclass
class Line:
	indent: int
	number: int
	refs: list[str] = field(default_factory=list)
	node: dict = field(default_factory=dict)


class Scanner:
	"""Cursor over one line's text, aware of quotes and nested brackets."""

	PAIRS = {"{": "}", "[": "]", "(": ")"}  # noqa: RUF012

	def __init__(self, text: str, number: int):
		self.text = text
		self.pos = 0
		self.number = number

	def done(self) -> bool:
		self.pos = len(self.text) - len(self.text[self.pos :].lstrip())
		return self.pos >= len(self.text)

	def rest(self) -> str:
		return self.text[self.pos :]

	def fail(self, why: str) -> MarkupError:
		return MarkupError(f"line {self.number}: {why} at `{self.rest()[:40]}`")

	def string(self) -> str:
		quote_char = self.text[self.pos]
		end = self.pos + 1
		while end < len(self.text) and self.text[end] != quote_char:
			end += 2 if self.text[end] == "\\" else 1
		if end >= len(self.text):
			raise self.fail("unclosed string")
		raw = self.text[self.pos : end + 1]
		self.pos = end + 1
		if quote_char == "'":
			raw = '"' + raw[1:-1].replace("\\'", "'").replace('\\"', '"').replace('"', '\\"') + '"'
		try:
			return json.loads(raw)
		except json.JSONDecodeError:
			return raw[1:-1]

	def group(self) -> str:
		"""The inside of the bracketed group at pos; nested brackets and quotes kept whole."""
		opener = self.text[self.pos]
		closer = self.PAIRS[opener]
		depth, i, quote_char = 0, self.pos, None
		while i < len(self.text):
			ch = self.text[i]
			if quote_char:
				if ch == "\\":
					i += 1
				elif ch == quote_char:
					quote_char = None
			elif ch in "\"'":
				quote_char = ch
			elif ch == opener:
				depth += 1
			elif ch == closer:
				depth -= 1
				if depth == 0:
					inner = self.text[self.pos + 1 : i]
					self.pos = i + 1
					return inner
			i += 1
		raise self.fail(f"unclosed {opener}")


def split_top(text: str, sep: str) -> list[str]:
	"""Split on `sep` outside quotes and brackets."""
	parts, depth, quote_char, start, i = [], 0, None, 0, 0
	while i < len(text):
		ch = text[i]
		if quote_char:
			if ch == "\\":
				i += 1
			elif ch == quote_char:
				quote_char = None
		elif ch in "\"'":
			quote_char = ch
		elif ch in "([{":
			depth += 1
		elif ch in ")]}":
			depth -= 1
		elif ch == sep and depth == 0:
			parts.append(text[start:i])
			start = i + 1
		i += 1
	parts.append(text[start:])
	return [p for p in parts if p.strip()]


def parse_css(text: str, state: str | None = None) -> dict:
	"""`a:b;c:d` -> {a: b, c: d} in camelCase. An empty value reads as None (remove)."""
	out = {}
	for decl in split_top(text, ";"):
		prop, sep, value = decl.partition(":")
		if not sep:
			continue
		prop, value, inner_state = prop.strip(), value.strip(), state
		if prop in STATES and WORD.match(value) and ":" in value:
			inner_state = prop
			prop, _, value = value.partition(":")
			prop, value = prop.strip(), value.strip()
		if not CSS_PROPERTY.match(prop):
			raise MarkupError(f"`{prop}` is not a CSS property")
		key = css_key(prop)
		out[f"{inner_state}:{key}" if inner_state else key] = from_tokens(value) if value else None
	return out


def parse_value(text: str, typed: bool = True):
	text = text.strip()
	if not text:
		return ""
	if text[0] in "\"'":
		return Scanner(text, 0).string()
	if typed and (
		text[0] in "[{" or text in ("true", "false", "null") or re.fullmatch(r"-?\d+(\.\d+)?", text)
	):
		try:
			return json.loads(text)
		except json.JSONDecodeError:
			return text
	return text


def parse_pairs(text: str, typed: bool = False) -> dict:
	"""`a=b c="d e" f` -> {a: 'b', c: 'd e', f: ''}; `a=` and `-a` -> {a: None} (remove).
	`typed` reads JSON literals (numbers, true, lists) as values, for props."""
	out = {}
	for token in split_top(text.replace("\n", " "), " "):
		key, sep, value = token.partition("=")
		key = key.strip()
		if key.startswith("-") and not sep:
			out[key[1:]] = None
		else:
			out[key] = (parse_value(value, typed) if value.strip() else None) if sep else ""
	return out


def merge_styles(into: dict, styles: dict) -> None:
	for _, key in DEVICES:
		if styles.get(key):
			into.setdefault(key, {}).update(styles[key])


class LineParser:
	"""One markup line -> (refs, node). Patch lines may omit the tag; `$set` uses
	spread from `sets` before the line's own declarations."""

	def __init__(self, text: str, number: int, sets: dict):
		self.scan = Scanner(text, number)
		self.sets = sets
		self.node: dict = {}
		self.refs: list[str] = []
		self.used: list[str] = []
		self.own: dict = {}

	def parse(self) -> tuple[list[str], dict]:
		scan = self.scan
		while not scan.done() and scan.rest().startswith("@"):
			match = re.match(r"@([\w-]+)", scan.rest())
			if not match:
				raise scan.fail("bad ref")
			self.refs.append(match.group(1))
			scan.pos += match.end()
		self.head()
		while not scan.done():
			self.segment()
		for name in self.used:
			merge_styles(self.node, self.sets[name])
		merge_styles(self.node, self.own)
		return self.refs, self.node

	def head(self) -> None:
		scan = self.scan
		if scan.done() or scan.rest()[0] in "[{\"'/$" or STYLE_GROUP.match(scan.rest()):
			return
		if scan.rest().startswith("icon("):
			scan.pos += 4
			self.node["icon"] = scan.group().strip()
			return
		match = HEAD.match(scan.rest())
		if not match.group(0) or self.is_call(match.group(1)):
			return
		if match.group(1):
			self.node["el"] = match.group(1).lower()
		if match.group(2):
			self.node["classes"] = [c for c in match.group(2).split(".") if c]
		scan.pos += match.end()

	def is_call(self, word: str | None) -> bool:
		return bool(word) and word in CALLS and self.scan.rest()[len(word) : len(word) + 1] == "("

	def segment(self) -> None:
		scan = self.scan
		rest = scan.rest()
		if rest.startswith("//"):
			self.node["name"] = rest[2:].strip()
			scan.pos = len(scan.text)
		elif rest[0] in "\"'":
			self.node["text"] = scan.string()
		elif rest[0] == "[":
			self.node.setdefault("attrs", {}).update(parse_pairs(scan.group()))
		elif rest[0] == "$":
			self.use_set(rest)
		elif match := STYLE_GROUP.match(rest):
			scan.pos += match.end() - 1
			try:
				styles = parse_css(scan.group(), match.group(2))
			except MarkupError as e:
				raise scan.fail(str(e)) from None
			self.rehome(styles)
			self.own.setdefault(DEVICE_KEYS[match.group(1) or ""], {}).update(styles)
		elif (match := WORD.match(rest)) and rest[match.end() : match.end() + 1] == "(":
			scan.pos += match.end()
			self.call(match.group(0), scan.group())
		elif rest[0] == ".":
			match = HEAD.match(rest)
			self.node["classes"] = [c for c in match.group(2).split(".") if c]
			scan.pos += match.end()
		else:
			raise scan.fail("unexpected text")

	def rehome(self, styles: dict) -> None:
		for key in [
			k for k in styles if split_state(k)[1] in MISPLACED_TEXT | MISPLACED_ATTRS | MISPLACED_CLASSES
		]:
			field, value = split_state(key)[1], styles.pop(key)
			value = parse_value(value) if value else ""
			if field in MISPLACED_TEXT:
				self.node["text"] = str(value)
			elif field in MISPLACED_CLASSES:
				self.node["classes"] = str(value).split()
			else:
				self.node.setdefault("attrs", {})[field] = str(value)

	def use_set(self, rest: str) -> None:
		match = WORD.match(rest, 1)
		if not match:
			raise self.scan.fail("`$` needs a style set name")
		if match.group(0) not in self.sets:
			raise self.scan.fail(f"style set ${match.group(0)} is not defined above")
		self.used.append(match.group(0))
		self.scan.pos += match.end()

	def call(self, name: str, args: str) -> None:
		value = args.strip()
		if name == "icon":
			self.node["icon"] = value
		elif name == "use":
			self.node["component"] = value
		elif name == "of":
			self.node["of"] = value.lstrip("@")
		elif name == "in":
			self.node["child_of"] = value
		elif name == "if":
			self.node.setdefault("bind", {})["visible"] = value or None
		elif name == "bind":
			bind = {("innerHTML" if k == "text" else k): (v or None) for k, v in parse_pairs(args).items()}
			self.node.setdefault("bind", {}).update(bind)
		elif name == "props":
			self.node.setdefault("props", {}).update(parse_pairs(args, typed=True))
		elif name == "repeat":
			key, sep, items = value.partition("=")
			self.node["repeat"] = {"data": key.strip()}
			if sep:
				self.node["repeat"]["items"] = parse_value(items)
		else:
			raise self.scan.fail(f"unknown call {name}()")


def define_set(body: str, number: int, sets: dict) -> None:
	match = re.match(r"\$([A-Za-z_][\w-]*)\s*", body)
	if not match:
		raise MarkupError(f"line {number}: a style set is `$name {{css}}`")
	parser = LineParser(body[match.end() :], number, sets)
	refs, node = parser.parse()
	if refs or set(node) - {"style", "t_style", "m_style"}:
		raise MarkupError(f"line {number}: a style set holds only {{css}}, t{{css}} and m{{css}} groups")
	sets[match.group(1)] = node


def parse_lines(
	text: str, first_number: int = 1, sets: dict | None = None, errors: list | None = None
) -> list[Line]:
	"""Markup -> flat Lines; `$set` definitions land in `sets`, raw `js |` / `css |`
	bodies fold into their block. With `errors`, a bad line is skipped and noted
	there instead of raising (a streamed page keeps every good line)."""
	sets = {} if sets is None else sets
	rows = (text or "").replace("\t", INDENT).split("\n")
	lines: list[Line] = []
	i = 0
	while i < len(rows):
		row, number = rows[i], first_number + i
		i += 1
		body = row.strip()
		if not body or body.startswith(COMMENTS):
			continue
		indent = len(row) - len(row.lstrip(" "))
		try:
			if raw := RAW_BLOCK.match(body):
				code, i = raw_body(rows, i, indent)
				owner = next((ln for ln in reversed(lines) if ln.indent < indent), None)
				if owner is None:
					raise MarkupError(f"line {number}: `{body}` has no block above it")
				owner.node.setdefault("client_script", {})[raw.group(1)] = code
			elif body.startswith("$"):
				define_set(body, number, sets)
			else:
				refs, node = LineParser(body, number, sets).parse()
				lines.append(Line(indent=indent, number=number, refs=refs, node=node))
		except MarkupError as e:
			if errors is None:
				raise
			errors.append(str(e))
	return lines


def raw_body(rows: list[str], i: int, indent: int) -> tuple[str, int]:
	body = []
	while i < len(rows) and (not rows[i].strip() or len(rows[i]) - len(rows[i].lstrip(" ")) > indent):
		body.append(rows[i])
		i += 1
	while body and not body[-1].strip():
		body.pop()
	cut = min((len(r) - len(r.lstrip(" ")) for r in body if r.strip()), default=0)
	return "\n".join(r[cut:] for r in body), i


def build_tree(lines: list[Line]) -> list[dict]:
	"""Flat Lines -> nested codec nodes (children under `c`; a repeater's first child is its item)."""
	roots: list[dict] = []
	stack: list[tuple[int, dict]] = []
	for line in lines:
		node = line.node
		if line.refs:
			node["ref"] = line.refs[0]
		while stack and stack[-1][0] >= line.indent:
			stack.pop()
		siblings = stack[-1][1].setdefault("c", []) if stack else roots
		siblings.append(node)
		stack.append((line.indent, node))
	for node in roots:
		settle(node)
	return roots


TEXT_LINE_KEYS = frozenset({"text", "style", "t_style", "m_style"})


def settle(node: dict) -> None:
	"""Fold bare quoted lines into the block above them (the Pug habit: an `h1` line,
	then its text indented below; kept as a child it is a div inside the h1, and a div
	inside a p escapes the p's styles in the browser), and give a repeater its item."""
	children = node.get("c") or []
	for child in children:
		settle(child)
	text_lines = [c for c in children if "text" in c and set(c) <= TEXT_LINE_KEYS]
	if text_lines and "text" not in node:
		node["text"] = " ".join(str(c["text"]) for c in text_lines)
		for line in text_lines:
			merge_styles(node, line)
		children = [c for c in children if c not in text_lines]
		node["c"] = children
		if not children:
			node.pop("c")
	if isinstance(node.get("repeat"), dict) and node.get("c"):
		node["repeat"]["item"] = node["c"][0]
		node["c"] = []


def load(text: str, errors: list | None = None) -> list[dict]:
	"""Markup -> codec node trees (roots in order)."""
	return build_tree(parse_lines(text, errors=errors))


# --- edits: an ops script against an existing tree ---------------------------

OP_HEADER = re.compile(r"^(add|remove|delete|move|replace)\b\s*(.*)$")
TARGET = re.compile(r"^(?:(after|before|into|to)\s+)?@([\w-]+)(?:\s+(?:at\s+)?(-?\d+))?\s*$")


@dataclass
class Op:
	"""One edit: `patch` (fields onto refs), `add` / `replace` (a body of new blocks),
	`remove`, or `move`. `where` = (mode, ref, index), mode one of into/after/before."""

	kind: str
	number: int
	refs: list[str] = field(default_factory=list)
	fields: dict = field(default_factory=dict)
	where: tuple = ("into", None, None)
	body: list[dict] = field(default_factory=list)
	error: str = ""


def parse_ops(text: str, sets: dict | None = None) -> list[Op]:
	"""An edit script -> Ops. A bad op carries its error instead of raising, so the
	good ones still apply and the reply names exactly what to resend. `$set` lines
	define sets for the ops after them; `sets` seeds the ones the last read showed."""
	sets = dict(sets or {})
	rows = (text or "").replace("\t", INDENT).split("\n")
	ops: list[Op] = []
	i = 0
	while i < len(rows):
		body = rows[i].strip()
		number = i + 1
		i += 1
		if not body or body.startswith(COMMENTS):
			continue
		indent = len(rows[i - 1]) - len(rows[i - 1].lstrip(" "))
		end = i
		while end < len(rows) and not starts_op(rows[end], indent):
			end += 1
		ops.append(parse_op(body, number, "\n".join(rows[i:end]), i + 1, sets))
		i = end
	return [op for op in ops if op.kind != "define"]


def starts_op(row: str, indent: int) -> bool:
	body = row.strip()
	if not body:
		return False
	row_indent = len(row) - len(row.lstrip(" "))
	return row_indent <= indent and (body.startswith(("@", "$", *COMMENTS)) or bool(OP_HEADER.match(body)))


def parse_op(header: str, number: int, body: str, body_number: int, sets: dict) -> Op:
	try:
		if header.startswith("$"):
			define_set(header, number, sets)
			return Op("define", number)
		if not (match := OP_HEADER.match(header)):
			return parse_patch(header, number, body, sets)
		verb, rest = match.group(1), match.group(2).strip()
		if verb in ("remove", "delete"):
			if not (refs := re.findall(r"@([\w-]+)", rest)):
				raise MarkupError(f"line {number}: remove which block? `remove @ref`")
			return Op("remove", number, refs=refs)
		if verb == "move":
			moved, _, target = rest.partition(" ")
			return Op("move", number, refs=[moved.lstrip("@")], where=parse_target(target, number))
		nodes = build_tree(parse_lines(body, body_number, sets))
		if not nodes:
			raise MarkupError(f"line {number}: `{verb}` needs the new block(s) indented below it")
		if verb == "replace":
			return Op("replace", number, refs=[parse_target(rest, number)[1]], body=nodes[:1])
		return Op("add", number, where=parse_target(rest, number), body=nodes)
	except MarkupError as e:
		return Op("error", number, error=str(e))


def parse_patch(header: str, number: int, body: str, sets: dict) -> Op:
	lines = parse_lines(header + ("\n" + body if body.strip() else ""), number, sets)
	refs = lines[0].refs
	if not refs:
		raise MarkupError(f"line {number}: start with @ref to change a block, or add/remove/move/replace")
	fields = build_tree(lines)[0]
	fields.pop("ref", None)
	if fields.pop("c", None):
		raise MarkupError(f"line {number}: a patch takes no child blocks; use `add @ref` for children")
	return Op("patch", number, refs=refs, fields=fields)


def parse_target(text: str, number: int) -> tuple:
	match = TARGET.match(text.strip())
	if not match:
		raise MarkupError(
			f"line {number}: target `{text.strip()}`: use `@parent`, `@parent 0`, `after @ref` or `before @ref`"
		)
	mode = match.group(1) if match.group(1) in ("after", "before") else "into"
	index = int(match.group(3)) if match.group(3) is not None else None
	return mode, match.group(2), index
