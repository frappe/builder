"""The providers Bob can connect to, and connecting one.

A preset carries what connecting needs and nobody should have to look up: how
the provider signs in, where a key comes from, how litellm routes it, and where
its models are listed and described. It names no models. Discovery
(builder/ai/discovery.py) finds those once the provider is connected, so a model
released tomorrow shows up without a change here.

Everything a preset creates is an ordinary Builder AI Provider row.
"""

import frappe
from frappe import _

from builder.ai.models import ModelRegistry

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


def find_preset(preset_id: str) -> dict | None:
	return next((p for p in PRESETS if p["id"] == preset_id), None)


def preset_for(provider) -> dict | None:
	"""The preset a provider row was made from. A row with its own base URL is a custom gateway."""
	if provider.api_base:
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
		return frappe.get_cached_doc("Builder AI Provider", preset["name"]).resolved_key() or ""
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
