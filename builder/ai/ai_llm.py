import logging
import time

import frappe
import litellm

litellm.drop_params = True

logger = frappe.logger("builder.ai_llm")
logger.setLevel(logging.INFO)

TASK_PARAMS = {
	"simple": {"max_tokens": 1000, "temperature": 0.5},
	"complex": {"max_tokens": 40000, "temperature": 0.7},
	"clarify": {"max_tokens": 700, "temperature": 0.1},  # Strict JSON output for Q&A phase
	"agent": {
		"max_tokens": 16000,
		"temperature": 0.3,
	},  # Tool-calling: higher limit, lower temperature for precision
}

# Fallback model chain: if the primary model fails, try the next in order.
# Maps model name patterns to their fallback.
FALLBACK_CHAIN: list[tuple[str, str]] = [
	# Sonnet 4.6 → Gemini 3.1 Pro → Gemini 3 Flash
	("claude-sonnet-4", "openrouter/google/gemini-3.1-pro-preview"),
	("gemini-3.1-pro", "openrouter/google/gemini-3-flash-preview"),
	("gemini-3-flash", "openrouter/google/gemini-3-flash-preview"),
	# Haiku 4.6 → Gemini 3 Flash
	("claude-haiku-4", "openrouter/google/gemini-3-flash-preview"),
]


def _get_fallback(model: str) -> str | None:
	for pattern, fallback in FALLBACK_CHAIN:
		if pattern in model:
			if fallback not in model:
				return fallback
	return None


def call_llm(model: str, messages: list, params: dict, *, stream: bool, api_key: str | None = None):
	if model.startswith("gemini-"):
		model = f"gemini/{model}"

	if "claude-" in model:
		for m in messages:
			if m["role"] == "system" and isinstance(m.get("content"), str):
				m["content"] = [{"type": "text", "text": m["content"]}]

	logger.info(
		f"LLM request | model={model} stream={stream} params={params}\n"
		+ "\n".join(f"[{m['role']}] {m['content']!s}" for m in messages)
	)

	last_err: Exception | None = None
	attempt_models = [model]
	fallback = _get_fallback(model)
	if fallback:
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
