"""What the eval reads off a finished turn: the run, the reply, a card, and the
built page's design fingerprint. No judge model, so two runs compare exactly."""

import json
import re
from itertools import pairwise

DASHES = "[\u2014\u2013]"


class PageMeasure:
	"""The design-gap fingerprint of a built page, read off its block tree: the
	numbers that separated Bob's pages from premium templates (photos, micro-labels,
	type ladder, copy volume) plus the mechanical AI tells."""

	STOCK = re.compile(
		r"\b(elevate|unlock|seamless|effortless|empower|curated|vibrant|nestled|look no further|"
		r"more than just|crafted with care|your journey starts here)\b",
		re.I,
	)

	def __init__(self, root: dict):
		self.root = root
		self.blocks = list(walk(root))

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
		}

	def eyebrow_headings(self) -> int:
		count = 0
		for block in self.blocks:
			children = block.get("children") or []
			for first, second in pairwise(children):
				count += is_micro_label(first) and second.get("element") in ("h1", "h2", "h3")
		return count


def run_measures(runner) -> dict:
	usage = runner.usage or {}
	return {
		"rounds": len(runner.trace),
		"prompt_tokens": usage.get("prompt_tokens"),
		"completion_tokens": usage.get("completion_tokens"),
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
	line = f"{result['scenario']}: {verdict} | tools {','.join(result['tools']) or '-'} | rounds {run['rounds']} | prompt {run['prompt_tokens']}"
	if page:
		line += " | " + " ".join(f"{k}={v}" for k, v in page.items())
	return line + f" | reply dashes={result['reply']['dashes']} hype={result['reply']['hype']}"


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
	with open(path) as f:
		return json.load(f)
