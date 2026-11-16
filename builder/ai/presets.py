"""The providers Bob can connect to, and connecting one.

A preset carries what connecting needs and nobody should have to look up: how
the provider signs in, where a key comes from, how litellm routes it, and where
its models are listed and described. It names no models. Discovery
(builder/ai/discovery.py) finds those once the provider is connected, so a model
released tomorrow shows up without a change here.

Everything a preset creates is an ordinary Builder AI Provider row.
"""

from contextlib import contextmanager
from contextvars import ContextVar

import frappe
from frappe import _

from builder.ai.models import (
	DEFAULT_AI_MODEL,
	GatewayListing,
	ModelRegistry,
	get_configured_default,
)
from builder.ai.site_key import SiteAIKey

PRESETS = [
	{
		"id": "codex",
		"name": "ChatGPT",
		"tagline": "Sign in with your ChatGPT plan",
		"route_prefix": "codex",
		"litellm_provider": "codex",
		"oauth": True,
		"listing": "codex",
		"catalog": "openai",
		"lab": "openai",
	},
	{
		"id": "anthropic",
		"name": "Anthropic",
		"tagline": "Claude, with an API key",
		"route_prefix": "anthropic",
		"litellm_provider": "anthropic",
		"key_url": "https://console.anthropic.com/settings/keys",
		"key_prefix": "sk-ant-",
		"listing": "anthropic",
		"catalog": "anthropic",
		"lab": "anthropic",
	},
	{
		"id": "openai",
		"name": "OpenAI",
		"tagline": "GPT, with an API key",
		"route_prefix": "openai",
		"litellm_provider": "openai",
		"key_url": "https://platform.openai.com/api-keys",
		"key_prefix": "sk-",
		"listing": "openai",
		"catalog": "openai",
		"lab": "openai",
	},
	{
		"id": "google",
		"name": "Google Gemini",
		"tagline": "Gemini, with an API key",
		"route_prefix": "gemini",
		"litellm_provider": "gemini",
		"key_url": "https://aistudio.google.com/apikey",
		"listing": "gemini",
		"catalog": "google",
		"lab": "google",
	},
	{
		"id": "openrouter",
		"name": "OpenRouter",
		"tagline": "Claude, GPT and Gemini on one key",
		"route_prefix": "openrouter",
		"litellm_provider": "openrouter",
		"key_url": "https://openrouter.ai/keys",
		"key_prefix": "sk-or-",
		"listing": "openrouter",
		"catalog": "openrouter",
	},
	{
		"id": "custom",
		"name": "",  # named after its URL by the client
		"tagline": "Any OpenAI-compatible endpoint",
		"custom": True,
	},
]


SITE_PROVIDER = {"provider_name": "Frappe", "route_prefix": "frappe"}
# a host app names the model of the site config key it wants as the default: an id, or part of one
DEFAULT_MODEL_HOOK = "builder_ai_default_model"
# the default this sync chose last, so a default the site picked itself is told apart and kept
ADOPTED_DEFAULT_KEY = "builder_ai_adopted_default_model"

logger = frappe.logger("builder.ai.presets")

# set only while sync_site_provider writes the row; scripts cannot reach a module's globals
_syncing_site_provider: ContextVar[bool] = ContextVar("builder_ai_syncing_site_provider", default=False)


@contextmanager
def syncing_site_provider():
	token = _syncing_site_provider.set(True)
	try:
		yield
	finally:
		_syncing_site_provider.reset(token)


def may_change_site_provider() -> bool:
	"""Whether this code may write the provider site config owns: the sync itself, or Administrator from
	the bench or an install. Never a member, and never a script, which can run as anyone."""
	if _syncing_site_provider.get():
		return True
	return frappe.session.user == "Administrator" and not frappe.flags.in_safe_exec


def get_site_ai_key(fresh: bool = False) -> SiteAIKey | None:
	"""The first `ai_keys` entry site config holds (see SiteAIKey for its shapes). A request sees config
	cached for up to 60 seconds, and Frappe Cloud can add the key inside that window: `fresh` reads the
	config files instead."""
	conf = frappe.get_site_config() if fresh else frappe.conf
	entries = conf.get("ai_keys") or []
	return SiteAIKey.from_entry(entries[0]) if entries else None


def sync_site_provider() -> None:
	"""Keep the Frappe provider in step with site config: on while `ai_keys` has a key,
	off when it has none. Site config keeps the key and a gateway's address, which
	the host may not want members to read, so the row holds neither: calls go to the
	API site config names (base_url()). A newly registered provider also lists its
	models and sets the default model. Frappe Cloud can add the key after install, so
	without the provider the config files are read past the request cache."""
	doc = get_site_provider()
	entry = get_site_ai_key(fresh=not doc)
	if not doc and entry:
		doc = new_site_provider(entry)
	if not doc:
		return
	# the routing is re-asserted too, should anything have changed the row behind validation; it is
	# only a record of it (models.route_site_config_models routes by site config)
	fields = {
		"api_base": None,
		"enabled": int(bool(entry)),
		"litellm_provider": entry.litellm_provider if entry else doc.litellm_provider,
		"route_prefix": SITE_PROVIDER["route_prefix"],
	}
	is_registering = not doc.name
	# a key for another API (a gateway's replaced by Anthropic's) can call none of the models listed before
	switched_api = bool(entry) and not is_registering and doc.litellm_provider != entry.litellm_provider
	if is_registering or any(doc.get(field) != value for field, value in fields.items()):
		doc.update(fields)
		with syncing_site_provider():
			doc.save(ignore_permissions=True)
	if switched_api:
		forget_models(doc)
	if is_registering or switched_api:
		list_models(doc)


def forget_models(provider) -> None:
	"""Remove the provider's models and what its last listing found, before listing another API's."""
	frappe.db.delete("Builder AI Model", {"provider": provider.name})
	frappe.cache.delete_value(GatewayListing.cache_key(provider.name))
	ModelRegistry.clear_cache()


def list_models(provider) -> None:
	"""Add the key's models now, so the first model list is not empty. An API that is down
	must not fail an install or a migrate: the next model list load retries."""
	try:
		GatewayListing(provider).sync()
	except Exception as error:
		logger.error(f"could not list the models of {provider.name}: {error}")


def adopt_default_model(provider, listed: list[str]) -> None:
	"""Make the model the host prefers the default, once the site config key lists it.

	A default the site picked itself stays. Three kinds are not the site's pick and give way: none at
	all, one this sync set before, and one naming a model the site cannot call. So a preference that
	changes later still takes over, and so does a host's preference once its app is installed (Builder
	installs first, and registers the provider before the host's hook exists)."""
	model_id = match_model(preferred_model(), listed)
	if not model_id:
		return
	name = f"{provider.route_prefix}/{model_id}"
	if not frappe.db.get_value("Builder AI Model", name, "enabled"):
		return  # switched off on this site
	current = get_configured_default()
	if current != name:
		if current and current != frappe.db.get_default(ADOPTED_DEFAULT_KEY) and can_call(current):
			return
		frappe.db.set_single_value("Builder Settings", "default_ai_model", name)
	frappe.db.set_default(ADOPTED_DEFAULT_KEY, name)


def can_call(model_name: str) -> bool:
	"""Whether the site can call this model: a row is on for it, and the API it is on still serves it."""
	found = ModelRegistry.find(model_name)
	return bool(found) and ModelRegistry.still_served(found)


def preferred_model() -> str:
	"""What a host app asks for (hook builder_ai_default_model), else the Frappe Cloud gateway's model."""
	from builder.ai.site_key import host_hook

	if (wanted_by_host := host_hook(DEFAULT_MODEL_HOOK)) and (wanted := wanted_by_host()):
		return wanted
	return DEFAULT_AI_MODEL.removeprefix(f"{SITE_PROVIDER['route_prefix']}/")


def match_model(wanted: str, ids: list[str]) -> str | None:
	"""The id `wanted` names, ignoring case: that id, else the id whose last part it is, else the
	shortest id containing it (so "sol" picks gpt-6.1-sol over gpt-6.1-sol-mini)."""
	wanted = (wanted or "").strip().lower()
	if not wanted:
		return None
	for found in (
		[i for i in ids if i.lower() == wanted],
		[i for i in ids if i.lower().rsplit("/", 1)[-1] == wanted],
		sorted((i for i in ids if wanted in i.lower()), key=len),
	):
		if found:
			return found[0]
	return None


def site_gateway_base() -> str | None:
	"""Where the site config key may go (SiteAIKey.api_base), or None with no key."""
	entry = get_site_ai_key() or get_site_ai_key(fresh=True)
	return entry.api_base if entry else None


def get_site_provider():
	"""The provider row site config owns, or None."""
	if name := frappe.db.get_value("Builder AI Provider", {"from_site_config": 1}):
		return frappe.get_doc("Builder AI Provider", name)
	return None


def new_site_provider(entry: SiteAIKey):
	"""A new unsaved provider for the site config key. A row of a member's in its way moves aside."""
	make_room_for_site_provider()
	return frappe.get_doc(
		{
			"doctype": "Builder AI Provider",
			"from_site_config": 1,
			"litellm_provider": entry.litellm_provider,
			**SITE_PROVIDER,
		}
	)


def make_room_for_site_provider() -> None:
	"""Move another row off the Frappe provider's name and route prefix, keeping its key and models. Both
	are reserved (BuilderAIProvider.guard_reserved_name), but a row saved before they were could hold
	either, and the site config key could then never be connected."""
	name, prefix = SITE_PROVIDER["provider_name"], SITE_PROVIDER["route_prefix"]
	in_the_way = frappe.get_all(
		"Builder AI Provider",
		filters={"from_site_config": 0},
		or_filters={"name": name, "route_prefix": prefix},
		pluck="name",
	)
	for row in in_the_way:
		if row.lower() == name.lower():
			row = rename("Builder AI Provider", row, free_name(f"{name} (own key)"))
		doc = frappe.get_doc("Builder AI Provider", row)
		if doc.route_prefix == prefix:
			move_route_prefix(doc)
		logger.warning(f"moved the provider {row} out of the way of the site config key's")


def free_name(base: str) -> str:
	name, suffix = base, 2
	while frappe.db.exists("Builder AI Provider", name):
		name, suffix = f"{base} {suffix}", suffix + 1
	return name


def move_route_prefix(provider) -> None:
	"""Give the provider a route prefix of its own, from its name, and its models the names that go with it."""
	provider.route_prefix = None
	provider.save(ignore_permissions=True)
	models = frappe.get_all(
		"Builder AI Model", filters={"provider": provider.name}, fields=["name", "model_id"]
	)
	for model in models:
		rename("Builder AI Model", model.name, f"{provider.route_prefix}/{model.model_id}")
	ModelRegistry.clear_cache()


def rename(doctype: str, old: str, new: str) -> str:
	"""Rename a row, and every link to it, whoever's request runs the sync."""
	from frappe.model.rename_doc import rename_doc

	return rename_doc(doctype, old, new, force=True, ignore_permissions=True, show_alert=False)


def find_preset(preset_id: str) -> dict | None:
	return next((p for p in PRESETS if p["id"] == preset_id), None)


def preset_for(provider) -> dict | None:
	"""The preset a provider row was made from. A row with its own base URL is a custom gateway, and the
	Frappe provider is none: its key goes to the API site config names only, never to a preset's listing."""
	if provider.api_base or provider.from_site_config:
		return None
	return next((p for p in PRESETS if p.get("litellm_provider") == provider.litellm_provider), None)


def catalogs() -> set[str]:
	"""The models.dev providers discovery reads."""
	return {p["catalog"] for p in PRESETS if p.get("catalog")}


def public_preset(preset: dict) -> dict:
	"""The shape the connect menu renders: routing internals stay server-side, and a key never leaves."""
	return {
		"id": preset["id"],
		"name": preset["name"],
		"tagline": preset["tagline"],
		"key_url": preset.get("key_url", ""),
		"key_prefix": preset.get("key_prefix", ""),
		"oauth": preset.get("oauth", False),
		"custom": preset.get("custom", False),
		"connected": bool(stored_key(preset)),
	}


def connect(preset: dict, api_key: str = "") -> dict:
	"""Check the credential by listing models with it, save the provider, and discover its models.

	Listing spends no tokens and fails on a bad key the way a completion would, so
	a bad key fails here, before it is saved. A blank key re-checks the stored one."""
	from builder.ai.discovery import Discovery
	from builder.ai.listings import list_models

	api_key = (api_key or "").strip() or stored_key(preset)
	if not api_key:
		frappe.throw(_("Paste a key first"))
	try:
		listed = list_models(preset, api_key)
	except Exception as e:
		frappe.throw(readable_error(str(e))[0])
	provider = save_provider(preset, api_key)
	names = Discovery(provider).sync(listed)
	return {"provider": provider.name, "models": enabled_models(names)}


def save_provider(preset: dict, api_key: str):
	fields = {
		"provider_name": preset["name"],
		"route_prefix": preset["route_prefix"],
		"litellm_provider": preset["litellm_provider"],
		"api_base": None,
		"api_key": api_key,
		"enabled": 1,
	}
	if frappe.db.exists("Builder AI Provider", preset["name"]):
		doc = frappe.get_doc("Builder AI Provider", preset["name"])
		doc.update(fields)
		doc.save(ignore_permissions=True)
	else:
		doc = frappe.get_doc({"doctype": "Builder AI Provider", **fields}).insert(ignore_permissions=True)
	ModelRegistry.clear_cache()
	return doc


def enabled_models(names: list[str]) -> list[dict]:
	"""The switched-on rows among `names`, in that order, for the client to pick from."""
	rows = frappe.get_all(
		"Builder AI Model", filters={"name": ["in", names or [""]], "enabled": 1}, fields=["name", "label"]
	)
	labels = {row.name: row.label for row in rows}
	return [{"name": name, "label": labels[name]} for name in names if name in labels]


def stored_key(preset: dict) -> str:
	if preset["name"] and frappe.db.exists("Builder AI Provider", preset["name"]):
		provider = frappe.get_cached_doc("Builder AI Provider", preset["name"])
		# a row claiming the site config key is not a preset's: that key goes where site config says only
		return "" if provider.from_site_config else provider.resolved_key() or ""
	return ""


def add_model(provider: str, route_prefix: str, model_id: str, label: str, enabled: bool = True) -> None:
	"""Add the model, or switch an existing row on. Kept for the patches that predate discovery."""
	full_name = f"{route_prefix}/{model_id}"
	if frappe.db.exists("Builder AI Model", full_name):
		if enabled:
			frappe.db.set_value("Builder AI Model", full_name, "enabled", 1)
		return
	frappe.get_doc(
		{
			"doctype": "Builder AI Model",
			"provider": provider,
			"model_id": model_id,
			"label": label,
			"enabled": int(enabled),
		}
	).insert(ignore_permissions=True)


def readable_error(raw: str) -> tuple[str, str]:
	"""Provider errors arrive as a wall of JSON. Say what to actually do about it,
	and how much it matters: "warn" means the credentials are fine and something
	else is in the way (credit, a rate limit), "error" that it cannot work as entered."""
	from builder.ai.site_key import redact

	raw = redact(raw)
	low = raw.lower()
	if "authentication" in low or ("invalid" in low and "key" in low) or "401" in low or "403" in low:
		return (
			_("That key was rejected. Check you copied all of it, and that it hasn't been revoked."),
			"error",
		)
	if "credit" in low or "quota" in low or "billing" in low or "429" in low:
		return (
			_("The key is valid, but the account has no credit or is rate limited right now."),
			"warn",
		)
	if "not found" in low or "404" in low or "does not exist" in low:
		return (_("The key is valid, but that model isn't available on this account."), "warn")
	if "connection" in low or "timeout" in low or "refused" in low:
		return (_("Couldn't reach the server. Check the address is right and that it's running."), "error")
	return (raw[:300], "error")
