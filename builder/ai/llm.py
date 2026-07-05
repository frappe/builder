"""Consolidated LLM adapter for Builder AI.

This is the ONLY place that knows about provider-specific quirks. The agent
loop and tools talk to LLMs exclusively through the functions defined here.
"""

import json
import logging

import frappe
import litellm

from builder.ai import cassette

litellm.drop_params = True

logger = frappe.logger("builder.ai.llm")
logger.setLevel(logging.INFO)


# Transient failures worth retrying a streaming round: rate limits, 5xx, and
# connection/stream drops (incl. mid-stream resets). Matched by class name across the
# exception's MRO so subclasses — and both litellm and raw httpx transport errors — are
# covered without version-pinning exact types. Permanent errors (auth, bad request,
# content policy, not found) are deliberately absent: retrying them only burns tokens.
TRANSIENT_ERROR_NAMES = frozenset(
	{
		"RateLimitError",
		"Timeout",
		"TimeoutError",
		"APITimeoutError",
		"APIConnectionError",
		"InternalServerError",
		"ServiceUnavailableError",
		"RemoteProtocolError",
		"ReadError",
		"ReadTimeout",
		"ConnectError",
		"ConnectionError",
		"ChunkedEncodingError",
		"ProtocolError",
	}
)


def is_retryable(exc: BaseException) -> bool:
	"""True if this exception looks like a transient network/provider hiccup worth
	retrying. Walks the class MRO and matches by name (see TRANSIENT_ERROR_NAMES)."""
	return any(cls.__name__ in TRANSIENT_ERROR_NAMES for cls in type(exc).__mro__)


def loads_tolerant(raw: str) -> tuple[object | None, bool]:
	"""Parse tool-call argument JSON, tolerating the malformed JSON weaker models emit
	(single-quote delimiters, unescaped quotes, trailing commas, truncated/missing
	brackets). Strict json.loads first; on failure fall back to json_repair if available.
	Returns (parsed_or_None, was_repaired)."""
	raw = (raw or "").strip()
	if not raw:
		return None, False
	try:
		return json.loads(raw), False
	except json.JSONDecodeError:
		pass
	try:
		from json_repair import repair_json

		obj = repair_json(raw, return_objects=True)
		if obj not in ("", None, [], {}):
			return obj, True
	except Exception:
		pass
	return None, False


# Token/temperature budgets per task tier.
TASK_PARAMS = {
	"simple": {"max_tokens": 1000, "temperature": 0.5},
	"complex": {"max_tokens": 40000, "temperature": 0.7},
	"clarify": {"max_tokens": 700, "temperature": 0.1},
	# 0.7 (not 0.3): the agent tier also composes the creative option cards
	# (layout directions, font pairings) — at 0.3 every session got the same
	# three flat options and the same famous fonts. Matches the "complex"
	# generation tier, which already proves 0.7 is safe for structured output.
	"agent": {"max_tokens": 16000, "temperature": 0.7},
}


def patch_messages_for_provider(model: str, messages: list[dict]) -> None:
	"""Anthropic via OpenRouter reads cache_control from INSIDE a content block, not
	from the message level (a message-level marker is silently ignored → full input
	price every turn). Relocate each marker set by the agent loop into the message's
	last content block for Claude models; strip markers entirely for other providers
	(their caching is implicit). Mutates in place."""
	claude = "claude-" in model
	for m in messages:
		marker = m.pop("cache_control", None)
		if not marker or not claude:
			continue
		content = m.get("content")
		if isinstance(content, str) or content is None:
			m["content"] = [{"type": "text", "text": content or "", "cache_control": marker}]
		elif isinstance(content, list) and content:
			content[-1] = {**content[-1], "cache_control": marker}


def provider_kwargs(model: str) -> dict:
	"""Pin Claude calls to the Anthropic route on OpenRouter: a fallback provider
	would silently drop the cache breakpoints and re-bill the whole prefix at full
	input price on every round."""
	if model.startswith("openrouter/") and "claude-" in model:
		return {"extra_body": {"provider": {"order": ["anthropic"], "allow_fallbacks": False}}}
	return {}


def complete(model: str, messages: list, params: dict, *, stream: bool, api_key: str | None = None):
	"""Plain completion. Returns the response iterator when streaming, else the
	text content. Transient failures are retried by litellm (and, for streaming
	rounds, by the agent loop's own retry layer — litellm can't fall back mid-stream)."""
	patch_messages_for_provider(model, messages)
	logger.info(
		f"LLM | model={model} stream={stream} params={params}\n"
		+ "\n".join(f"[{m['role']}] {m['content']!s}" for m in messages)
	)
	cas = cassette.config()
	if cas and cas["mode"] == "replay":
		return cassette.replay_call(cas, model, messages, stream)
	resp = litellm.completion(
		model=model,
		messages=messages,
		stream=stream,
		api_key=api_key,
		num_retries=1,
		# Read timeout (max stall between bytes, not total duration): a wedged
		# provider connection otherwise blocks the worker forever — the loop only
		# checks cancellation between chunks, so a silent stall is uncancellable.
		timeout=120,
		# Emit a final usage chunk while streaming so the loop can tally tokens per
		# turn (dropped automatically for providers that don't support it).
		**({"stream_options": {"include_usage": True}} if stream else {}),
		**provider_kwargs(model),
		**params,
	)
	if not stream:
		content = resp.choices[0].message.content or ""
		logger.info(f"LLM response | length={len(content)}\n{content}")
		if cas:
			cassette.append_record(
				cas["episode"],
				{
					"seq": cassette.next_seq(cas["episode"]),
					"kind": "text",
					"model": model,
					"hash": cassette.prompt_hash(model, messages),
					"content": content,
				},
			)
		return content
	if cas:
		return cassette.record_stream(
			cas["episode"],
			cassette.next_seq(cas["episode"]),
			model,
			cassette.prompt_hash(model, messages),
			resp,
		)
	return resp


def complete_with_tools(
	model: str,
	messages: list,
	tools: list,
	params: dict,
	*,
	api_key: str | None = None,
	stream: bool = False,
):
	"""Tool-calling completion. Returns the raw response (iterator when streaming)."""
	patch_messages_for_provider(model, messages)
	logger.info(
		f"LLM tools | model={model} stream={stream} tools={[t['function']['name'] for t in tools]}\n"
		+ "\n".join(f"[{m['role']}] {m['content']}" for m in messages)
	)
	cas = cassette.config()
	if cas and cas["mode"] == "replay":
		return cassette.replay_call(cas, model, messages, stream)
	resp = litellm.completion(
		model=model,
		messages=messages,
		tools=tools,
		stream=stream,
		api_key=api_key,
		num_retries=1,
		timeout=120,  # see complete() — a stalled connection must fail, not wedge the turn
		# Final usage chunk while streaming — see complete().
		**({"stream_options": {"include_usage": True}} if stream else {}),
		**provider_kwargs(model),
		**params,
	)
	if cas:
		seq = cassette.next_seq(cas["episode"])
		phash = cassette.prompt_hash(model, messages)
		if stream:
			return cassette.record_stream(cas["episode"], seq, model, phash, resp)
		cassette.append_record(
			cas["episode"],
			{
				"seq": seq,
				"kind": "response",
				"model": model,
				"hash": phash,
				"data": cassette.serialize_chunk(resp),
			},
		)
	return resp
