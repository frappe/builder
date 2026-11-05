"""Online research — a primitive and a specialist.

`read_url` is the primitive: fetch one public page as readable text (SSRF-
guarded, redirect-checked, bounded). `research` is a SPECIALIST sub-agent
behind the same seam generate_page uses: a focused one-shot run on a web-
grounded model variant that returns distilled findings with sources. The main
loop stays the coordinator; specialists live behind tool calls, so there is no
second coordination protocol and no second writer on the page tree.
"""

import html
import json
import re
from html.parser import HTMLParser
from urllib.parse import urljoin

import frappe

from builder.ai.agent.registry import Tool
from builder.public_fetch import public_session

MAX_URL_READS_PER_TURN = 5
MAX_RESEARCH_PER_TURN = 2
MAX_BYTES = 1_000_000
TEXT_LIMIT = 10_000
FETCH_TIMEOUT = 12
USER_AGENT = "Mozilla/5.0 (compatible; FrappeBuilderAI/1.0)"

READABLE_TYPES = ("text/", "application/xhtml", "application/json", "application/xml")


def run_read_url(ctx, args: dict) -> str:
	url = (args.get("url") or "").strip().strip("<>")
	if not url:
		return "FAILED: pass `url` — an http(s) address of a public page."
	if ctx.web_read_count >= MAX_URL_READS_PER_TURN:
		return "URL-read limit reached for this turn — work with what you have."
	ctx.web_read_count += 1
	try:
		response, final_url = fetch_public(url)
	except Exception as e:
		return f"FAILED: {e}"
	content_type = (response.headers.get("content-type") or "").lower()
	if not content_type.startswith(READABLE_TYPES):
		return f"FAILED: '{content_type or 'unknown type'}' is not a readable page — text/HTML only."
	if response.status_code >= 400:
		return f"FAILED: {final_url} answered HTTP {response.status_code}."
	raw = read_bounded(response)
	fields = requested_fields(args)
	text = page_text(raw, content_type, fields)
	note_source(ctx, final_url, fields)
	title = extract_title(raw)
	head = f"Read {final_url}" + (f" — '{title}'" if title else "")
	if "html" in content_type:
		head += data_links_note(raw, final_url)
	return f"{head}\n\n{text}" if text.strip() else f"{head}\n\n(no readable text on the page)"


def fetch_public(url: str):
	"""GET through public_session, which refuses a private address on every redirect
	hop and on the address each connection actually dials."""
	response = public_session().get(
		url, timeout=FETCH_TIMEOUT, stream=True, headers={"User-Agent": USER_AGENT}
	)
	return response, response.url


def requested_fields(args: dict) -> list[str]:
	fields = args.get("fields") or []
	if isinstance(fields, str):
		fields = fields.split(",")
	return [str(f).strip() for f in fields if str(f).strip()]


def page_text(raw: str, content_type: str, fields: list[str]) -> str:
	is_json = "json" in content_type
	text = (pick_json_fields(raw, fields) if fields else raw) if is_json else html_to_text(raw)
	if len(text) <= TEXT_LIMIT:
		return text
	hint = "; pass `fields` to keep only the keys you need" if is_json and not fields else ""
	return f"{text[:TEXT_LIMIT]}… (truncated{hint})"


def note_source(ctx, url: str, fields: list[str]) -> None:
	"""Kept on the turn's message, so a later turn reads what answered instead of guessing."""
	source = {"url": url, "fields": fields} if fields else {"url": url}
	if source not in ctx.web_sources:
		ctx.web_sources.append(source)


def pick_json_fields(raw: str, fields: list[str]) -> str:
	try:
		picked = pick_fields(json.loads(raw), set(fields))
	except ValueError:
		return raw
	if picked is None:
		return f"(no {', '.join(fields)} key in this JSON; read it without fields to see its shape)"
	return json.dumps(picked, ensure_ascii=False, separators=(",", ":"))


def pick_fields(value, fields: set[str]):
	"""`value` keeping only the keys in `fields`, at any depth; None when none matched."""
	if isinstance(value, dict):
		kept = {k: v if k in fields else pick_fields(v, fields) for k, v in value.items()}
		return {k: v for k, v in kept.items() if k in fields or v is not None} or None
	if isinstance(value, list):
		kept = [v for v in (pick_fields(item, fields) for item in value) if v is not None]
		return kept or None
	return None


def data_links_note(markup: str, base_url: str) -> str:
	"""A list a script builds after load is invisible as text; the API or feed the page
	declares for it is the way in."""
	parser = DataLinks()
	parser.feed(markup)
	rows = [
		f"- {link['type']}"
		+ (f" '{link['title']}'" if link.get("title") else "")
		+ f": {urljoin(base_url, link['href'])}"
		for link in parser.links
	]
	return "\n\nData links the page declares:\n" + "\n".join(rows) if rows else ""


class DataLinks(HTMLParser):
	"""<link rel="alternate"> tags that carry a type: feeds and APIs, not language versions."""

	def __init__(self):
		super().__init__()
		self.links: list[dict] = []

	def handle_starttag(self, tag, attrs):
		link = dict(attrs)
		rel = (link.get("rel") or "").lower().split()
		if tag == "link" and "alternate" in rel and link.get("type") and link.get("href"):
			self.links.append(link)


def read_bounded(response) -> str:
	chunks, total = [], 0
	for chunk in response.iter_content(chunk_size=65536, decode_unicode=False):
		chunks.append(chunk)
		total += len(chunk)
		if total >= MAX_BYTES:
			break
	return b"".join(chunks).decode(response.encoding or "utf-8", errors="replace")


BLOCK_TAGS_RE = re.compile(r"<(script|style|noscript|svg|template)\b.*?</\1>", re.IGNORECASE | re.DOTALL)
BREAK_TAGS_RE = re.compile(r"</?(p|div|section|article|li|tr|br|h[1-6])\b[^>]*>", re.IGNORECASE)
TAG_RE = re.compile(r"<[^>]+>")
TITLE_RE = re.compile(r"<title[^>]*>(.*?)</title>", re.IGNORECASE | re.DOTALL)


def html_to_text(markup: str) -> str:
	text = BLOCK_TAGS_RE.sub(" ", markup)
	text = BREAK_TAGS_RE.sub("\n", text)
	text = TAG_RE.sub(" ", text)
	text = html.unescape(text)
	lines = [re.sub(r"[ \t]+", " ", line).strip() for line in text.splitlines()]
	return "\n".join(line for line in lines if line)


def extract_title(markup: str) -> str:
	match = TITLE_RE.search(markup)
	return html.unescape(match.group(1)).strip()[:200] if match else ""


RESEARCH_SYSTEM = (
	"You are the research specialist for a website-building agent. Answer the question "
	"from CURRENT web sources. Return a compact bullet list of verified findings, each "
	"with its source URL. Facts only — no design advice, no filler. If something cannot "
	"be verified, say 'not found' for it plainly instead of guessing; the agent will "
	"write around the gap. Keep it under 300 words."
)
RESEARCH_LIMIT = 6_000


def run_research(ctx, args: dict) -> str:
	question = (args.get("question") or "").strip()
	if not question:
		return "FAILED: pass `question` — what to find out."
	if ctx.research_count >= MAX_RESEARCH_PER_TURN:
		return "Research limit reached for this turn — work with the findings you have."
	from builder.ai import llm

	routed, _overrides, api_key = llm.route(ctx.loop_model or ctx.model, ctx.api_key)
	if not routed.startswith("openrouter/"):
		return (
			"FAILED: web-grounded research needs an OpenRouter-routed model — read specific "
			"pages with read_url instead."
		)
	ctx.research_count += 1
	messages = [
		{"role": "system", "content": RESEARCH_SYSTEM},
		{"role": "user", "content": question},
	]
	try:
		# ':online' is the provider's web-search variant of the SAME model.
		text = llm.complete(f"{routed}:online", messages, {}, stream=False, api_key=api_key)
	except Exception as e:
		return (
			f"FAILED: research call failed ({type(e).__name__}) — fall back to read_url or proceed without."
		)
	text = (text or "").strip()
	if len(text) > RESEARCH_LIMIT:
		text = text[:RESEARCH_LIMIT] + "… (truncated)"
	return text or "The researcher returned nothing — proceed without, or try read_url on a specific page."


read_url = Tool(
	name="read_url",
	side="server",
	handler=run_read_url,
	description=(
		"Fetch ONE public web page (http/https) and return its readable text. Use it when "
		"the user points at a specific external page — their current site, a business "
		"listing, a reference they want content taken from. External pages are SOURCE "
		"MATERIAL (copy, structure, tone), not something you can clone pixel-perfect or "
		"edit. Internal pages of THIS site are read with read_page, not this."
	),
	parameters={
		"type": "object",
		"properties": {
			"url": {"type": "string", "description": "The full http(s) address."},
			"fields": {
				"type": "array",
				"items": {"type": "string"},
				"description": (
					"JSON responses only: keep just these keys, at any depth (e.g. "
					'["name", "photo_url"]), so a long API list fits in one read.'
				),
			},
		},
		"required": ["url"],
	},
)

research = Tool(
	name="research",
	side="server",
	handler=run_research,
	description=(
		"Delegate an open question to the web research specialist and get back verified "
		"findings with source URLs. Use it for facts you must not invent: a real "
		"business's details (address, hours, offerings), a brand or person the user "
		"names, current prices/dates, what competitors' sites say. One focused question "
		"per call. For a specific page the user already pointed at, read_url is cheaper "
		"and more faithful."
	),
	parameters={
		"type": "object",
		"properties": {
			"question": {
				"type": "string",
				"description": "One specific question, with all context the researcher needs.",
			},
		},
		"required": ["question"],
	},
)

TOOLS = [read_url, research]
