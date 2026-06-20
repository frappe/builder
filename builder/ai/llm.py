"""Consolidated LLM adapter for Builder AI.

This is the ONLY place that knows about provider-specific quirks. The agent
loop and tools talk to LLMs exclusively through the functions defined here.
"""

import logging

import frappe
import litellm

litellm.drop_params = True

logger = frappe.logger("builder.ai.llm")
logger.setLevel(logging.INFO)

# Token/temperature budgets per task tier.
TASK_PARAMS = {
	"simple": {"max_tokens": 1000, "temperature": 0.5},
	"complex": {"max_tokens": 40000, "temperature": 0.7},
	"clarify": {"max_tokens": 700, "temperature": 0.1},
	"agent": {"max_tokens": 16000, "temperature": 0.3},
}

# If the primary model fails, try the next in order. Matched by substring.
FALLBACK_CHAIN: list[tuple[str, str]] = [
	("claude-sonnet-4", "openrouter/google/gemini-3.1-pro-preview"),
	("gemini-3.1-pro", "openrouter/google/gemini-3.5-flash"),
	("claude-haiku-4", "openrouter/google/gemini-3.5-flash"),
]


def fallbacks_for(model: str) -> list[str]:
	for pattern, fallback in FALLBACK_CHAIN:
		if pattern in model and fallback not in model:
			return [fallback]
	return []


def patch_messages_for_provider(model: str, messages: list[dict]) -> None:
	"""Anthropic via OpenRouter needs the system prompt as a content-block list
	with cache_control set ON THE BLOCK (not the message) for the ephemeral cache
	to be honoured. Move any message-level marker into the block. Mutates in place."""
	if "claude-" in model:
		for m in messages:
			if m["role"] == "system" and isinstance(m.get("content"), str):
				block = {"type": "text", "text": m["content"]}
				# Anthropic reads cache_control from inside the content block; a
				# message-level marker is silently ignored (full input price every turn).
				if cache_control := m.pop("cache_control", None):
					block["cache_control"] = cache_control
				m["content"] = [block]


def complete(model: str, messages: list, params: dict, *, stream: bool, api_key: str | None = None):
	"""Plain completion. Returns the response iterator when streaming, else the
	text content. litellm handles fallback + retry."""
	patch_messages_for_provider(model, messages)
	logger.info(
		f"LLM | model={model} stream={stream} fallbacks={fallbacks_for(model)} params={params}\n"
		+ "\n".join(f"[{m['role']}] {m['content']!s}" for m in messages)
	)
	resp = litellm.completion(
		model=model,
		messages=messages,
		stream=stream,
		api_key=api_key,
		# Fallbacks are disabled during streaming: litellm's mid-stream fallback
		# attempts __next__ on async generators returned by OpenRouter, causing
		# MidStreamFallbackError. Fallbacks only work safely for non-streaming calls.
		fallbacks=[] if stream else fallbacks_for(model),
		num_retries=1,
		# Emit a final usage chunk while streaming so the loop can tally tokens per
		# turn (dropped automatically for providers that don't support it).
		**({"stream_options": {"include_usage": True}} if stream else {}),
		**params,
	)
	if not stream:
		content = resp.choices[0].message.content or ""
		logger.info(f"LLM response | length={len(content)}\n{content}")
		return content
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
	"""Tool-calling completion. Returns the raw response (iterator when
	streaming). litellm handles fallback + retry."""
	patch_messages_for_provider(model, messages)
	logger.info(
		f"LLM tools | model={model} stream={stream} tools={[t['function']['name'] for t in tools]}\n"
		+ "\n".join(f"[{m['role']}] {m['content']}" for m in messages)
	)
	return litellm.completion(
		model=model,
		messages=messages,
		tools=tools,
		stream=stream,
		api_key=api_key,
		# Fallbacks disabled during streaming — see comment in complete().
		fallbacks=[] if stream else fallbacks_for(model),
		num_retries=1,
		# Final usage chunk while streaming — see complete().
		**({"stream_options": {"include_usage": True}} if stream else {}),
		**params,
	)
