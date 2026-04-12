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

	logger.info(
		f"LLM request | model={model} stream={stream} params={params}\n"
		+ "\n".join(
			f"[{m['role']}] {m['content'] if isinstance(m['content'], str) else m['content']}"
			for m in messages
		)
	)

	try:
		resp = litellm.completion(model=model, messages=messages, stream=stream, api_key=api_key, **params)
		if not stream:
			content = resp.choices[0].message.content or ""
			logger.info(f"LLM response | model={model} length={len(content)}\n{content}")
			return content
		return resp
	except Exception as e:
		logger.error(f"LiteLLM call failed: {str(e)}", exc_info=True)
		raise
