"""The provider catalogue the setup flow offers.

Adding a provider by hand means knowing its route prefix, its litellm name, its
api_base and which of its models are worth enabling — none of which a user
should have to look up to get started. Each preset carries that, plus where the
key comes from and a shortlist of models to switch on.

A preset is only a starting point: everything it creates is an ordinary Builder
AI Provider / Builder AI Model row, editable afterwards like any other.
"""

import frappe
from frappe import _

from builder.ai.models import ModelRegistry

PRESETS = [
	{
		"id": "openrouter",
		"name": "OpenRouter",
		"tagline": "One key, every major model",
		"blurb": "Claude, GPT, Gemini and hundreds more behind a single key. The easiest way to start, and the only one where you can switch model without a new account.",
		"route_prefix": "openrouter",
		"litellm_provider": "openrouter",
		"api_base": None,
		"key_url": "https://openrouter.ai/keys",
		"key_prefix": "sk-or-",
		"key_steps": [
			"Sign in at openrouter.ai",
			"Open Keys and create a new key",
			"Add a little credit — most pages cost a few cents",
		],
		"models": [
			("anthropic/claude-sonnet-5", "Claude Sonnet 5", "Best all-rounder for building pages", True),
			("openai/gpt-5.6-luna", "GPT-5.6 Luna", "Fastest and cheapest of the good ones", True),
			("openai/gpt-5.6-terra", "GPT-5.6 Terra", "Frontier tier from OpenAI", False),
			("google/gemini-3.6-flash", "Gemini 3.6 Flash", "Google's latest, fast", False),
			("nvidia/nemotron-3-ultra-550b-a55b:free", "Nemotron 3 Ultra", "Free, no credit needed", False),
		],
	},
	{
		"id": "anthropic",
		"name": "Anthropic",
		"tagline": "Claude, direct",
		"blurb": "Straight to Anthropic with your own account. Claude is the strongest model for page design, and this is the cheapest way to reach it if you already have credit.",
		"route_prefix": "anthropic",
		"litellm_provider": "anthropic",
		"api_base": None,
		"key_url": "https://console.anthropic.com/settings/keys",
		"key_prefix": "sk-ant-",
		"key_steps": [
			"Sign in to the Anthropic Console",
			"Open Settings, then API keys",
			"Create a key and copy it",
		],
		"models": [
			("claude-sonnet-5", "Claude Sonnet 5", "Best all-rounder for building pages", True),
			("claude-haiku-4.5", "Claude Haiku 4.5", "Fastest and cheapest Claude", False),
		],
	},
	{
		"id": "openai",
		"name": "OpenAI",
		"tagline": "GPT, direct",
		"blurb": "Straight to OpenAI with your own account.",
		"route_prefix": "openai",
		"litellm_provider": "openai",
		"api_base": None,
		"key_url": "https://platform.openai.com/api-keys",
		"key_prefix": "sk-",
		"key_steps": [
			"Sign in at platform.openai.com",
			"Open API keys and create a secret key",
			"Copy it before closing the dialog",
		],
		"models": [
			("gpt-5.6-terra", "GPT-5.6 Terra", "Frontier tier, best value of these", True),
			("gpt-5.6-luna", "GPT-5.6 Luna", "Fastest and cheapest", False),
			("gpt-5.6-sol", "GPT-5.6 Sol", "Top of the 5.6 line", False),
			("gpt-5.5", "GPT-5.5", "Previous generation", False),
		],
	},
	{
		"id": "codex",
		"name": "ChatGPT",
		"tagline": "Included with ChatGPT Plus/Pro",
		"blurb": "OpenAI's models through the ChatGPT subscription you already pay for. No API credits or per-token billing, just sign in with your ChatGPT account.",
		"route_prefix": "codex",
		"litellm_provider": "codex",
		"api_base": None,
		"oauth": True,
		"key_url": "",
		"key_prefix": "",
		"key_steps": [
			"Click Sign in with ChatGPT and approve in the tab that opens",
			"You'll be connected automatically when the sign-in completes",
		],
		"models": [
			("gpt-5.6-terra", "GPT-5.6 Terra", "Frontier tier, best for building", True),
			("gpt-5.6-luna", "GPT-5.6 Luna", "Fastest of the 5.6 line", False),
			("gpt-5.3-codex", "GPT-5.3 Codex", "Code-tuned, largest context", False),
			("gpt-5.5", "GPT-5.5", "Previous generation", False),
		],
	},
	{
		"id": "google",
		"name": "Google Gemini",
		"tagline": "Gemini, direct",
		"blurb": "Straight to Google AI Studio. Generous free tier to try things out.",
		"route_prefix": "gemini",
		"litellm_provider": "gemini",
		"api_base": None,
		"key_url": "https://aistudio.google.com/apikey",
		"key_prefix": "",
		"key_steps": [
			"Open Google AI Studio",
			"Click Get API key",
			"Create a key in a new or existing project",
		],
		"models": [
			("gemini-3.6-flash", "Gemini 3.6 Flash", "Latest, fast, good value", True),
			("gemini-3.1-pro-preview", "Gemini 3.1 Pro", "Strongest Gemini for building", False),
			("gemini-3.1-flash-lite", "Gemini 3.1 Flash Lite", "Cheapest of these", False),
		],
	},
	{
		"id": "custom",
		"name": "",  # the user names it
		"tagline": "Any OpenAI-compatible endpoint",
		"blurb": "A gateway of your own: an internal proxy, a hosted endpoint not listed here, or Ollama / LM Studio / vLLM on your own machine. You name it and point it at a base URL.",
		"route_prefix": "",  # slugged from the name by the provider doctype
		"litellm_provider": "",  # derived from whether an api_base is set
		"api_base": "",
		"custom": True,
		"key_url": "",
		"key_prefix": "",
		"key_steps": [],
		"models": [],
	},
]


def find_preset(preset_id: str) -> dict | None:
	return next((p for p in PRESETS if p["id"] == preset_id), None)


def public_preset(preset: dict) -> dict:
	"""The shape the setup flow renders — routing internals stay server-side."""
	custom = preset.get("custom", False)
	existing = preset["name"] and frappe.db.exists("Builder AI Provider", preset["name"])
	return {
		# A stored key is never sent back, so the flow has to be told one exists —
		# otherwise re-entering setup looks identical to having no key at all.
		"has_key": bool(existing and frappe.get_cached_doc("Builder AI Provider", existing).resolved_key()),
		"id": preset["id"],
		"name": preset["name"],
		"tagline": preset["tagline"],
		"blurb": preset["blurb"],
		"key_url": preset["key_url"],
		"key_prefix": preset["key_prefix"],
		"key_steps": preset["key_steps"],
		"api_base": preset["api_base"],
		"custom": custom,
		# OAuth providers sign in with a browser round-trip instead of a key.
		"oauth": preset.get("oauth", False),
		# A custom endpoint is named and addressed by the user; a known one only
		# ever needs the key, and often already exists from a previous setup.
		"needs_name": custom,
		"needs_api_base": custom,
		"configured": bool(existing),
		"models": [
			{"model_id": mid, "label": label, "note": note, "recommended": rec}
			for mid, label, note, rec in preset["models"]
		],
	}


def install_preset(
	preset: dict, api_key: str, api_base: str, model_ids: list[str], provider_name: str = ""
) -> str:
	"""Create (or update) the provider and switch on the chosen models.

	route_prefix and litellm_provider are deliberately left unset for a custom
	endpoint: Builder AI Provider slugs the prefix from the name and infers the
	litellm side from whether a base URL is present, so there is one place that
	decides routing rather than two that can disagree."""
	name = (provider_name or preset["name"]).strip()
	if not name:
		frappe.throw(_("Give this provider a name"))
	fields = {
		"provider_name": name,
		"api_base": (api_base or preset["api_base"] or "") or None,
		"enabled": 1,
	}
	if preset["route_prefix"]:
		fields["route_prefix"] = preset["route_prefix"]
	if preset["litellm_provider"]:
		fields["litellm_provider"] = preset["litellm_provider"]
	if api_key:
		fields["api_key"] = api_key

	if frappe.db.exists("Builder AI Provider", name):
		doc = frappe.get_doc("Builder AI Provider", name)
		doc.update(fields)
		doc.save(ignore_permissions=True)
	else:
		doc = frappe.get_doc({"doctype": "Builder AI Provider", **fields}).insert(ignore_permissions=True)

	known = {m[0]: m[1] for m in preset["models"]}
	for model_id in model_ids:
		add_model(doc.name, doc.route_prefix, model_id, known.get(model_id, model_id))
	ModelRegistry.clear_cache()
	return doc.name


def add_model(provider: str, route_prefix: str, model_id: str, label: str) -> None:
	full_name = f"{route_prefix}/{model_id}"
	if frappe.db.exists("Builder AI Model", full_name):
		frappe.db.set_value("Builder AI Model", full_name, "enabled", 1)
		return
	frappe.get_doc(
		{
			"doctype": "Builder AI Model",
			"provider": provider,
			"model_id": model_id,
			"label": label,
			"enabled": 1,
		}
	).insert(ignore_permissions=True)


def verify_key(preset: dict, api_key: str, api_base: str, model_id: str) -> dict:
	"""Make the smallest real call this provider will accept, so a key that looks
	right but is revoked, out of credit or scoped wrong fails HERE rather than
	three screens later on the user's first build."""
	if preset["id"] == "codex":
		from builder.ai import codex

		return codex.verify_credential(api_key)
	import litellm

	base = api_base or preset["api_base"]
	# Mirrors BuilderAIProvider.derive_routing, so the test call routes exactly the
	# way the saved provider will.
	llm_provider = preset["litellm_provider"] or ("openai" if base else "openrouter")
	qualified = f"{llm_provider}/{model_id}"
	overrides = {"api_base": base} if base else {}
	try:
		litellm.completion(
			model=qualified,
			**overrides,
			messages=[{"role": "user", "content": "Reply with OK"}],
			max_tokens=5,
			api_key=api_key or "not-needed",
		)
		return {"success": True, "severity": "ok", "message": _("Connected")}
	except Exception as e:
		message, severity = readable_error(str(e))
		return {"success": False, "severity": severity, "message": message}


def readable_error(raw: str) -> tuple[str, str]:
	"""Provider errors arrive as a wall of JSON. Say what to actually do about it,
	and how much it matters.

	"warn" means the credentials are FINE and something else is in the way — an
	empty balance, a rate limit, a model this account can't see. Setup should not
	dead-end on those: the key is right, and topping up an account is a thing you
	go and do elsewhere, later. Only "error" means it cannot work as entered."""
	low = raw.lower()
	if "authentication" in low or ("invalid" in low and "key" in low) or "401" in low:
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
