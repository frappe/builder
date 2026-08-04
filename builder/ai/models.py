"""The model registry: Builder AI Provider / Builder AI Model rows + live metadata.

Which models are offered is a configuration decision, not a code one. Providers
and models are DocTypes, so a new gateway (OpenRouter, any OpenAI-compatible
endpoint, a local Ollama) or a new model is added from the desk UI without a
deploy; `builder.builder.patches.seed_ai_providers_and_models` seeds the shipped
shortlist on migrate.

Everything factual about an OpenRouter model — context window, pricing (incl.
cache-read), vision support — is still fetched from OpenRouter's public models
API and cached, so it never goes stale. The values stored on the row are the
offline fallback, and the only source for every other provider.
"""

import logging

import frappe
import requests
from frappe.utils.caching import redis_cache

logger = frappe.logger("builder.ai.models")
logger.setLevel(logging.INFO)

CATALOG_TTL = 6 * 3600
ROWS_TTL = 3600
FETCH_TIMEOUT = 10
DEFAULT_CONTEXT_WINDOW = 200_000

# Used only when the rows are unreachable (install/migrate ordering) or all gone,
# so the agent still has something to call.
FALLBACK_MODEL = {
	"name": "openrouter/anthropic/claude-sonnet-5",
	"label": "Claude Sonnet 5",
	"provider": "OpenRouter",
	"route_prefix": "openrouter",
	"litellm_provider": "openrouter",
	"api_base": None,
	"extra_headers": None,
	"extra_body": None,
	"max_tokens": 1_000_000,
	"input_price": 2.0,
	"output_price": 10.0,
	"cache_read_price": None,
	"temperature": None,
	"vision": True,
	"is_default": 1,
	"is_simple": 0,
}


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


@redis_cache(ttl=ROWS_TTL)
def load_models() -> list[dict]:
	"""Every enabled model, flattened with its provider's routing fields. Cached
	because the loop asks for model facts many times per turn; both doctypes clear
	it on update."""
	try:
		providers = {
			p.name: p
			for p in frappe.get_all(
				"Builder AI Provider",
				filters={"enabled": 1},
				fields=[
					"name",
					"route_prefix",
					"litellm_provider",
					"api_base",
					"extra_headers",
					"extra_body",
				],
			)
		}
		rows = frappe.get_all(
			"Builder AI Model",
			filters={"enabled": 1},
			fields=[
				"name",
				"label",
				"provider",
				"supports_vision",
				"max_tokens",
				"temperature",
				"input_price",
				"output_price",
				"cache_read_price",
				"is_default",
				"is_simple",
			],
			order_by="creation asc",
		)
	except Exception as e:
		logger.warning(f"AI model rows unavailable, using the built-in fallback: {e}")
		return [dict(FALLBACK_MODEL)]

	models = []
	for row in rows:
		provider = providers.get(row.provider)
		if not provider:
			continue  # a disabled provider takes its models with it
		models.append(
			{
				"name": row.name,
				"label": row.label or row.name,
				"provider": provider.name,
				"route_prefix": provider.route_prefix,
				"litellm_provider": provider.litellm_provider,
				"api_base": provider.api_base or None,
				"extra_headers": provider.extra_headers or None,
				"extra_body": provider.extra_body or None,
				"max_tokens": row.max_tokens or DEFAULT_CONTEXT_WINDOW,
				"input_price": row.input_price,
				"output_price": row.output_price,
				"cache_read_price": row.cache_read_price or None,
				"temperature": row.temperature or None,
				"vision": bool(row.supports_vision),
				"is_default": row.is_default,
				"is_simple": row.is_simple,
			}
		)
	return models or [dict(FALLBACK_MODEL)]


class ModelRegistry:
	@classmethod
	def clear_cache(cls) -> None:
		load_models.clear_cache()

	@classmethod
	def catalog(cls) -> list[dict]:
		"""The configured models with live OpenRouter metadata merged over the
		stored values. A failed/unreachable fetch degrades to the stored values,
		never to an error."""
		live = {}
		try:
			live = fetch_openrouter_catalog()
		except Exception as e:
			logger.warning(f"OpenRouter catalog fetch failed, using stored values: {e}")
		return [
			{**m, **{k: v for k, v in (live.get(m["name"]) or {}).items() if v is not None}}
			for m in load_models()
		]

	@classmethod
	def available(cls) -> list[dict]:
		"""Provider-grouped catalog — the shape the model picker consumes."""
		grouped: dict[str, list] = {}
		for m in cls.catalog():
			grouped.setdefault(m["provider"], []).append(m)
		return [{"provider": provider, "models": models} for provider, models in grouped.items()]

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
		return model_name.split("/", 1)[-1].replace("/", " ").replace("-", " ").title()

	@classmethod
	def detect_provider(cls, model: str) -> str | None:
		m = cls.find(model)
		return m["provider"] if m else None

	@classmethod
	def input_price(cls, model_name: str) -> float:
		"""Input price (USD per 1M tokens) for cost comparison. Unknown models are
		treated as expensive (inf) so the loop safely downgrades to the cheap model."""
		m = cls.find(model_name)
		if not m or m.get("input_price") is None:
			return float("inf")
		return m["input_price"]

	@classmethod
	def output_price(cls, model_name: str) -> float | None:
		"""Output price (USD per 1M tokens); None for unknown models (cost then
		reads as unavailable rather than a wrong number)."""
		m = cls.find(model_name)
		return m.get("output_price") if m else None

	@classmethod
	def context_window(cls, model_name: str) -> int:
		m = cls.find(model_name)
		return int((m or {}).get("max_tokens") or DEFAULT_CONTEXT_WINDOW)

	@classmethod
	def temperature_override(cls, model_name: str) -> float | None:
		"""The temperature a model insists on, when it rejects the agent tier's."""
		m = cls.find(model_name)
		return m.get("temperature") if m else None

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
	def simple_model(cls) -> str | None:
		return next((m["name"] for m in cls.catalog() if m.get("is_simple")), None)

	@classmethod
	def get_simple(cls, model: str) -> str:
		"""The model to run the lightweight conversational loop (clarify / plan /
		targeted edits) on. Only downgrade to the cheap loop model when the
		selected model is PRICIER than it — if the user already picked something
		as cheap or cheaper, keep their model rather than forcing a swap."""
		simple = cls.simple_model()
		if not simple or simple == model:
			return model
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
		"""Resolve a selection to a model name. A known model passes through;
		anything else (a provider name, or the legacy "openrouter" sentinel the
		frontend still sends) resolves to the model flagged as default."""
		if cls.find(model_or_provider):
			return model_or_provider
		default = next((m["name"] for m in cls.catalog() if m.get("is_default")), None)
		return default or model_or_provider

	@classmethod
	def is_known_model(cls, model: str) -> bool:
		return cls.find(model) is not None
