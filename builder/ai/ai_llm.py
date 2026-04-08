import logging

import frappe
import litellm

litellm.drop_params = True

logger = frappe.logger("builder.ai_llm")
logger.setLevel(logging.INFO)

TASK_PARAMS = {
	"simple": {"max_tokens": 1000, "temperature": 0.5},
	"complex": {"max_tokens": 22000, "temperature": 0.7},
}


def call_llm(model: str, messages: list, params: dict, *, stream: bool, api_key: str | None = None):
	if model.startswith("gemini-"):
		model = f"gemini/{model}"

	if "claude-" in model:
		for m in messages:
			if m["role"] == "system" and isinstance(m.get("content"), str):
				m["content"] = [{"type": "text", "text": m["content"]}]

	try:
		resp = litellm.completion(model=model, messages=messages, stream=stream, api_key=api_key, **params)
		return resp if stream else (resp.choices[0].message.content or "")
	except Exception as e:
		logger.error(f"LiteLLM call failed: {str(e)}", exc_info=True)
		raise
