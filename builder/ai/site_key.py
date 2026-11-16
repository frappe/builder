"""The AI key that site config gives a site, and what calls with it cost.

Frappe Cloud writes `ai_keys` into a site's config (frappe.page writes it into the bench's common
config, for every site), and the Frappe provider (builder/ai/presets.py) calls the gateway with it.
The key belongs to whoever hosts the site, not to the site: it is sent to that gateway and nowhere
else, it is kept out of every text a user can read, and a host app can hold what a site spends with it
to an allowance by implementing the hook `builder_ai_site_key_allowance`.

The hook names a callable that returns the allowance for the current site, or None when that site is
not metered. An allowance has:
- `reserve(tokens: int)`: hold `tokens` against what is left, atomically, and return a reservation; or
  raise UsageLimitError, whose message the user reads, when nothing is left.
- `status() -> dict`: what is used and left, for the AI panel.
A reservation has `settle(usage: Usage)`, called once when the call's usage is known.
"""

import hmac
import json
import math
from dataclasses import dataclass

import frappe

ALLOWANCE_HOOK = "builder_ai_site_key_allowance"
REDACTED = "[the site's AI key]"
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
	"""What a call used. `measured` is False when the model reported nothing and this is an estimate."""

	prompt_tokens: int
	completion_tokens: int
	cached_tokens: int = 0
	measured: bool = True


def site_key() -> str | None:
	"""The key itself. Site config cached by the request can miss a key that was just added."""
	from builder.ai.presets import get_site_ai_key

	entry = get_site_ai_key() or get_site_ai_key(fresh=True)
	return entry["api_key"] if entry else None


def is_site_key(api_key: str | None) -> bool:
	"""Whether a call made with `api_key` is paid with the site config key, whichever row or model led to it."""
	if not api_key:
		return False
	key = site_key()
	return bool(key) and hmac.compare_digest(api_key.encode(), key.encode())


def redact(text: str) -> str:
	"""`text` without the site key, for anything a user or a log reader may see."""
	key = site_key()
	if not key or not isinstance(text, str) or key not in text:
		return text
	return text.replace(key, REDACTED)


def scrub_exception(exc: BaseException) -> BaseException:
	"""Take the site key out of an exception and the ones chained to it. A gateway can echo the
	request's Authorization header in an error, and an exception's text reaches the chat, the error
	log and tracebacks."""
	key = site_key()
	if not key:
		return exc
	seen = set()
	current = exc
	while current is not None and id(current) not in seen:
		seen.add(id(current))
		current.args = tuple(a.replace(key, REDACTED) if isinstance(a, str) else a for a in current.args)
		if isinstance(getattr(current, "message", None), str):
			try:
				current.message = current.message.replace(key, REDACTED)
			except AttributeError:
				pass
		current = current.__cause__ or current.__context__
	return exc


def allowance():
	"""The host's allowance for this site's key, or None when nothing meters it."""
	hooks = frappe.get_hooks(ALLOWANCE_HOOK)
	return frappe.get_attr(hooks[-1])() if hooks else None


def allowance_status() -> dict | None:
	meter = allowance()
	return meter.status() if meter else None


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
		self.streamed_chars = 0
		self.chunks = 0
		self.reported = None
		self.settled = False

	def observe(self, chunk) -> None:
		"""Note a streamed chunk: its usage, when it is the final one, and the text it carried."""
		self.chunks += 1
		if usage := getattr(chunk, "usage", None):
			self.reported = usage
		for choice in getattr(chunk, "choices", None) or []:
			delta = getattr(choice, "delta", None)
			self.streamed_chars += len(getattr(delta, "content", None) or "")
			self.streamed_chars += len(getattr(delta, "reasoning_content", None) or "")
			for call in getattr(delta, "tool_calls", None) or []:
				self.streamed_chars += len(getattr(getattr(call, "function", None), "arguments", None) or "")

	def settle(self, usage=None) -> None:
		"""Charge what the call used: `usage` as the model reported it, else what was observed. A call
		that failed before anything came back costs no tokens."""
		if self.settled:
			return
		self.settled = True
		self.reservation.settle(self.used(usage or self.reported))

	def used(self, reported) -> Usage:
		if reported:
			return Usage(
				prompt_tokens=getattr(reported, "prompt_tokens", 0) or 0,
				completion_tokens=getattr(reported, "completion_tokens", 0) or 0,
				cached_tokens=cached_prompt_tokens(reported),
			)
		if not self.chunks:
			return Usage(0, 0)
		return Usage(self.prompt_estimate, math.ceil(self.streamed_chars / CHARS_PER_TOKEN), measured=False)

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


def cached_prompt_tokens(usage) -> int:
	details = getattr(usage, "prompt_tokens_details", None)
	if cached := getattr(details, "cached_tokens", None):
		return cached
	return getattr(usage, "cache_read_input_tokens", 0) or 0


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
