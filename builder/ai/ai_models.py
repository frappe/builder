import re
from typing import ClassVar


class ModelRegistry:
	AVAILABLE: ClassVar[list] = [
		{
			"provider": "openrouter",
			"models": [
				{
					"name": "openrouter/anthropic/claude-sonnet-4.6",
					"label": "Claude Sonnet 4.6",
					"max_tokens": 200000,
					"vision": True,
				},
				{
					"name": "openrouter/anthropic/claude-haiku-4-6",
					"label": "Claude Haiku 4.6",
					"max_tokens": 200000,
					"vision": True,
				},
				{
					"name": "openrouter/google/gemini-3.1-pro",
					"label": "Gemini 3.1 Pro",
					"max_tokens": 1048576,
					"vision": True,
				},
				{
					"name": "openrouter/google/gemini-3-flash-preview",
					"label": "Gemini 3 Flash",
					"max_tokens": 1048576,
					"vision": True,
				},
				{
					"name": "openrouter/openai/gpt-5.4-mini",
					"label": "GPT-5.4 Mini",
					"max_tokens": 1000000,
					"vision": True,
				},
				{
					"name": "openrouter/moonshotai/kimi-k2.5",
					"label": "Kimi K2.5",
					"max_tokens": 2000000,
					"vision": True,
				},
				{
					"name": "openrouter/z-ai/glm-5",
					"label": "GLM-5",
					"max_tokens": 200000,
					"vision": True,
				},
				{
					"name": "openrouter/moonshotai/kimi-k2",
					"label": "Kimi K2",
					"max_tokens": 131072,
					"vision": False,
				},
			],
		},
	]

	PROVIDER_DEFAULT: ClassVar[dict[str, str]] = {
		"openrouter": "openrouter/anthropic/claude-sonnet-4.6",
	}

	PROVIDER_SIMPLE: ClassVar[dict[str, str]] = {
		"openrouter": "openrouter/google/gemini-3-flash-preview",
	}

	@classmethod
	def get_label(cls, model_name: str) -> str:
		for provider in cls.AVAILABLE:
			for m in provider["models"]:
				if m["name"] == model_name:
					return m["label"]
		return model_name.removeprefix("openrouter/").replace("/", " ").replace("-", " ").title()

	@classmethod
	def get_progress_stage(cls, content: str) -> str | None:
		lookback = content[-400:]
		major_elements = ["section", "nav", "header", "footer"]

		last_pos = -1
		found_el = None
		for el in major_elements:
			pos = lookback.rfind(f"el: {el}")
			if pos > last_pos:
				last_pos = pos
				found_el = el

		if found_el and last_pos != -1:
			part = lookback[last_pos:]
			name_match = re.search(r"name:\s*['\"]?([^'\"\n]+)['\"]?", part)
			if name_match:
				block_name = name_match.group(1).strip()
				if block_name.lower() not in {"body", "root", "container"}:
					return f"Building {block_name}"
		return None

	@classmethod
	def detect_provider(cls, model: str) -> str | None:
		if model.lower().startswith("openrouter/"):
			return "openrouter"
		return None

	@classmethod
	def get_simple(cls, model: str) -> str:
		provider = cls.detect_provider(model)
		if provider is None:
			return cls.PROVIDER_SIMPLE.get(model, model)
		return cls.PROVIDER_SIMPLE.get(provider, model)

	@classmethod
	def get_default(cls, model_or_provider: str) -> str:
		return cls.PROVIDER_DEFAULT.get(model_or_provider, model_or_provider)
