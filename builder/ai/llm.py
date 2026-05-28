"""Consolidated LLM adapter for Builder AI.

This is the ONLY place that knows about provider-specific quirks (model name
resolution, Claude system-prompt shaping, fallback chains). The agent loop and
tools talk to LLMs exclusively through the functions defined here.
"""

import logging
import time

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
	("gemini-3.1-pro", "openrouter/google/gemini-3-flash-preview"),
	("gemini-3-flash", "openrouter/google/gemini-3-flash-preview"),
	("claude-haiku-4", "openrouter/google/gemini-3-flash-preview"),
]


def resolve_model(model: str) -> str:
	"""Normalise a model name into the form litellm expects."""
	if model.startswith("gemini-"):
		return f"gemini/{model}"
	return model


def patch_messages_for_provider(model: str, messages: list[dict]) -> None:
	"""Mutate `messages` in place to satisfy provider-specific requirements.

	Anthropic models require the system prompt as a content-block list (so the
	ephemeral cache_control marker is honoured), not a bare string.
	"""
	if "claude-" in model:
		for m in messages:
			if m["role"] == "system" and isinstance(m.get("content"), str):
				m["content"] = [{"type": "text", "text": m["content"]}]


def _get_fallback(model: str) -> str | None:
	for pattern, fallback in FALLBACK_CHAIN:
		if pattern in model and fallback not in model:
			return fallback
	return None


def complete(model: str, messages: list, params: dict, *, stream: bool, api_key: str | None = None):
	"""Plain completion with provider patching and a one-step fallback chain.

	Returns the response object when streaming, or the text content when not.
	"""
	model = resolve_model(model)
	patch_messages_for_provider(model, messages)

	logger.info(
		f"LLM request | model={model} stream={stream} params={params}\n"
		+ "\n".join(f"[{m['role']}] {m['content']!s}" for m in messages)
	)

	last_err: Exception | None = None
	attempt_models = [model]
	if fallback := _get_fallback(model):
		attempt_models.append(fallback)

	for attempt, attempt_model in enumerate(attempt_models):
		try:
			if attempt > 0:
				time.sleep(2 ** (attempt - 1))  # 2s, 4s… before each fallback
				logger.warning(f"Falling back to {attempt_model} after error: {last_err}")
			resp = litellm.completion(
				model=attempt_model, messages=messages, stream=stream, api_key=api_key, **params
			)
			if not stream:
				content = resp.choices[0].message.content or ""
				logger.info(f"LLM response | model={attempt_model} length={len(content)}\n{content}")
				return content
			return resp
		except litellm.APIError as e:
			last_err = e
			logger.error(f"LiteLLM APIError on {attempt_model}: {e}")
			if attempt + 1 >= len(attempt_models):
				raise
		except Exception as e:
			logger.error(f"LiteLLM call failed: {e!s}", exc_info=True)
			raise


def complete_with_tools(
	model: str,
	messages: list,
	tools: list,
	params: dict,
	*,
	api_key: str | None = None,
	stream: bool = False,
):
	"""Tool-calling completion. Returns the raw response object (an iterable of
	chunks when stream=True, otherwise a single response)."""
	model = resolve_model(model)
	patch_messages_for_provider(model, messages)

	logger.info(
		f"LLM tool request | model={model} stream={stream} tools={[t['function']['name'] for t in tools]}\n"
		+ "\n".join(f"[{m['role']}] {m['content']}" for m in messages)
	)
	return litellm.completion(
		model=model, messages=messages, tools=tools, stream=stream, api_key=api_key, **params
	)
