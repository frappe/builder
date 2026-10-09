"""Checks for block trees. Each rule is a failure reproduced on a live site: a broken
render, a style that silently doesn't apply, a canvas that shows something else, or a
component prop that only does what editing the instance in place already does."""

from __future__ import annotations

import json
import re

TEXT_ELEMENTS = {
	*("span", "h1", "h2", "h3", "h4", "h5", "h6", "p", "b", "label", "a", "cite"),
	*("li", "strong", "em", "i", "blockquote", "summary", "button"),
}
LENGTH_PROPS = re.compile(
	r"^(width|height|minWidth|maxWidth|minHeight|maxHeight|top|right|bottom|left|gap|rowGap|columnGap"
	r"|fontSize|letterSpacing|borderRadius|(padding|margin)(Top|Right|Bottom|Left)?)$"
)
RAW_LAYOUT = re.compile(
	r"<(div|p|h[1-6]|section|article|header|footer|nav|table|ul|ol|form|input|button)\b", re.I
)
RAW_SKIPPED = re.compile(r"<(svg|script|style|iframe)\b.*?</\1>", re.I | re.S)
SIDES = ("Top", "Right", "Bottom", "Left")
# style maps lose their key order on server rewrites (sync, snapshot restore), so a
# shorthand and its longhand in one map end up in alphabetical order
SHORTHANDS = {
	"border": [f"border{s}" for s in SIDES],
	"borderWidth": [f"border{s}" for s in SIDES] + [f"border{s}Width" for s in SIDES],
	"borderStyle": [f"border{s}" for s in SIDES] + [f"border{s}Style" for s in SIDES],
	"borderColor": [f"border{s}" for s in SIDES] + [f"border{s}Color" for s in SIDES],
	"borderRadius": [f"border{v}{h}Radius" for v in ("Top", "Bottom") for h in ("Left", "Right")],
	"padding": [f"padding{s}" for s in SIDES],
	"margin": [f"margin{s}" for s in SIDES],
	"inset": ["top", "right", "bottom", "left"],
	"gap": ["rowGap", "columnGap"],
	"flexFlow": ["flexDirection", "flexWrap"],
}


class Block:
	def __init__(self, data: dict, path: str):
		self.data = data
		self.path = path

	def __getattr__(self, key):
		return self.data.get(key)

	@property
	def label(self) -> str:
		name = f" ({self.blockName})" if self.blockName else ""
		return f"{self.path} {self.element or '?'}#{self.blockId or ''}{name}"

	@property
	def children(self) -> list[Block]:
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

	def reads_prop(self, word: re.Pattern) -> bool:
		condition = self.visibilityCondition if isinstance(self.visibilityCondition, dict) else {}
		keys = [binding.get("key") for binding in self.bindings() if binding.get("comesFrom") == "props"]
		if condition.get("comesFrom") == "props":
			keys.append(condition.get("key"))
		return any(word.search(str(key or "")) for key in keys)

	def script(self) -> dict:
		script = dict(self.clientScript or {})
		if not script.get("js") and self.blockClientScript:
			script["js"] = self.blockClientScript
		return script


class Linter:
	def __init__(
		self,
		roots: list[dict],
		tokens: set[str] | None,
		components: set[str] | None,
		kind="page",
		definitions: dict[str, dict] | None = None,
		data_script: str = "",
	):
		self.roots = [Block(root, str(index)) for index, root in enumerate(roots)]
		self.tokens = tokens
		self.components = components
		self.definitions = definitions or {}
		self.kind = kind
		self.data_script = data_script
		self.issues: list[tuple[str, str, str]] = []

	def add(self, level: str, block: Block | None, message: str):
		self.issues.append((level, block.label if block else "-", message))

	def run(self) -> list[tuple[str, str, str]]:
		if len(self.roots) != 1:
			self.add("error", None, f"expected one root block, found {len(self.roots)}")
		if (
			self.roots
			and self.kind == "page"
			and "body" not in (self.roots[0].originalElement, self.roots[0].element)
		):
			self.add(
				"error",
				self.roots[0],
				'page root needs originalElement "body", or the page drops its scripts',
			)
		seen: dict[str, str] = {}
		for root in self.roots:
			for block in root.walk():
				if block.blockId and block.blockId in seen:
					self.add("error", block, f"duplicate blockId, also at {seen[block.blockId]}")
				seen.setdefault(block.blockId or "", block.path)
				self.check_block(block)
		if self.kind == "component" and self.roots:
			self.check_props(self.roots[0])
		return self.issues

	def check_block(self, block: Block):
		self.check_element(block)
		self.check_jinja(block)
		self.check_styles(block)
		self.check_bindings(block)
		self.check_component(block)
		self.check_script(block)

	def check_element(self, block: Block):
		element = (block.element or "").lower()
		original = block.originalElement
		if original and original not in ("body", "__raw_html__") and original != block.element:
			self.add("warn", block, f"originalElement '{original}' renders instead of element '{element}'")
		html = block.innerHTML or ""
		plain_text = html and "<" not in html
		if plain_text and element not in TEXT_ELEMENTS and element != "svg" and original != "__raw_html__":
			self.add("warn", block, "text on a non-text element is invisible in the editor canvas")
		if "darkSrc" in (block.customAttributes or {}):
			self.add("error", block, "darkSrc only works in attributes, not customAttributes")
		if original == "__raw_html__":
			self.check_raw_html(block, html)

	def check_raw_html(self, block: Block, html: str):
		if re.search(r"<script\b", html, re.I):
			self.add(
				"warn",
				block,
				"a <script> in raw HTML never runs in the editor; use a clientScript or script file",
			)
		markup = RAW_SKIPPED.sub(" ", html)
		words = len(re.sub(r"<[^>]+>", " ", markup).split())
		if words > 25 or (words > 2 and RAW_LAYOUT.search(markup)):
			self.add(
				"warn",
				block,
				"text and layout in raw HTML can't be edited in the editor; build them from blocks",
			)

	def check_jinja(self, block: Block):
		script = block.script()
		fields = {
			"innerHTML": block.innerHTML or "",
			"js": script.get("js") or "",
			"css": script.get("css") or "",
		}
		for name in ("attributes", "customAttributes"):
			fields[name] = " ".join(str(v) for v in (block.data.get(name) or {}).values())
		for name, text in fields.items():
			if ".__" in text:
				self.add("error", block, f"{name}: `.__` fails the whole page, even inside {{% raw %}}")
			if "{#" in text and "{% raw %}" not in text:
				self.add(
					"error",
					block,
					f"{name}: `{{#` opens a Jinja comment and fails the page; wrap in {{% raw %}}",
				)
		if "{{" in fields["innerHTML"] + fields["attributes"] and "{% raw %}" not in fields["innerHTML"]:
			self.add(
				"warn", block, "{{ }} is evaluated on the live page and shown raw in the editor; bind instead"
			)
		if re.search(r"\{%[^%]*[<>&][^%]*%\}", fields["innerHTML"]):
			self.add("error", block, "innerHTML: < > & inside {% %} are HTML-escaped before Jinja runs")

	def check_styles(self, block: Block):
		for field, styles in block.style_maps():
			for key, value in styles.items():
				self.check_style(block, field, key, value)
			for shorthand, longhands in SHORTHANDS.items():
				mixed = (
					[longhand for longhand in longhands if longhand in styles] if shorthand in styles else []
				)
				if mixed:
					self.add(
						"error",
						block,
						f"{field}: {shorthand} with {mixed[0]}; key order isn't kept, use longhands",
					)

	def check_style(self, block: Block, field: str, key: str, value):
		state, _, prop = key.rpartition(":")
		if key.count(":") > 1 or state.startswith(":"):
			self.add("error", block, f"{field}.{key}: one single-colon state only (hover:, before:), no ::")
		if LENGTH_PROPS.match(prop) and re.fullmatch(r"-?\d*\.?\d+", str(value).strip()) and float(value):
			self.add("error", block, f"{field}.{key}: {value!r} has no unit and is ignored")
		text = str(value)
		if text.count("(") != text.count(")"):
			self.add("error", block, f"{field}.{key}: unbalanced parentheses get escaped")
		if prop == "background" and "var(" in text:
			self.add(
				"warn",
				block,
				f"{field}.{key}: the editor canvas drops var() in background; use backgroundColor",
			)
		if prop == "fontFamily" and (re.search(r"[,'\"]", text) or text.strip() == "inherit"):
			self.add("error", block, f"{field}.fontFamily: one bare family name ({text!r})")
		if self.tokens is not None:
			for handle in re.findall(r"var\(--([\w-]+)\)", text):
				if handle not in self.tokens:
					self.add("warn", block, f"{field}.{key}: var(--{handle}) is not a Builder Token name")

	def check_bindings(self, block: Block):
		if block.isRepeaterBlock and len(block.children) != 1:
			self.add("warn", block, f"a repeater renders only its first child, it has {len(block.children)}")
		for binding in block.bindings():
			text_binding = binding.get("property") == "innerHTML" and not block.isRepeaterBlock
			if text_binding and block.element and block.element not in TEXT_ELEMENTS:
				self.add("warn", block, "bound text on a non-text element is empty in the editor canvas")

	def check_component(self, block: Block):
		component = block.extendedFromComponent
		if not component or block.referenceBlockId:
			return
		if not block.children and component not in self.definitions:
			self.add(
				"warn", block, "instance without skeleton children: empty unless the component is one block"
			)
		elif not block.children and self.definitions[component].get("children"):
			self.add("error", block, "component instance without skeleton children renders empty")
		if self.components is not None and component not in self.components:
			self.add("error", block, f"component '{component}' does not exist on the site")

	def check_props(self, root: Block):
		blocks = list(root.walk())
		for name in root.props or {}:
			word = re.compile(rf"\b{re.escape(name)}\b")
			if self.drives_logic(word, blocks):
				continue
			reached = [block for block in blocks if block.reads_prop(word)]
			if not reached:
				self.add("warn", root, f"prop '{name}' is read by no block or script")
			elif len(reached) == 1:
				self.add(
					"warn",
					reached[0],
					f"prop '{name}' only fills this block; leave it unbound and edit it on each instance",
				)

	def drives_logic(self, word: re.Pattern, blocks: list[Block]) -> bool:
		"""A prop that a script, a repeater or a nested component reads does work the editor can't."""
		sources = [self.data_script]
		for block in blocks:
			script = block.script()
			sources += [script.get("js") or "", script.get("css") or ""]
			if block.isRepeaterBlock:
				sources.append(json.dumps(block.dataKey or {}))
			if block.extendedFromComponent:
				sources.append(json.dumps(block.props or {}))
		return any(word.search(source) for source in sources)

	def check_script(self, block: Block):
		script = block.script()
		js, css = script.get("js") or "", script.get("css") or ""
		if re.search(r"\bfb-[0-9a-f]{8}", js + css):
			self.add("error", block, "fb- classes change on every render; select your own classes")
		if re.search(r"\.innerHTML\s*=", js):
			self.add("warn", block, "setting innerHTML throws in the editor canvas; use textContent")
