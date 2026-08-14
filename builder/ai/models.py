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
	"max_tokens": 1_000_000,
	"vision": True,
}


@redis_cache(ttl=CATALOG_TTL)
def fetch_openrouter_catalog() -> dict:
	"""Live metadata for every OpenRouter model, keyed by our litellm-prefixed name."""
	r = requests.get("https://openrouter.ai/api/v1/models", timeout=FETCH_TIMEOUT)
	r.raise_for_status()
	catalog = {}
	for m in r.json().get("data", []):
		modalities = (m.get("architecture") or {}).get("input_modalities") or []
		catalog[f"openrouter/{m['id']}"] = {
			"max_tokens": m.get("context_length"),
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
				"max_tokens": row.max_tokens or DEFAULT_CONTEXT_WINDOW,
				"vision": bool(row.supports_vision),
			}
		)
	return models or [dict(FALLBACK_MODEL)]


def lookup_metadata(qualified_name: str, model_id: str) -> dict:
	"""Context window and vision support for a model, so nobody has to type them in.
	OpenRouter models come from its catalog; everything else from litellm's own model
	map, which knows the mainstream hosted models. An unknown model returns {} and
	keeps whatever defaults it was given."""
	if qualified_name.startswith("codex/"):
		from builder.ai.codex import model_metadata

		if found := model_metadata(model_id):
			return found
	if qualified_name.startswith("openrouter/"):
		try:
			if found := fetch_openrouter_catalog().get(qualified_name):
				return {k: v for k, v in found.items() if v is not None}
		except Exception as e:
			logger.warning(f"OpenRouter lookup failed for {qualified_name}: {e}")

	try:
		import litellm

		# the cost map directly: get_model_info raises (and logs a provider list) for
		# every model it does not know, which is the normal case for a custom gateway
		info = litellm.model_cost.get(model_id) or litellm.model_cost.get(model_id.split("/")[-1])
	except Exception:
		info = None
	if not info:
		return {}
	found = {
		"max_tokens": info.get("max_input_tokens") or info.get("max_tokens"),
		"vision": info.get("supports_vision"),
	}
	return {k: v for k, v in found.items() if v is not None}


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
		"""Provider-grouped catalog — the shape the model picker consumes.

		`ready` says whether this model can actually be called: its provider's own
		key, or the shared one in Builder Settings. Computed here rather than in the
		cached row loader, so key state is never held in redis, and so the picker can
		say a model is unusable BEFORE someone writes a prompt for it."""
		from builder.ai.llm import provider_api_key

		fallback = bool(
			frappe.get_single("Builder Settings").get_password("ai_api_key", raise_exception=False)
		)
		grouped: dict[str, list] = {}
		for m in cls.catalog():
			grouped.setdefault(m["provider"], []).append(
				{**m, "ready": bool(provider_api_key(m)) or fallback}
			)
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
	def context_window(cls, model_name: str) -> int:
		m = cls.find(model_name)
		return int((m or {}).get("max_tokens") or DEFAULT_CONTEXT_WINDOW)

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
		frontend still sends) falls back to the first configured model."""
		if cls.find(model_or_provider):
			return model_or_provider
		catalog = cls.catalog()
		return catalog[0]["name"] if catalog else model_or_provider

	@classmethod
	def is_known_model(cls, model: str) -> bool:
		return cls.find(model) is not None
