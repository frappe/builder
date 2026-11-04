"""What the eval reads off a finished turn: the run, the reply, a card, and the
built page's design fingerprint. No judge model, so two runs compare exactly."""

import colorsys
import json
import re
from itertools import pairwise

DASHES = "[\u2014\u2013]"
POSITIONED = frozenset({"relative", "absolute", "fixed", "sticky"})
TEXT_TAGS = frozenset({"p", "h1", "h2", "h3", "h4", "h5", "h6", "span", "a", "button", "label"})
BOX_TAGS = frozenset({"div", "section", "p", "ul", "ol", "figure", "article", "header", "footer"})
# block fields that land in styles when a model writes them inside the CSS: dead on the page
NOT_CSS = frozenset({"text", "innerHTML", "html", "src", "href", "alt", "class", "classes", "el", "tag"})
CSS_KEY = re.compile(r"^(--[\w-]+|-?[A-Za-z][A-Za-z0-9-]*)$")


class PageMeasure:
	"""The design-gap fingerprint of a built page, read off its block tree: the
	numbers that separated Bob's pages from premium templates (photos, micro-labels,
	type ladder, copy volume) plus the mechanical AI tells."""

	STOCK = re.compile(
		r"\b(elevate|unlock|seamless|effortless|empower|curated|vibrant|nestled|look no further|"
		r"more than just|crafted with care|your journey starts here)\b",
		re.I,
	)

	# the faces models reach for when they stop looking (Impeccable's reflex list)
	REFLEX_FACES = frozenset(
		{
			"fraunces",
			"playfair display",
			"cormorant",
			"cormorant garamond",
			"lora",
			"crimson",
			"crimson pro",
			"newsreader",
			"syne",
			"space grotesk",
			"space mono",
			"ibm plex sans",
			"ibm plex serif",
			"ibm plex mono",
			"dm sans",
			"dm serif display",
			"dm serif text",
			"outfit",
			"plus jakarta sans",
			"instrument sans",
		}
	)

	def __init__(self, root: dict, tokens: dict | None = None):
		self.root = root
		self.blocks = list(walk(root))
		self.tokens = tokens or {}

	def measures(self) -> dict:
		text = " ".join(block_text(b) for b in self.blocks)
		return {
			"sections": len(self.root.get("children") or []),
			"photos": len({src for b in self.blocks if (src := photo_src(b))}),
			"words": len(text.split()),
			"font_sizes": len({s for b in self.blocks if (s := styles(b).get("fontSize"))}),
			"micro_labels": sum(is_micro_label(b) for b in self.blocks),
			"eyebrow_headings": self.eyebrow_headings(),
			"gradient_text": sum(is_gradient_text(b) for b in self.blocks),
			"dashes": len(re.findall(DASHES, text)),
			"stock_phrases": len(self.STOCK.findall(text)),
			"no_mobile_fallback": sum(lacks_mobile_fallback(b) for b in self.blocks),
			"reflex_faces": sum(face.lower() in self.REFLEX_FACES for face in self.fonts()),
			"cream_ground": int(is_cream(self.ground())),
			"pinned_absolute": self.pinned_absolute(),
			"escaped_text": sum(escapes_text(b) for b in self.blocks),
			"dead_styles": sum(dead_styles(b) for b in self.blocks),
			"overflow_width": sum(overflows_width(b) for b in self.blocks),
		}

	def pinned_absolute(self) -> int:
		"""Absolute blocks under an unpositioned parent: they pin to the page, not their section."""
		return sum(
			styles(child).get("position") == "absolute" and styles(block).get("position") not in POSITIONED
			for block in self.blocks
			for child in block.get("children") or []
		)

	def look(self) -> dict:
		return {"fonts": sorted(self.fonts()), "ground": self.ground()}

	def fonts(self) -> set[str]:
		return {self.resolve(font) for b in self.blocks if (font := styles(b).get("fontFamily"))}

	def ground(self) -> str:
		return self.resolve(styles(self.root).get("backgroundColor"))

	def resolve(self, value) -> str:
		"""A token handle, var(--<id>), as the value it stands for."""
		handle = re.fullmatch(r"var\(--([\w-]+)\)", str(value or "").strip())
		return str(self.tokens.get(handle.group(1), value) if handle else value or "")

	def eyebrow_headings(self) -> int:
		count = 0
		for block in self.blocks:
			children = block.get("children") or []
			for first, second in pairwise(children):
				count += is_micro_label(first) and second.get("element") in ("h1", "h2", "h3")
		return count


def escapes_text(block: dict) -> bool:
	"""A text element holding a box child (a div inside a p): the browser closes the p
	early and the child renders without the p's styles."""
	return block.get("element") in TEXT_TAGS and any(
		child.get("element") in BOX_TAGS for child in block.get("children") or []
	)


def overflows_width(block: dict) -> bool:
	"""width:100% plus side padding under content-box sizing: wider than its parent."""
	base = styles(block)
	if str(base.get("width")) not in ("100%", "100vw") or base.get("boxSizing") == "border-box":
		return False
	padding = str(base.get("padding") or "0").split()
	sides = (padding[1::2] if len(padding) > 1 else padding) + [
		str(base.get(k) or "0") for k in ("paddingLeft", "paddingRight")
	]
	return any(side not in ("0", "0px") for side in sides)


def dead_styles(block: dict) -> int:
	keys = [
		k.rpartition(":")[2]
		for key in ("baseStyles", "tabletStyles", "mobileStyles")
		for k in block.get(key) or {}
	]
	return sum(key in NOT_CSS or not CSS_KEY.match(key) for key in keys)


def changed_blocks(before: dict, after: dict) -> int:
	"""Blocks added, removed or altered between two trees: 0 means the edits never landed."""
	fields = ("element", "innerHTML", "baseStyles", "mobileStyles", "tabletStyles", "attributes", "classes")
	sign = {
		b.get("blockId"): json.dumps([b.get(f) for f in fields], sort_keys=True, default=str)
		for b in walk(before)
	}
	sign_after = {
		b.get("blockId"): json.dumps([b.get(f) for f in fields], sort_keys=True, default=str)
		for b in walk(after)
	}
	return sum(sign.get(k) != sign_after.get(k) for k in sign.keys() | sign_after.keys())


def run_measures(runner, seconds: float = 0.0) -> dict:
	usage = runner.usage or {}
	per_call = usage.get("per_call") or []
	return {
		"rounds": len(runner.trace),
		"seconds": round(seconds),
		"prompt_tokens": usage.get("prompt_tokens"),
		"completion_tokens": usage.get("completion_tokens"),
		# the generation step is the turn's longest single output
		"longest_output": max((call.get("completion") or 0 for call in per_call), default=0),
		"calls": usage.get("calls"),
		"stop_reason": runner.stop_reason,
		"tool_failures": len(runner.tool_failures or []),
	}


def reply_measures(text: str) -> dict:
	return {
		"text": text[:1500],
		"words": len(text.split()),
		"dashes": len(re.findall(DASHES, text)),
		"hype": len(re.findall(r"\b(stunning|beautiful|perfect|elevate|seamless)\b", text, re.I)),
		"exclamations": text.count("!"),
		"emoji": len(re.findall("[\U0001f300-\U0001faff☀-➿]", text)),
	}


def authored_text(reply: dict) -> str:
	"""What the model wrote: a card's own words, not its rendered text, whose joins
	(an em dash between option label and description) the renderer adds."""
	if reply.get("message_type") != "clarification":
		return reply.get("content") or ""
	card = json.loads(reply.get("metadata_json") or "{}")
	return " ".join(strings(card.get("text"))) + " " + " ".join(strings(card.get("ui")))


def strings(value):
	if isinstance(value, str):
		yield value
	elif isinstance(value, dict | list):
		for item in value.values() if isinstance(value, dict) else value:
			yield from strings(item)


def card_measures(reply: dict) -> dict:
	ui = json.loads(reply.get("metadata_json") or "{}").get("ui") or []
	asks = [el for el in ui if el.get("kind") in ("input", "choices", "color_input", "upload")]
	return {
		"asks": len(asks),
		"kinds": [el.get("kind") for el in asks],
		"options": [o.get("label") for el in asks for o in el.get("options") or []],
	}


def summary_line(result: dict) -> str:
	if "error" in result:
		return f"{result['scenario']}: ERROR {result['error']}"
	run, page = result["run"], result.get("page") or {}
	verdict = "PASS" if result["ok"] else f"FAIL missing={result['missing']} forbidden={result['forbidden']}"
	line = f"{result['scenario']}: {verdict} | tools {','.join(result['tools']) or '-'} | rounds {run['rounds']} | {run.get('seconds')}s | prompt {run['prompt_tokens']}"
	if result.get("changed_blocks") is not None:
		line += f" | changed {result['changed_blocks']}"
	if page:
		line += " | " + " ".join(f"{k}={v}" for k, v in page.items())
	return line + f" | reply dashes={result['reply']['dashes']} hype={result['reply']['hype']}"


def is_cream(colour: str) -> bool:
	"""A warm, pale, muted ground: the cream of the most common generated look."""
	match = re.fullmatch(r"#([0-9a-fA-F]{6})", colour.strip())
	if not match:
		return False
	r, g, b = (int(match.group(1)[i : i + 2], 16) / 255 for i in (0, 2, 4))
	hue, lightness, saturation = colorsys.rgb_to_hls(r, g, b)
	return 20 <= hue * 360 <= 60 and lightness >= 0.85 and 0.15 <= saturation <= 0.8


def walk(block: dict):
	yield block
	for child in block.get("children") or []:
		yield from walk(child)


def styles(block: dict) -> dict:
	return block.get("baseStyles") or {}


def block_text(block: dict) -> str:
	# YAML reads a bare `2019` as a number
	return re.sub(r"<[^>]+>", " ", str(block.get("innerHTML") or ""))


def photo_src(block: dict) -> str | None:
	src = (block.get("attributes") or {}).get("src") or ""
	return src if block.get("element") == "img" and src and not src.endswith(".svg") else None


def is_micro_label(block: dict) -> bool:
	style = styles(block)
	if style.get("display") == "none":
		return False
	if style.get("textTransform") != "uppercase" or not block_text(block).strip():
		return False
	size = re.match(r"([\d.]+)px", str(style.get("fontSize") or ""))
	return bool(style.get("letterSpacing")) or (size is not None and float(size.group(1)) <= 14)


def is_gradient_text(block: dict) -> bool:
	style = styles(block)
	clip = style.get("backgroundClip") or style.get("WebkitBackgroundClip")
	return clip == "text" and "gradient" in str(style.get("backgroundImage") or "")


def lacks_mobile_fallback(block: dict) -> bool:
	style, mobile = styles(block), block.get("mobileStyles") or {}
	risky = {
		"position": style.get("position") in ("absolute", "sticky"),
		"fontSize": str(style.get("fontSize") or "").endswith("vw"),
		"gridTemplateAreas": bool(style.get("gridTemplateAreas")),
	}
	return any(flag and prop not in mobile for prop, flag in risky.items())


def write_json(path: str, data):
	with open(path, "w") as f:  # nosemgrep
		json.dump(data, f, indent=1, ensure_ascii=False, default=str)


def read_json(path: str):
	with open(path) as f:  # nosemgrep
		return json.load(f)
