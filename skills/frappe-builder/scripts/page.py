#!/usr/bin/env python3
"""Pull, outline, lint and push Frappe Builder page block trees through frappectl.

    page.py [-s PROFILE] pull <page name | route | page URL> [--dir .builder]
    page.py outline <workdir | blocks.json>
    page.py [-s PROFILE] lint <workdir | blocks.json>
    page.py [-s PROFILE] push <workdir> [--force]
    page.py [-s PROFILE] publish <workdir>

A workdir holds doc.json (the page as pulled, the rollback), blocks.json (the
working tree, pretty-printed) and data_script.py (the page data script). push
writes draft_blocks, and page_data_script when it changed; the live page
changes when the page is published.
"""

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from urllib.parse import urlparse

TEXT_ELEMENTS = {
	"span",
	"h1",
	"h2",
	"h3",
	"h4",
	"h5",
	"h6",
	"p",
	"b",
	"label",
	"a",
	"cite",
	"li",
	"strong",
	"em",
	"i",
	"blockquote",
	"summary",
	"button",
}
CODE_ELEMENTS = {"script", "style", "link", "meta"}
LENGTH_PROPS = re.compile(
	r"^(width|height|minWidth|maxWidth|minHeight|maxHeight|top|right|bottom|left|gap|rowGap|columnGap"
	r"|fontSize|letterSpacing|borderRadius|(padding|margin)(Top|Right|Bottom|Left)?)$"
)
SIDES = ("Top", "Right", "Bottom", "Left")
# shorthand -> longhands it resets; stored style keys are sorted, so a longhand
# that sorts before its shorthand is silently overridden on the published page
SHORTHANDS = {
	"borderWidth": [f"border{s}" for s in SIDES] + [f"border{s}Width" for s in SIDES],
	"borderStyle": [f"border{s}" for s in SIDES] + [f"border{s}Style" for s in SIDES],
	"borderColor": [f"border{s}" for s in SIDES] + [f"border{s}Color" for s in SIDES],
	"inset": ["top", "right", "bottom", "left"],
	"gap": ["rowGap", "columnGap"],
	"placeItems": ["alignItems", "justifyItems"],
	"placeContent": ["alignContent", "justifyContent"],
	"placeSelf": ["alignSelf", "justifySelf"],
}
# JSON depth the oldest sites' CHECK (json_valid(...)) constraint rejects
MAX_JSON_DEPTH = 32


class Frappectl:
	def __init__(self, profile: str | None):
		self.base = ["frappectl", *(["-s", profile] if profile else []), "--json"]

	def run(self, *args: str, hint: str = "") -> object:
		result = subprocess.run([*self.base, *args], capture_output=True, text=True, stdin=subprocess.DEVNULL)
		if result.returncode:
			sys.exit("\n".join(filter(None, [result.stderr.strip() or f"frappectl {args[0]} failed", hint])))
		return json.loads(result.stdout) if result.stdout.strip() else None

	def list_names(self, doctype: str, **filters: str) -> list[dict]:
		flags = [f for key, value in filters.items() for f in ("-f", f"{key}={value}")]
		return self.run("doc", "list", doctype, *flags, "--fields", "name,route", "--limit", "2")

	def find_page(self, ref: str) -> str:
		route = urlparse(ref).path.strip("/") if "://" in ref else ref.strip("/")
		for filters in ({"name": ref}, {"route": route}):
			if pages := self.list_names("Builder Page", **filters):
				return pages[0]["name"]
		sys.exit(f"No Builder Page with name or route '{ref}'")


class Block:
	def __init__(self, data: dict, path: str):
		self.data = data
		self.path = path

	def __getattr__(self, key):
		return self.data.get(key)

	@property
	def label(self) -> str:
		return f"{self.path} {self.element or '?'}#{self.blockId or ''}" + (
			f" ({self.blockName})" if self.blockName else ""
		)

	@property
	def children(self) -> list["Block"]:
		return [
			Block(child, f"{self.path}.{index}")
			for index, child in enumerate(self.data.get("children") or [])
			if isinstance(child, dict)
		]

	def walk(self):
		yield self
		for child in self.children:
			yield from child.walk()

	def style_maps(self):
		for field in ("baseStyles", "tabletStyles", "mobileStyles"):
			if isinstance(self.data.get(field), dict):
				yield field, self.data[field]

	def bindings(self) -> list[dict]:
		keys = [self.dataKey] if isinstance(self.dataKey, dict) and self.dataKey.get("key") else []
		return keys + [v for v in self.dynamicValues or [] if isinstance(v, dict)]


class Linter:
	def __init__(self, roots: list[dict], tokens: set[str] | None, components: set[str] | None):
		self.roots = [Block(root, str(index)) for index, root in enumerate(roots)]
		self.tokens = tokens
		self.components = components
		self.issues: list[tuple[str, str, str]] = []

	def add(self, level: str, block: Block, message: str):
		self.issues.append((level, block.label, message))

	def run(self) -> list[tuple[str, str, str]]:
		if len(self.roots) != 1:
			self.issues.append(("error", "-", f"expected one root block, found {len(self.roots)}"))
		seen: dict[str, str] = {}
		for root in self.roots:
			for block in root.walk():
				if block.blockId and block.blockId in seen:
					self.add("error", block, f"duplicate blockId, also at {seen[block.blockId]}")
				seen.setdefault(block.blockId or "", block.path)
				self.check_block(block)
		depth = json_depth(self.roots[0].data) if self.roots else 0
		if depth >= MAX_JSON_DEPTH:
			self.issues.append(
				("warn", "-", f"JSON depth {depth}: older sites reject saves past {MAX_JSON_DEPTH - 1}")
			)
		return self.issues

	def check_block(self, block: Block):
		self.check_element(block)
		self.check_styles(block)
		self.check_bindings(block)
		self.check_component(block)

	def check_element(self, block: Block):
		element = (block.element or "").lower()
		if element in CODE_ELEMENTS:
			self.add(
				"error", block, f"<{element}> block bypasses the page's scripts; use a Builder Client Script"
			)
		original = block.originalElement
		if original and original not in ("body", "__raw_html__") and original != block.element:
			self.add("warn", block, f"originalElement '{original}' renders instead of element '{element}'")
		html = block.innerHTML or ""
		if html and element not in TEXT_ELEMENTS and element != "svg" and original != "__raw_html__":
			if "<" not in html:
				self.add("warn", block, "text on a non-text element is invisible in the editor canvas")
		if "{{" in html or any("{{" in str(v) for v in (block.attributes or {}).values()):
			self.add(
				"error",
				block,
				"{{ }} runs as Jinja when published but shows raw in the editor; use a binding",
			)
		if "darkSrc" in (block.customAttributes or {}):
			self.add("error", block, "darkSrc belongs in attributes, not customAttributes")

	def check_styles(self, block: Block):
		responsive = set((block.mobileStyles or {}).keys())
		for field, styles in block.style_maps():
			for key, value in styles.items():
				self.check_style_value(block, field, key, value)
			self.check_shorthands(block, field, styles)
		base = block.baseStyles or {}
		needs_mobile = base.get("position") in ("absolute", "sticky") or "vw" in str(base.get("fontSize", ""))
		if needs_mobile and not responsive:
			self.add("warn", block, "absolute/sticky/vw type ships no mobileStyles fallback")

	def check_style_value(self, block: Block, field: str, key: str, value):
		prop = key.split(":", 1)[-1]
		if "-" in prop and not prop.startswith("--"):
			self.add("error", block, f"{field}.{key}: CSS property names are camelCase")
		if isinstance(value, int | float) and value and LENGTH_PROPS.match(prop):
			self.add("error", block, f"{field}.{key}: {value} needs a unit")
		text = str(value)
		if re.search(r"var\(--[^,)]+,", text):
			self.add("warn", block, f"{field}.{key}: drop the var() fallback, it drifts from the token")
		if prop == "background" and ("gradient" in text or "var(" in text):
			self.add("warn", block, f"{field}.{key}: use backgroundImage / backgroundColor")
		if prop == "fontFamily" and (re.search(r"[,'\"]", text) or text.strip() == "inherit"):
			self.add("error", block, f"{field}.fontFamily: one bare family name ({text!r})")
		if self.tokens is not None:
			for handle in re.findall(r"var\(--([\w-]+)", text):
				if handle not in self.tokens:
					self.add("warn", block, f"{field}.{key}: var(--{handle}) is not a Builder Token name")

	def check_shorthands(self, block: Block, field: str, styles: dict):
		for shorthand, longhands in SHORTHANDS.items():
			if shorthand not in styles:
				continue
			for longhand in longhands:
				if longhand in styles and longhand < shorthand:
					self.add(
						"error",
						block,
						f"{field}: {shorthand} is stored after {longhand} and overrides it; set longhands only",
					)

	def check_bindings(self, block: Block):
		if block.isRepeaterBlock:
			if len(block.children) != 1:
				self.add("warn", block, f"repeater renders children[0] only, has {len(block.children)}")
		for binding in block.bindings():
			key = str(binding.get("key", ""))
			if not re.fullmatch(r"[A-Za-z_][\w.]*", key):
				self.add("error", block, f"binding key '{key}' must be a bare dotted key")
			if (
				binding.get("property") == "innerHTML"
				and not block.isRepeaterBlock
				and block.element
				and block.element not in TEXT_ELEMENTS
			):
				self.add("warn", block, "bound text on a non-text element shows empty in the canvas")
		condition = block.visibilityCondition
		if (
			isinstance(condition, dict)
			and condition.get("key")
			and not re.fullmatch(r"[\w.]+", condition["key"])
		):
			self.add("error", block, f"visibility key '{condition['key']}' must be a bare dotted key")

	def check_component(self, block: Block):
		component = block.extendedFromComponent
		if not component:
			return
		if not block.children:
			self.add("error", block, "component instance without skeleton children publishes empty")
		if self.components is not None and component not in self.components:
			self.add("error", block, f"component '{component}' does not exist on the site")


def json_depth(value, depth: int = 1) -> int:
	if isinstance(value, dict):
		return max((json_depth(v, depth + 1) for v in value.values()), default=depth)
	if isinstance(value, list):
		return max((json_depth(v, depth + 1) for v in value), default=depth)
	return depth


def parse_blocks(raw) -> list:
	value = json.loads(raw) if isinstance(raw, str) else raw
	if isinstance(value, dict):
		value = [value]
	return value or []


def blocks_path(target: str) -> Path:
	path = Path(target)
	return path / "blocks.json" if path.is_dir() else path


def outline_line(block: Block, depth: int) -> str:
	element = block.element or ("ref" if block.referenceBlockId else "?")
	parts = [f"{'  ' * depth}{block.blockId or '-'} {element}"]
	if block.blockName:
		parts.append(f"'{block.blockName}'")
	if block.classes:
		parts.append("." + ".".join(block.classes))
	if block.extendedFromComponent:
		parts.append(f"[component {block.extendedFromComponent}]")
	if block.referenceBlockId:
		parts.append(f"[of {block.referenceBlockId}]")
	if block.isRepeaterBlock:
		parts.append(f"[repeat {(block.dataKey or {}).get('key') or 'from definition'}]")
	if bound := [f"{b.get('property')}<-{b.get('key')}" for b in block.bindings() if b.get("property")]:
		parts.append("[bind " + ", ".join(bound) + "]")
	if text := re.sub(r"<[^>]+>|\s+", " ", block.innerHTML or "").strip():
		parts.append(repr(text[:60]))
	return " ".join(parts)


def print_outline(block: Block, depth: int = 0):
	print(outline_line(block, depth))
	for child in block.children:
		print_outline(child, depth + 1)


def cmd_pull(ctl: Frappectl, args):
	name = ctl.find_page(args.page)
	doc = ctl.run("doc", "get", "Builder Page", name)
	workdir = Path(args.dir) / name
	if has_unpushed_edits(workdir):
		sys.exit(f"{workdir} has edits you haven't pushed; push them, or pull into another --dir")
	workdir.mkdir(parents=True, exist_ok=True)
	source = "draft_blocks" if parse_blocks(doc.get("draft_blocks")) else "blocks"
	(workdir / "doc.json").write_text(json.dumps(doc, indent=1))
	(workdir / "blocks.json").write_text(json.dumps(parse_blocks(doc.get(source)), indent=1))
	(workdir / "data_script.py").write_text(doc.get("page_data_script") or "")
	state = "published" if doc.get("published") else "staging" if doc.get("staging") else "unpublished"
	print(f"{workdir}  route=/{doc.get('route')}  {state}  working tree from {source}")
	if source == "draft_blocks" and parse_blocks(doc.get("blocks")) != parse_blocks(doc["draft_blocks"]):
		print("note: the page has unpublished edits; publishing ships them together with yours")


def has_unpushed_edits(workdir: Path) -> bool:
	if not (workdir / "doc.json").exists() or not (workdir / "blocks.json").exists():
		return False
	doc = json.loads((workdir / "doc.json").read_text())
	pulled = parse_blocks(doc.get("draft_blocks")) or parse_blocks(doc.get("blocks"))
	script = workdir / "data_script.py"
	script_changed = script.exists() and script.read_text() != (doc.get("page_data_script") or "")
	return script_changed or parse_blocks((workdir / "blocks.json").read_text()) != pulled


def cmd_outline(args):
	for index, root in enumerate(parse_blocks(blocks_path(args.target).read_text())):
		print_outline(Block(root, str(index)))


def site_names(ctl: Frappectl | None, doctype: str) -> set[str] | None:
	if not ctl:
		return None
	return {row["name"] for row in ctl.run("doc", "list", doctype, "--fields", "name", "--all")}


def lint(ctl: Frappectl | None, path: Path) -> int:
	roots = parse_blocks(path.read_text())
	issues = Linter(roots, site_names(ctl, "Builder Token"), site_names(ctl, "Builder Component")).run()
	for level, where, message in issues:
		print(f"{level:5} {where}: {message}")
	errors = sum(1 for level, _, _ in issues if level == "error")
	print(f"{errors} errors, {len(issues) - errors} warnings")
	return errors


def cmd_push(ctl: Frappectl, args):
	workdir = Path(args.workdir)
	doc = json.loads((workdir / "doc.json").read_text())
	if lint(ctl, workdir / "blocks.json") and not args.force:
		sys.exit("lint errors: fix them, or pass --force")
	if not doc.get("_snapshot"):
		ctl.run(
			"method",
			"call",
			"create_manual_snapshot",
			"--doctype",
			"Builder Page",
			"--name",
			doc["name"],
			"-F",
			"label=Before agent edit",
		)
	blocks = json.loads((workdir / "blocks.json").read_text())
	update = {"draft_blocks": json.dumps(blocks, separators=(",", ":")), "modified": doc["modified"]}
	data_script = workdir / "data_script.py"
	if data_script.exists() and data_script.read_text() != (doc.get("page_data_script") or ""):
		update["page_data_script"] = data_script.read_text()
	update_path = workdir / "update.json"
	update_path.write_text(json.dumps(update))
	try:
		ctl.run(
			"doc",
			"update",
			"Builder Page",
			doc["name"],
			"--input",
			str(update_path),
			hint="Someone saved the page after your pull: pull into another --dir, merge, push from there.",
		)
	finally:
		update_path.unlink()
	refresh(ctl, workdir, doc)
	print(f"draft saved on {doc['name']}; the live page keeps its blocks until publish")
	if "page_data_script" in update:
		print("page_data_script has no draft: the live page runs the new script already")


def refresh(ctl: Frappectl, workdir: Path, doc: dict):
	fresh = ctl.run("doc", "get", "Builder Page", doc["name"])
	doc.update(
		modified=fresh["modified"],
		published=fresh.get("published"),
		blocks=fresh.get("blocks"),
		draft_blocks=fresh.get("draft_blocks"),
		page_data_script=fresh.get("page_data_script"),
		_snapshot=True,
	)
	(workdir / "doc.json").write_text(json.dumps(doc, indent=1))


def cmd_publish(ctl: Frappectl, args):
	workdir = Path(args.workdir)
	doc = json.loads((workdir / "doc.json").read_text())
	route = ctl.run("method", "call", "publish", "--doctype", "Builder Page", "--name", doc["name"])
	refresh(ctl, workdir, doc)
	print(f"published {doc['name']} at /{route}")


def main():
	parser = argparse.ArgumentParser(
		description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
	)
	parser.add_argument("-s", "--site", help="frappectl profile")
	sub = parser.add_subparsers(dest="command", required=True)
	pull = sub.add_parser("pull")
	pull.add_argument("page")
	pull.add_argument("--dir", default=".builder")
	sub.add_parser("outline").add_argument("target")
	sub.add_parser("lint").add_argument("target")
	push = sub.add_parser("push")
	push.add_argument("workdir")
	push.add_argument("--force", action="store_true", help="push despite lint errors")
	sub.add_parser("publish").add_argument("workdir")
	args = parser.parse_args()

	if args.command == "outline":
		return cmd_outline(args)
	ctl = Frappectl(args.site)
	if args.command == "pull":
		return cmd_pull(ctl, args)
	if args.command == "lint":
		site_aware = args.site or os.environ.get("FRAPPE_SITE")
		sys.exit(1 if lint(ctl if site_aware else None, blocks_path(args.target)) else 0)
	if args.command == "publish":
		return cmd_publish(ctl, args)
	return cmd_push(ctl, args)


if __name__ == "__main__":
	main()
