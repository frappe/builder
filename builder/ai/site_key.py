"""The AI key that site config gives a site, and what calls with it cost.

Frappe Cloud writes `ai_keys` into a site's config (frappe.page writes it into the bench's common
config, for every site), and the Frappe provider (builder/ai/presets.py) calls models with it: through
the host's OpenAI-compatible gateway, or Anthropic's own API (SiteAIKey says which). The key belongs to
whoever hosts the site, not to the site: it is sent to that one API and nowhere else, it and a gateway's
address are kept out of every text a user can read, and a host app can hold what a site spends with it
to an allowance by implementing the hook `builder_ai_site_key_allowance`.

The hook names a callable that returns the allowance for the current site, or None when that site is
not metered. An allowance has:
- `reserve(tokens: int)`: hold `tokens` against what is left, atomically, and return a reservation; or
  raise UsageLimitError, whose message the user reads, when nothing is left.
- `check()`: raise that same UsageLimitError when nothing is left, holding nothing. A turn is checked
  before it is queued, since one that can only fail would still hold a worker.
- `status() -> dict`: what is used and left, for the AI panel.
A reservation has `settle(usage: Usage)`, called once when the call's usage is known.
"""

import hmac
import json
import math
from dataclasses import dataclass, field
from urllib.parse import urlsplit

import frappe

ALLOWANCE_HOOK = "builder_ai_site_key_allowance"
ANTHROPIC = "anthropic"
GATEWAY = "gateway"
# the only address an Anthropic site key is sent to, whatever else the entry or a row says
ANTHROPIC_API = "https://api.anthropic.com"
ANTHROPIC_VERSION = "2023-06-01"
# a gateway's OpenAI-compatible API, under the host site config names
GATEWAY_BASE_PATH = "/openai/v1"
REDACTED = "[the site's AI key]"
REDACTED_GATEWAY = "[the site's AI gateway]"
# a rough count, on the high side: a held estimate that is too low lets parallel calls overspend
CHARS_PER_TOKEN = 3
IMAGE_TOKENS = 1500
# what a call may write when it sets no max_tokens
DEFAULT_COMPLETION_TOKENS = 4096


class UsageLimitError(frappe.ValidationError):
	"""The host's allowance refused a call paid with the site key. Its message is written for the user."""

	http_status_code = 429


@dataclass(frozen=True)
class Usage:
	"""What a call used. `prompt_tokens` counts every input token, those read from and written to the
	prompt cache included; `cache_write_tokens` is how many were written, `cache_write_1h_tokens` how many
	of those for an hour rather than five minutes. `measured` is False when the model reported nothing
	and this is an estimate."""

	prompt_tokens: int
	completion_tokens: int
	cached_tokens: int = 0
	measured: bool = True
	cache_write_tokens: int = 0
	cache_write_1h_tokens: int = 0


@dataclass(frozen=True)
class SiteAIKey:
	"""The first `ai_keys` entry in site config: the key, and the one API it may be sent to.

	- {"provider": "anthropic", "api_key": ...}: Anthropic's own API, called natively. The key goes to
	  ANTHROPIC_API and nowhere else; an address in the entry is ignored.
	- {"gateway_url": ..., "api_key": ...}, Frappe Cloud's shape ("provider" absent or "gateway"): an
	  OpenAI-compatible gateway at <gateway_url>/openai/v1, which may report the key's balance.
	"""

	provider: str
	api_key: str = field(repr=False)  # kept out of any repr of the entry
	gateway_url: str | None = None

	@classmethod
	def from_entry(cls, entry) -> "SiteAIKey | None":
		"""The key an entry describes, or None (logged) when it is incomplete or names no API Builder knows."""
		entry = entry if isinstance(entry, dict) else {}
		provider = (entry.get("provider") or GATEWAY).strip().lower()
		api_key = (entry.get("api_key") or "").strip()
		if provider == ANTHROPIC and api_key:
			return cls(ANTHROPIC, api_key)
		if provider == GATEWAY and api_key and entry.get("gateway_url"):
			return cls(GATEWAY, api_key, entry["gateway_url"])
		frappe.logger("builder.ai.site_key").error(
			'site config ai_keys[0] needs {"provider": "anthropic", "api_key"} or {"gateway_url", "api_key"}'
		)
		return None

	@property
	def is_anthropic(self) -> bool:
		return self.provider == ANTHROPIC

	@property
	def litellm_provider(self) -> str:
		"""How litellm calls it: Anthropic's own route, or the OpenAI API a gateway speaks."""
		return "anthropic" if self.is_anthropic else "openai"

	@property
	def api_base(self) -> str:
		"""Where calls go. litellm adds /v1/messages to Anthropic's."""
		if self.is_anthropic:
			return ANTHROPIC_API
		parts = urlsplit(self.gateway_url)
		return f"{parts.scheme}://{parts.netloc}{GATEWAY_BASE_PATH}"

	def listing_request(self) -> tuple[str, dict]:
		"""The URL and headers that list the models this key may call."""
		if self.is_anthropic:
			headers = {"x-api-key": self.api_key, "anthropic-version": ANTHROPIC_VERSION}
			return f"{ANTHROPIC_API}/v1/models?limit=1000", headers
		return f"{self.api_base}/models", {"Authorization": f"Bearer {self.api_key}"}

	@property
	def credits_url(self) -> str | None:
		"""Frappe's gateway reports the key's balance at its host's /v1/key/balance; Anthropic reports none."""
		if self.is_anthropic:
			return None
		parts = urlsplit(self.gateway_url)
		return f"{parts.scheme}://{parts.netloc}/v1/key/balance"

	def hidden(self) -> list[tuple[str, str]]:
		"""What no user may read, each with what stands in for it, longest first: the key, and a gateway's
		address, which is the host's (errors name its host without the scheme). Anthropic's is public."""
		found = [(self.api_key, REDACTED)]
		if not self.is_anthropic:
			parts = urlsplit(self.gateway_url)
			hosts = {a for a in (parts.netloc, parts.hostname) if a and "." in a}
			addresses = {f"{parts.scheme}://{parts.netloc}", *hosts}
			found += [(a, REDACTED_GATEWAY) for a in addresses]
		return sorted(found, key=lambda pair: len(pair[0]), reverse=True)


def site_key() -> str | None:
	"""The key itself."""
	entry = site_entry()
	return entry.api_key if entry else None


def site_entry() -> SiteAIKey | None:
	"""The site config key. Site config cached by the request can miss a key that was just added."""
	from builder.ai.presets import get_site_ai_key

	return get_site_ai_key() or get_site_ai_key(fresh=True)


def is_site_key(api_key: str | None) -> bool:
	"""Whether a call made with `api_key` is paid with the site config key, whichever row or model led to it."""
	if not api_key:
		return False
	key = site_key()
	return bool(key) and hmac.compare_digest(api_key.encode(), key.encode())


def redact(text: str) -> str:
	"""`text` without the site key or its gateway's address, for anything a user or a log reader may see."""
	if not isinstance(text, str):
		return text
	for secret, stand_in in hidden():
		text = text.replace(secret, stand_in)
	return text


def scrub_exception(exc: BaseException) -> BaseException:
	"""Take the site key and its gateway's address out of an exception and the ones chained to it. A
	gateway can echo the request's Authorization header in an error, and an exception's text reaches the
	chat, the error log and tracebacks."""
	if not hidden():
		return exc
	seen = set()
	pending = [exc]
	while pending:
		current = pending.pop()
		if current is None or id(current) in seen:
			continue
		seen.add(id(current))
		current.args = tuple(redact(a) for a in current.args)
		if isinstance(getattr(current, "message", None), str):
			try:
				current.message = redact(current.message)
			except AttributeError:
				pass
		# requests wraps urllib3's error, which names the host, in its args rather than its cause
		pending += [a for a in current.args if isinstance(a, BaseException)]
		pending += [current.__cause__, current.__context__]
	return exc


def hidden() -> list[tuple[str, str]]:
	"""What site config holds that no user may read (SiteAIKey.hidden), or nothing without a key."""
	entry = site_entry()
	return entry.hidden() if entry else []


def allowance():
	"""The host's allowance for this site's key, or None when nothing meters it."""
	meter = host_hook(ALLOWANCE_HOOK)
	return meter() if meter else None


def host_hook(name: str):
	"""The callable the last installed app names for hook `name`, or None. Read from each app's hooks.py
	as this process imported it, not from the bench's shared hooks cache: a process started before a host
	app added the hook (a long-running scheduler, say) writes hooks without it back into that cache when a
	site's cache is cleared, which for the allowance would leave the site key unmetered."""
	found = None
	for app in frappe.get_installed_apps():
		if hooks := frappe.get_hooks(name, app_name=app):
			found = hooks[-1]
	return frappe.get_attr(found) if found else None


def allowance_status() -> dict | None:
	meter = allowance()
	return meter.status() if meter else None


def ensure_allowance_left(api_key: str | None) -> None:
	"""Raise UsageLimitError, holding nothing, when a call with `api_key` is paid with the site key and the
	host's allowance has nothing left."""
	if is_site_key(api_key) and (meter := allowance()):
		meter.check()


class Charge:
	"""One call paid with the site key, held against the allowance from before the request until its
	usage is known. The hold is the most the call can cost (its prompt and every token it may write),
	taken atomically, so calls started side by side cannot overspend between them. Settling swaps the
	hold for what the model reports, or for an estimate from what streamed when it reports nothing."""

	@classmethod
	def open(cls, api_key: str | None, messages: list, params: dict, tools: list | None = None):
		"""A charge for this call, or None when it isn't paid with the site key or nothing meters it.
		Raises UsageLimitError when the allowance is spent."""
		if not is_site_key(api_key):
			return None
		meter = allowance()
		if not meter:
			return None
		prompt = estimate_tokens(messages) + estimate_tokens(tools or [])
		hold = prompt + int(params.get("max_tokens") or DEFAULT_COMPLETION_TOKENS)
		return cls(meter.reserve(hold), prompt)

	def __init__(self, reservation, prompt_estimate: int):
		self.reservation = reservation
		self.prompt_estimate = prompt_estimate
		self.answer_chars = 0
		self.answered = False
		self.reported = None
		self.settled = False

	def observe(self, chunk) -> None:
		"""Note a streamed chunk: its usage, when it is the final one, and the text it carried."""
		self.answered = True
		if usage := getattr(chunk, "usage", None):
			self.reported = usage
		for choice in getattr(chunk, "choices", None) or []:
			self.answer_chars += text_length(getattr(choice, "delta", None))

	def receive(self, response) -> None:
		"""Note a response that came back whole: its usage and the text it carried."""
		self.answered = True
		self.reported = getattr(response, "usage", None)
		for choice in getattr(response, "choices", None) or []:
			self.answer_chars += text_length(getattr(choice, "message", None))

	def settle(self, usage=None) -> None:
		"""Charge what the call used: `usage` as the model reported it, else what was observed. A call
		that failed before anything came back costs no tokens."""
		if self.settled:
			return
		self.settled = True
		self.reservation.settle(self.used(usage or self.reported))

	def used(self, reported) -> Usage:
		# a gateway that reports nothing can still get an empty usage object from litellm
		if reported and (getattr(reported, "prompt_tokens", 0) or getattr(reported, "completion_tokens", 0)):
			written, written_1h = cache_write_tokens(reported)
			return Usage(
				prompt_tokens=getattr(reported, "prompt_tokens", 0) or 0,
				completion_tokens=getattr(reported, "completion_tokens", 0) or 0,
				cached_tokens=cached_prompt_tokens(reported),
				cache_write_tokens=written,
				cache_write_1h_tokens=written_1h,
			)
		if not self.answered:
			return Usage(0, 0)
		return Usage(self.prompt_estimate, math.ceil(self.answer_chars / CHARS_PER_TOKEN), measured=False)

	def stream(self, stream) -> "MeteredStream":
		return MeteredStream(stream, self)


class MeteredStream:
	"""A streamed response that settles its charge once it ends, fails or is closed. Closing it closes
	the provider's stream too, which is what stops a provider billing for a cancelled turn."""

	def __init__(self, stream, charge: Charge):
		self.stream = stream
		self.chunks = iter(stream)
		self.charge = charge

	def __iter__(self):
		return self

	def __next__(self):
		try:
			chunk = next(self.chunks)
		except StopIteration:
			self.charge.settle()
			raise
		except Exception as exc:
			self.charge.settle()
			raise scrub_exception(exc)
		self.charge.observe(chunk)
		return chunk

	def close(self) -> None:
		try:
			if close := getattr(self.stream, "close", None):
				close()
		finally:
			self.charge.settle()


def text_length(part) -> int:
	"""Characters of text, reasoning and tool arguments in a message or a streamed delta."""
	texts = [getattr(part, "content", None), getattr(part, "reasoning_content", None)]
	calls = getattr(part, "tool_calls", None) or []
	texts += [getattr(getattr(c, "function", None), "arguments", None) for c in calls]
	return sum(len(t) for t in texts if isinstance(t, str))


def cached_prompt_tokens(usage) -> int:
	details = getattr(usage, "prompt_tokens_details", None)
	if cached := part(details, "cached_tokens"):
		return cached
	return getattr(usage, "cache_read_input_tokens", 0) or 0


def cache_write_tokens(usage) -> tuple[int, int]:
	"""(prompt tokens written to the cache, how many of them for an hour), as Anthropic reports them
	through litellm. A gateway that reports no writes writes nothing."""
	details = getattr(usage, "prompt_tokens_details", None)
	written = getattr(usage, "cache_creation_input_tokens", 0) or part(details, "cache_creation_tokens")
	by_ttl = part(details, "cache_creation_token_details")
	return written, min(part(by_ttl, "ephemeral_1h_input_tokens"), written)


def part(value, name: str):
	"""A field of a usage detail, which litellm hands back as an object or a dict; 0 when it is missing."""
	found = value.get(name) if isinstance(value, dict) else getattr(value, name, None)
	return found or 0


def estimate_tokens(value) -> int:
	"""Tokens in a request's messages or tools, counted from their text; an image counts IMAGE_TOKENS
	(its data URL would count as megabytes of text)."""
	images = 0

	def strip_images(node):
		nonlocal images
		if isinstance(node, dict):
			if node.get("type") in ("image_url", "input_image"):
				images += 1
				return None
			return {k: strip_images(v) for k, v in node.items()}
		if isinstance(node, list):
			return [strip_images(v) for v in node]
		return node

	text = json.dumps(strip_images(value), default=str)
	return math.ceil(len(text) / CHARS_PER_TOKEN) + images * IMAGE_TOKENS
