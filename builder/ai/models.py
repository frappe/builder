"""The model registry: a small CURATED allowlist + live metadata.

Which models are offered is a hand-picked QUALITY judgment — only models that
reliably produce well-designed pages (plus one fast/cheap model for the
lightweight conversational loop). Everything factual about them — context
window, pricing (incl. cache-read), vision support — is fetched from
OpenRouter's public models API and cached, so it never goes stale in code.
The static values on each curated entry are only the offline fallback.
"""

import logging
from typing import ClassVar

import frappe
import requests
from frappe.utils.caching import redis_cache

logger = frappe.logger("builder.ai.models")
logger.setLevel(logging.INFO)

CATALOG_TTL = 6 * 3600
FETCH_TIMEOUT = 10


@redis_cache(ttl=CATALOG_TTL)
def fetch_openrouter_catalog() -> dict:
	"""Live metadata for every OpenRouter model, keyed by our litellm-prefixed
	name. Prices normalised to USD per 1M tokens."""
	r = requests.get("https://openrouter.ai/api/v1/models", timeout=FETCH_TIMEOUT)
	r.raise_for_status()
	catalog = {}
	for m in r.json().get("data", []):
		pricing = m.get("pricing") or {}
		modalities = (m.get("architecture") or {}).get("input_modalities") or []

		def per_million(key: str) -> float | None:
			try:
				return float(pricing[key]) * 1_000_000
			except (KeyError, TypeError, ValueError):
				return None

		catalog[f"openrouter/{m['id']}"] = {
			"max_tokens": m.get("context_length"),
			"input_price": per_million("prompt"),
			"output_price": per_million("completion"),
			"cache_read_price": per_million("input_cache_read"),
			"vision": "image" in modalities,
		}
	return catalog


class ModelRegistry:
	# The quality gate: models trusted to design good pages, in display order.
	# Gemini 3.5 Flash stays as the cheap conversational-loop model (see
	# PROVIDER_SIMPLE). Static fields are offline fallbacks — live OpenRouter
	# data overrides them (see catalog()).
	CURATED: ClassVar[list] = [
		{
			"name": "openrouter/anthropic/claude-sonnet-5",
			"label": "Claude Sonnet 5",
			"max_tokens": 1_000_000,
			"input_price": 2.0,
			"output_price": 10.0,
			"vision": True,
		},
		{
			"name": "openrouter/anthropic/claude-opus-4.8",
			"label": "Claude Opus 4.8",
			"max_tokens": 1_000_000,
			"input_price": 5.0,
			"output_price": 25.0,
			"vision": True,
		},
		{
			"name": "openrouter/anthropic/claude-fable-5",
			"label": "Claude Fable 5",
			"max_tokens": 1_000_000,
			"input_price": 10.0,
			"output_price": 50.0,
			"vision": True,
		},
		{
			"name": "openrouter/openai/gpt-5.5",
			"label": "GPT-5.5",
			"max_tokens": 1_050_000,
			"input_price": 5.0,
			"output_price": 30.0,
			"vision": True,
		},
		{
			"name": "openrouter/google/gemini-3.1-pro-preview",
			"label": "Gemini 3.1 Pro",
			"max_tokens": 1_048_576,
			"input_price": 2.0,
			"output_price": 12.0,
			"vision": True,
		},
		{
			"name": "openrouter/google/gemini-3.5-flash",
			"label": "Gemini 3.5 Flash",
			"max_tokens": 1_048_576,
			"input_price": 1.5,
			"output_price": 9.0,
			"vision": True,
		},
		{
			# Free OpenRouter tier for local testing — native tool calling, zero cost.
			# 0.0 prices keep the whole loop (incl. the lightweight clarify/plan rounds)
			# on this model rather than falling back to paid Gemini via PROVIDER_SIMPLE.
			# Text-only: vision False, or an image input kills the turn.
			"name": "openrouter/nvidia/nemotron-3-ultra-550b-a55b:free",
			"label": "Nemotron 3 Ultra (Free)",
			"max_tokens": 1_000_000,
			"input_price": 0.0,
			"output_price": 0.0,
			"vision": False,
		},
	]

	PROVIDER_DEFAULT: ClassVar[dict[str, str]] = {
		"openrouter": "openrouter/anthropic/claude-sonnet-5",
	}

	PROVIDER_SIMPLE: ClassVar[dict[str, str]] = {
		"openrouter": "openrouter/google/gemini-3.5-flash",
	}

	@classmethod
	def catalog(cls) -> list[dict]:
		"""The curated models with live metadata merged over the static fallbacks.
		A failed/unreachable fetch degrades to the fallbacks, never to an error."""
		live = {}
		try:
			live = fetch_openrouter_catalog()
		except Exception as e:
			logger.warning(f"OpenRouter catalog fetch failed, using static fallbacks: {e}")
		return [
			{**m, **{k: v for k, v in (live.get(m["name"]) or {}).items() if v is not None}}
			for m in cls.CURATED
		]

	@classmethod
	def available(cls) -> list[dict]:
		"""Provider-grouped catalog — the shape the model picker consumes."""
		return [{"provider": "openrouter", "models": cls.catalog()}]

	@classmethod
	def find(cls, model_name: str) -> dict | None:
		for m in cls.catalog():
			if m["name"] == model_name:
				return m
		return None

	@classmethod
	def get_label(cls, model_name: str) -> str:
		m = cls.find(model_name)
		if m:
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
		m = cls.find(model_name)
		return m.get("input_price", float("inf")) if m else float("inf")

	@classmethod
	def output_price(cls, model_name: str) -> float | None:
		"""Output price (USD per 1M tokens); None for unknown models (cost then
		reads as unavailable rather than a wrong number)."""
		m = cls.find(model_name)
		return m.get("output_price") if m else None

	@classmethod
	def context_window(cls, model_name: str) -> int:
		m = cls.find(model_name)
		return int((m or {}).get("max_tokens") or 200_000)

	@classmethod
	def estimate_cost(cls, model_name: str, prompt: int, completion: int, cached: int = 0) -> float | None:
		"""Approximate USD cost of one call. Uses the provider's exact cache-read
		price when the live catalog has it; otherwise a discount heuristic
		(~10% Anthropic, ~25% elsewhere)."""
		m = cls.find(model_name)
		if not m or m.get("output_price") is None or m.get("input_price") is None:
			return None
		inp, outp = m["input_price"], m["output_price"]
		cache_read = m.get("cache_read_price")
		if cache_read is None:
			cache_read = inp * (0.1 if "/anthropic/" in model_name else 0.25)
		fresh = max(prompt - cached, 0)
		return (fresh * inp + cached * cache_read + completion * outp) / 1_000_000

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
		m = cls.find(model_name)
		return bool(m.get("vision")) if m else False

	@classmethod
	def get_default(cls, model_or_provider: str) -> str:
		return cls.PROVIDER_DEFAULT.get(model_or_provider, model_or_provider)

	@classmethod
	def is_known_model(cls, model: str) -> bool:
		return cls.find(model) is not None
