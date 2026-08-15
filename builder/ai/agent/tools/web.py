"""Online research — a primitive and a specialist.

`read_url` is the primitive: fetch one public page as readable text (SSRF-
guarded, redirect-checked, bounded). `research` is a SPECIALIST sub-agent
behind the same seam generate_page uses: a focused one-shot run on a web-
grounded model variant that returns distilled findings with sources. The main
loop stays the coordinator; specialists live behind tool calls, so there is no
second coordination protocol and no second writer on the page tree.
"""

import html
import re

import frappe
import requests

from builder.ai.agent.registry import Tool

MAX_URL_READS_PER_TURN = 5
MAX_RESEARCH_PER_TURN = 2
MAX_REDIRECTS = 3
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
	text = html_to_text(raw) if "json" not in content_type else raw
	if len(text) > TEXT_LIMIT:
		text = text[:TEXT_LIMIT] + "… (truncated)"
	title = extract_title(raw)
	head = f"Read {final_url}" + (f" — '{title}'" if title else "")
	return f"{head}\n\n{text}" if text.strip() else f"{head}\n\n(no readable text on the page)"


def fetch_public(url: str):
	"""GET with the SSRF guard applied to EVERY hop — a public host that redirects
	to a private address is the classic bypass. Each hop then connects to the
	ADDRESS the guard validated: letting requests re-resolve the hostname is the
	other classic bypass (DNS rebinding — a public answer for the check, a private
	one for the connect)."""
	from urllib.parse import urljoin

	from builder.api import assert_not_private_url

	for _ in range(MAX_REDIRECTS + 1):
		ips = assert_not_private_url(url)
		response = pinned_get(url, ips[0])
		location = response.headers.get("location")
		if response.status_code in (301, 302, 303, 307, 308) and location:
			url = urljoin(url, location)
			continue
		return response, url
	raise Exception(f"too many redirects (>{MAX_REDIRECTS})")


class SniAdapter(requests.adapters.HTTPAdapter):
	"""TLS for a pinned connection: the socket dials the validated IP while the
	handshake (SNI) and certificate check use the real hostname."""

	def __init__(self, hostname: str):
		self.hostname = hostname
		super().__init__()

	def init_poolmanager(self, connections, maxsize, block=False, **pool_kwargs):
		pool_kwargs["server_hostname"] = self.hostname
		super().init_poolmanager(connections, maxsize, block, **pool_kwargs)


def pinned_url(url: str, ip: str) -> tuple[str, str]:
	"""The URL rewritten to dial the validated address, plus the Host header that
	keeps the request addressed to the original site."""
	from urllib.parse import urlparse

	parsed = urlparse(url)
	literal = f"[{ip}]" if ":" in ip else ip
	netloc = f"{literal}:{parsed.port}" if parsed.port else literal
	host_header = f"{parsed.hostname}:{parsed.port}" if parsed.port else parsed.hostname
	return parsed._replace(netloc=netloc).geturl(), host_header


def pinned_get(url: str, ip: str):
	from urllib.parse import urlparse

	target, host_header = pinned_url(url, ip)
	session = requests.Session()
	session.mount("https://", SniAdapter(urlparse(url).hostname))
	return session.get(
		target,
		timeout=FETCH_TIMEOUT,
		stream=True,
		allow_redirects=False,
		headers={"User-Agent": USER_AGENT, "Host": host_header},
	)


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
		"properties": {"url": {"type": "string", "description": "The full http(s) address."}},
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
