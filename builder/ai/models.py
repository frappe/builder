"""The model registry: Builder AI Provider / Builder AI Model rows + live metadata.

Which models are offered is found, not configured in code. Providers are
DocTypes connected from Bob's /providers menu; their models are discovered from
each provider's own listing and kept to the frontier (builder/ai/discovery.py),
and a gateway with its own api_base lists its models through GatewayListing
below. A row can still be added, switched on or off by hand from the desk.

Everything factual about an OpenRouter model — context window, pricing (incl.
cache-read), vision support — is still fetched from OpenRouter's public models
API and cached, so it never goes stale. The values stored on the row are the
offline fallback, and the only source for every other provider.
"""

import logging
import re
from concurrent.futures import ThreadPoolExecutor

import frappe
import requests
from frappe.utils.caching import redis_cache

logger = frappe.logger("builder.ai.models")
logger.setLevel(logging.INFO)

CATALOG_TTL = 6 * 3600
ROWS_TTL = 3600
FETCH_TIMEOUT = 10
DEFAULT_CONTEXT_WINDOW = 200_000
# a new site starts with this in Builder Settings: the Frappe Cloud gateway's model
DEFAULT_AI_MODEL = "frappe/openai/gpt-5.6-terra"

# Used only when the rows are unreachable (install/migrate ordering) or all gone,
# so the agent still has something to call.
FALLBACK_MODEL = {
	"name": "openrouter/anthropic/claude-sonnet-5.5",
	"label": "Claude Sonnet 5.5",
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
					"from_site_config",
				],
				order_by="creation asc",
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
				"frontier_rank",
			],
			order_by="creation asc",
		)
	except Exception as e:
		logger.warning(f"AI model rows unavailable, using the built-in fallback: {e}")
		return [dict(FALLBACK_MODEL)]

	# providers in the order they were connected; within one, discovery's ranking
	# (best first), and rows added by hand after the ranked ones
	order = {name: i for i, name in enumerate(providers)}
	rows = sorted(rows, key=lambda r: (order.get(r.provider, 0), r.frontier_rank or len(rows) + 1))
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
				"from_site_config": bool(provider.from_site_config),
				"max_tokens": row.max_tokens or DEFAULT_CONTEXT_WINDOW,
				"vision": bool(row.supports_vision),
			}
		)
	return models or [dict(FALLBACK_MODEL)]


def route_site_config_models(models: list[dict]) -> list[dict]:
	"""Point the Frappe provider's models at the API site config names (a gateway, or Anthropic's own),
	whatever its row says. The row is only a record: one edited by hand, or by a script that skips
	validation, must never send the site's key to another address or another kind of API. With no key
	in site config the provider is off, so its models go too."""
	if not any(m.get("from_site_config") for m in models):
		return models
	from builder.ai.site_key import site_entry

	entry = site_entry()
	routed = []
	for m in models:
		if m.get("from_site_config"):
			if not entry:
				continue
			m = {**m, "api_base": entry.api_base, "litellm_provider": entry.litellm_provider}
		routed.append(m)
	return routed


def lookup_metadata(qualified_name: str, model_id: str) -> dict:
	"""Context window and vision support for a model, so nobody has to type them in.
	OpenRouter models come from its catalog; everything else from litellm's own model
	map, which knows the mainstream hosted models. An unknown model returns {} and
	keeps whatever defaults it was given."""
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


LISTING_TTL = 5 * 60
# The site config key is the host's: someone asking for the latest models sends it to the gateway at
# most this often, however often they ask.
SITE_KEY_LISTING_INTERVAL = 60
SITE_KEY_LISTING_KEY = "builder_ai_site_key_listing"
# Embeddings and rerankers answer /models too, and fail as chat models.
NON_CHAT_MARKERS = ("embed", "embedding", "rerank", "reranker", "whisper", "tts", "moderation")


class GatewayListing:
	"""The models a gateway with its own api_base serves right now, per its /models; and the models the
	site config key may call, from its gateway or Anthropic's /v1/models.

	Gateways add and retire models without telling anyone, so newly listed models
	get rows as they appear, and the cached listing lets the picker hide a model
	the gateway stopped serving instead of failing the turn that picks it."""

	def __init__(self, provider):
		self.provider = provider

	@classmethod
	def refresh_in_background(cls) -> None:
		"""Queue a sync when any gateway's listing is stale. A slow gateway never holds up the
		picker this way: it shows what is stored, and what changed on its next load."""
		names = cls.provider_names()
		if any(frappe.cache.get_value(cls.cache_key(name)) is None for name in names):
			frappe.enqueue(
				sync_stale_gateways,
				queue="short",
				job_id="builder_ai_gateway_sync",
				deduplicate=True,
				enqueue_after_commit=True,
			)

	@classmethod
	def sync_all(cls, force: bool = False) -> None:
		"""Sync every enabled gateway whose listing is stale (or all that may be asked, when forced)."""
		listings = [cls(frappe.get_doc("Builder AI Provider", name)) for name in cls.provider_names()]
		stale = [listing for listing in listings if not listing.is_fresh() or (force and listing.may_ask())]
		if not stale:
			return
		# side by side, so one unreachable gateway can't stall the picker for the rest
		with ThreadPoolExecutor(max_workers=len(stale)) as pool:
			outcomes = list(pool.map(fetch_listing, [listing.request() for listing in stale]))
		for listing, outcome in zip(stale, outcomes, strict=True):
			if isinstance(outcome, Exception):
				logger.warning(f"model listing failed for {listing.provider.name}: {outcome}")
				listing.remember(None)
			else:
				listing.apply(outcome)

	@staticmethod
	def provider_names() -> list[str]:
		"""Enabled providers that list their models at a gateway: their own api_base, or site config's."""
		return frappe.get_all(
			"Builder AI Provider",
			filters={"enabled": 1},
			or_filters={"api_base": ["is", "set"], "from_site_config": 1},
			pluck="name",
		)

	@classmethod
	def served_ids(cls, provider_name: str) -> set[str] | None:
		"""Ids from the last good listing, or None when there is none to go by."""
		cached = frappe.cache.get_value(cls.cache_key(provider_name)) or {}
		ids = cached.get("ids")
		return set(ids) if ids is not None else None

	@staticmethod
	def cache_key(provider_name: str) -> str:
		return f"builder_ai_gateway_listing::{provider_name}"

	def is_fresh(self) -> bool:
		return frappe.cache.get_value(self.cache_key(self.provider.name)) is not None

	def refresh(self) -> dict:
		"""sync(), for someone asking for the latest. Within SITE_KEY_LISTING_INTERVAL of the last time
		the site config key listed its gateway, what that listing found stands."""
		if not self.may_ask():
			return {"added": [], "skipped": [], "found": len(self.served_ids(self.provider.name) or [])}
		return self.sync()

	def may_ask(self) -> bool:
		if not self.provider.from_site_config:
			return True
		cache = frappe.cache
		key = cache.make_key(SITE_KEY_LISTING_KEY)
		return bool(cache.set(key, 1, nx=True, ex=SITE_KEY_LISTING_INTERVAL))

	def sync(self) -> dict:
		"""Add a row for every listed chat model that has none. Existing rows are
		left alone, so a model someone switched off stays off."""
		outcome = fetch_listing(self.request())
		if isinstance(outcome, Exception):
			from builder.ai.site_key import scrub_exception

			self.remember(None)
			# the error, and the traceback a member may be shown, name the gateway
			raise scrub_exception(outcome)
		return self.apply(outcome)

	def apply(self, listed: list) -> dict:
		"""`listed` is what /models answered: entries with an id, or bare ids."""
		entries = [entry if isinstance(entry, dict) else {"id": entry} for entry in listed]
		chosen = self.offered(entries)
		ids = [entry["id"] for entry in chosen]
		self.remember(ids)
		added = [entry["id"] for rank, entry in enumerate(chosen, start=1) if self.add_row(entry, rank)]
		if self.provider.from_site_config:
			from builder.ai.presets import adopt_default_model

			adopt_default_model(self.provider, ids)
		all_ids = {entry["id"] for entry in entries}
		return {"added": added, "skipped": sorted(all_ids - set(ids)), "found": len(entries)}

	def offered(self, entries: list[dict]) -> list[dict]:
		"""The listed models worth a row: an Anthropic site key's current models, else every chat model."""
		entry = self.site_key()
		if entry and entry.is_anthropic:
			from builder.ai.presets import match_model, preferred_model

			keep = match_model(preferred_model(), [e["id"] for e in entries])
			return current_claude_models(entries, keep)
		return [e for e in entries if not any(m in e["id"].lower() for m in NON_CHAT_MARKERS)]

	def site_key(self):
		"""The site config key, when this lists for it."""
		if not self.provider.from_site_config:
			return None
		from builder.ai.site_key import site_entry

		return site_entry()

	def credits(self) -> dict | None:
		"""The balance the gateway reports at its credits_url, or None when it reports none."""
		_, headers = self.request()
		return fetch_credits(self.provider.credits_url, headers)

	def request(self) -> tuple[str, dict]:
		if self.provider.from_site_config:
			# the API site config names and its own way of listing, whatever the row says
			entry = self.site_key()
			return entry.listing_request() if entry else ("", {})
		base = (self.provider.base_url() or "").rstrip("/")
		# Never the Builder Settings key: that belongs to OpenRouter, not this api_base.
		key = self.provider.resolved_key()
		if not base:
			return "", {}
		if self.provider.litellm_provider == "anthropic":
			# litellm treats an Anthropic api_base as the host root and appends /v1/messages
			return f"{base}/v1/models", {"x-api-key": key or "", "anthropic-version": "2023-06-01"}
		return f"{base}/models", {"Authorization": f"Bearer {key}"} if key else {}

	def remember(self, ids: list[str] | None) -> None:
		frappe.cache.set_value(self.cache_key(self.provider.name), {"ids": ids}, expires_in_sec=LISTING_TTL)

	def add_row(self, entry: dict, rank: int | None = None) -> bool:
		"""A row for a listed model that has none. What the listing says about it (Anthropic's names its
		display name, context window and image input) fills the row; litellm's model map the rest."""
		model_id = entry["id"]
		name = f"{self.provider.route_prefix}/{model_id}"
		if frappe.db.exists("Builder AI Model", name):
			# where it sits in the picker follows the listing; whether it is on stays the site's
			if rank and frappe.db.get_value("Builder AI Model", name, "frontier_rank") != rank:
				frappe.db.set_value("Builder AI Model", name, "frontier_rank", rank, update_modified=False)
				ModelRegistry.clear_cache()
			return False
		capabilities = entry.get("capabilities") or {}
		try:
			frappe.get_doc(
				{
					"doctype": "Builder AI Model",
					"provider": self.provider.name,
					"model_id": model_id,
					# the provider heads its group in the picker, so a vendor prefix is noise
					"label": entry.get("display_name") or model_id.rsplit("/", 1)[-1],
					"max_tokens": entry.get("max_input_tokens") or None,
					"supports_vision": int(supported(capabilities, "image_input")),
					"frontier_rank": rank,
					"enabled": 1,
				}
			).insert(ignore_permissions=True)
		except frappe.DuplicateEntryError:
			return False
		return True


def sync_stale_gateways() -> None:
	GatewayListing.sync_all()


def fetch_listing(request: tuple[str, dict]) -> list[dict] | Exception:
	"""The models a /models endpoint lists, each as it describes it (at least an id). Plain HTTP and no
	frappe calls, so it is safe in a worker thread; it returns the error rather than raising, so one
	failure can't sink a batch."""
	url, headers = request
	try:
		response = requests.get(url, headers=headers, timeout=FETCH_TIMEOUT)
		response.raise_for_status()
		return [entry for entry in response.json().get("data") or [] if (entry or {}).get("id")]
	except Exception as e:
		return e


def current_claude_models(entries: list[dict], keep: str | None = None) -> list[dict]:
	"""What an Anthropic key offers of what it lists: the newest model of each line (Opus, Sonnet,
	Fable...) that Builder's frontier policy admits (builder/ai/frontier.json: it takes images, has the
	context, and is no tier the policy leaves out, such as Haiku), never a deprecated or retiring one.
	`keep`, the model the host wants as the default, is offered whenever the key lists it. Best first:
	`keep`, then the newest."""
	from builder.ai.discovery import load_policy, qualifies

	policy = load_policy()
	newest: dict[str, dict] = {}
	for entry in sorted(entries, key=lambda e: e.get("created_at") or "", reverse=True):
		described = describe_claude(entry)
		if described["deprecated"] or not qualifies(described, policy):
			continue
		newest.setdefault(entry.get("line") or claude_line(entry["id"]), entry)
	chosen = list(newest.values())
	if keep and keep not in {e["id"] for e in chosen}:
		chosen += [e for e in entries if e["id"] == keep]
	chosen.sort(key=lambda e: e.get("created_at") or "", reverse=True)
	return sorted(chosen, key=lambda e: e["id"] != keep)


def describe_claude(entry: dict) -> dict:
	"""An Anthropic /v1/models entry in the terms discovery's policy judges by."""
	capabilities = entry.get("capabilities") or {}
	return {
		"id": entry["id"],
		"tools": True,  # every Claude model calls tools
		"input": ["text", "image"] if supported(capabilities, "image_input") else ["text"],
		"output": ["text"],
		"context": entry.get("max_input_tokens") or 0,
		"deprecated": bool(
			entry.get("deprecated_at")
			or entry.get("retires_at")
			or entry.get("lifecycle") not in (None, "active")
		),
	}


def claude_line(model_id: str) -> str:
	"""claude-opus-4-5-20251101 -> claude-opus, for a listing that names no line."""
	return re.sub(r"-\d.*$", "", model_id)


def supported(capabilities: dict, name: str) -> bool:
	found = capabilities.get(name)
	return bool(found.get("supported") if isinstance(found, dict) else found)


def fetch_credits(url: str, headers: dict) -> dict | None:
	"""The balance a gateway reports at `url` as {balance, spent}, or None when it reports none."""
	try:
		response = requests.get(url, headers=headers, timeout=FETCH_TIMEOUT)
		response.raise_for_status()
		reported = response.json()
	except Exception:
		return None
	if not isinstance(reported, dict) or not is_number(reported.get("balance")):
		return None
	spent = reported.get("spent")
	return {"balance": reported["balance"], "spent": spent if is_number(spent) else None}


def is_number(value) -> bool:
	return isinstance(value, int | float) and not isinstance(value, bool)


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
			for m in route_site_config_models(load_models())
		]

	@classmethod
	def available(cls) -> list[dict]:
		"""Provider-grouped catalog — the shape the model picker consumes.

		Only models that can actually be called: their provider's own key, a
		gateway's api_base (which may need no key), or for OpenRouter the shared one
		in Builder Settings. A model with nothing behind it belongs to a provider
		that isn't connected, and connecting is what /providers is for. Computed
		here rather than in the cached row loader, so key state is never held in redis."""
		from builder.ai.llm import provider_api_key, settings_api_key, uses_settings_key

		fallback = bool(settings_api_key())
		default = get_configured_default()
		grouped: dict[str, list] = {}
		for m in cls.catalog():
			if not cls.still_served(m):
				continue
			if not (m.get("api_base") or provider_api_key(m) or (fallback and uses_settings_key(m))):
				continue
			grouped.setdefault(m["provider"], []).append(
				{**public_model(m), "ready": True, "default": m["name"] == default}
			)
		return [{"provider": provider, "models": models} for provider, models in grouped.items()]

	@staticmethod
	def still_served(m: dict) -> bool:
		served = GatewayListing.served_ids(m["provider"]) if m.get("api_base") else None
		prefix = m.get("route_prefix") or ""
		return served is None or m["name"][len(prefix) + 1 :] in served

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
		frontend still sends) falls back to the Builder Settings default, then to
		the first configured model."""
		if cls.find(model_or_provider):
			return model_or_provider
		default = get_configured_default()
		if default and cls.find(default):
			return default
		catalog = cls.catalog()
		return catalog[0]["name"] if catalog else model_or_provider

	@classmethod
	def is_known_model(cls, model: str) -> bool:
		return cls.find(model) is not None


def public_model(m: dict) -> dict:
	"""A model as the browser sees it. Where it is called and how stay on the server: the site config
	gateway's address is the host's, not the site's. `gateway` says it may report credits."""
	public = {k: v for k, v in m.items() if k not in ("api_base", "litellm_provider")}
	return {**public, "gateway": bool(m.get("api_base"))}


def get_configured_default() -> str | None:
	"""The model Builder Settings names as the default, which may not be available."""
	return frappe.db.get_single_value("Builder Settings", "default_ai_model")
