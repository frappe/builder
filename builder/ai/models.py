from typing import ClassVar


class ModelRegistry:
	AVAILABLE: ClassVar[list] = [
		{
			"provider": "openrouter",
			"models": [
				{
					"name": "openrouter/anthropic/claude-opus-4.8",
					"label": "Claude Opus 4.8",
					"max_tokens": 1048576,
					"input_price": 5.0,
					"output_price": 25.0,
					"vision": True,
				},
				{
					"name": "openrouter/anthropic/claude-sonnet-4.6",
					"label": "Claude Sonnet 4.6",
					"max_tokens": 200000,
					"input_price": 3.0,
					"output_price": 15.0,
					"vision": True,
				},
				{
					"name": "openrouter/anthropic/claude-haiku-4-6",
					"label": "Claude Haiku 4.6",
					"max_tokens": 200000,
					"input_price": 1.0,
					"output_price": 5.0,
					"vision": True,
				},
				{
					"name": "openrouter/openai/gpt-5.4",
					"label": "GPT-5.4",
					"max_tokens": 1048576,
					"input_price": 2.5,
					"output_price": 10.0,
					"vision": True,
				},
				{
					"name": "openrouter/google/gemini-3.1-pro-preview",
					"label": "Gemini 3.1 Pro",
					"max_tokens": 1048576,
					"input_price": 2.0,
					"output_price": 12.0,
					"vision": True,
				},
				# --- Fast / cheap (great value for the conversational loop + edits) ---
				{
					"name": "openrouter/google/gemini-3.5-flash",
					"label": "Gemini 3.5 Flash",
					"max_tokens": 1048576,
					"input_price": 1.5,
					"output_price": 4.5,
					"vision": True,
				},
				{
					"name": "openrouter/google/gemini-3.1-flash-lite",
					"label": "Gemini 3.1 Flash Lite",
					"max_tokens": 1048576,
					"input_price": 0.25,
					"output_price": 1.0,
					"vision": True,
				},
				{
					"name": "openrouter/openai/gpt-5.4-mini",
					"label": "GPT-5.4 Mini",
					"max_tokens": 400000,
					"input_price": 0.75,
					"output_price": 3.0,
					"vision": True,
				},
				{
					"name": "openrouter/deepseek/deepseek-v4-pro",
					"label": "DeepSeek V4 Pro",
					"max_tokens": 1048576,
					"input_price": 0.435,
					"output_price": 1.75,
					"vision": False,
				},
				{
					"name": "openrouter/deepseek/deepseek-v4-flash",
					"label": "DeepSeek V4 Flash",
					"max_tokens": 1048576,
					"input_price": 0.098,
					"output_price": 0.4,
					"vision": False,
				},
				# --- Open-weight alternatives ---
				{
					"name": "openrouter/moonshotai/kimi-k2.6",
					"label": "Kimi K2.6",
					"max_tokens": 262144,
					"input_price": 0.68,
					"output_price": 2.7,
					"vision": True,
				},
				{
					"name": "openrouter/z-ai/glm-5.2",
					"label": "GLM-5.2",
					"max_tokens": 203000,
					"input_price": 1.1,
					"output_price": 4.4,
					"vision": False,
				},
				{
					"name": "openrouter/z-ai/glm-5.1",
					"label": "GLM-5.1",
					"max_tokens": 203000,
					"input_price": 0.98,
					"output_price": 3.9,
					"vision": False,
				},
				{
					"name": "openrouter/qwen/qwen3.7-max",
					"label": "Qwen 3.7 Max",
					"max_tokens": 1048576,
					"input_price": 1.25,
					"output_price": 5.0,
					"vision": True,
				},
			],
		},
	]

	PROVIDER_DEFAULT: ClassVar[dict[str, str]] = {
		"openrouter": "openrouter/anthropic/claude-sonnet-4.6",
	}

	PROVIDER_SIMPLE: ClassVar[dict[str, str]] = {
		"openrouter": "openrouter/google/gemini-3.5-flash",
	}

	@classmethod
	def get_label(cls, model_name: str) -> str:
		for provider in cls.AVAILABLE:
			for m in provider["models"]:
				if m["name"] == model_name:
					return m["label"]
		return model_name.removeprefix("openrouter/").replace("/", " ").replace("-", " ").title()

	@classmethod
	def detect_provider(cls, model: str) -> str | None:
		if model.lower().startswith("openrouter/"):
			return "openrouter"
		return None

	@classmethod
	def input_price(cls, model_name: str) -> float:
		"""Input price (USD per 1M tokens) for cost comparison. Unknown models are
		treated as expensive (inf) so the loop safely downgrades to the cheap model."""
		for provider in cls.AVAILABLE:
			for m in provider["models"]:
				if m["name"] == model_name:
					return m.get("input_price", float("inf"))
		return float("inf")

	@classmethod
	def output_price(cls, model_name: str) -> float | None:
		"""Output price (USD per 1M tokens); None for unknown models (cost then
		reads as unavailable rather than a wrong number)."""
		for provider in cls.AVAILABLE:
			for m in provider["models"]:
				if m["name"] == model_name:
					return m.get("output_price")
		return None

	@classmethod
	def context_window(cls, model_name: str) -> int:
		"""The model's context window in tokens (`max_tokens` in the registry)."""
		for provider in cls.AVAILABLE:
			for m in provider["models"]:
				if m["name"] == model_name:
					return int(m.get("max_tokens") or 200_000)
		return 200_000

	@classmethod
	def estimate_cost(cls, model_name: str, prompt: int, completion: int, cached: int = 0) -> float | None:
		"""Approximate USD cost of one call from the registry's per-1M prices.
		Cache reads bill at a provider discount (~10% Anthropic, ~25% elsewhere).
		Approximate by design — OpenRouter's exact cost isn't surfaced by litellm."""
		inp, outp = cls.input_price(model_name), cls.output_price(model_name)
		if outp is None or inp == float("inf"):
			return None
		factor = 0.1 if "/anthropic/" in model_name else 0.25
		fresh = max(prompt - cached, 0)
		return (fresh * inp + cached * inp * factor + completion * outp) / 1_000_000

	@classmethod
	def get_simple(cls, model: str) -> str:
		"""The model to run the lightweight conversational loop (clarify / plan /
		targeted edits) on. Only downgrade to the cheap loop model when the
		selected model is PRICIER than it — if the user already picked something
		as cheap or cheaper, keep their model rather than forcing a swap."""
		provider = cls.detect_provider(model)
		if provider is None:
			return cls.PROVIDER_SIMPLE.get(model, model)
		simple = cls.PROVIDER_SIMPLE.get(provider, model)
		if cls.input_price(model) <= cls.input_price(simple):
			return model
		return simple

	@classmethod
	def supports_vision(cls, model_name: str) -> bool:
		"""Whether this model accepts image input. Unknown models are treated as
		text-only — sending an image a provider can't route kills the whole turn
		(OpenRouter: 'No endpoints found that support image input')."""
		for provider in cls.AVAILABLE:
			for m in provider["models"]:
				if m["name"] == model_name:
					return bool(m.get("vision"))
		return False

	@classmethod
	def get_default(cls, model_or_provider: str) -> str:
		return cls.PROVIDER_DEFAULT.get(model_or_provider, model_or_provider)

	@classmethod
	def is_known_model(cls, model: str) -> bool:
		return any(m["name"] == model for provider in cls.AVAILABLE for m in provider["models"])
