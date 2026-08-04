# Copyright (c) 2026, Frappe Technologies Pvt Ltd and contributors
# For license information, please see license.txt

"""Seed the shipped provider/model shortlist into Builder AI Provider and
Builder AI Model.

Only ever creates what is missing, so a site that has edited prices, disabled a
model or added its own keeps them. A patch runs once per site, so a row deleted
afterwards stays deleted.
"""

import frappe

PROVIDERS = [
	{
		"provider_name": "OpenRouter",
		"route_prefix": "openrouter",
		"litellm_provider": "openrouter",
		"api_base": None,
	},
	{
		# opencode.ai fronts two OpenAI-compatible gateways with native tool calling.
		# Cloudflare rejects default httpx/urllib agents (error 1010), hence the UA.
		"provider_name": "OpenCode Zen",
		"route_prefix": "opencode",
		"litellm_provider": "openai",
		"api_base": "https://opencode.ai/zen/v1",
		"extra_headers": '{"User-Agent": "opencode/1.18.3"}',
	},
	{
		"provider_name": "OpenCode Go",
		"route_prefix": "opencode-go",
		"litellm_provider": "openai",
		"api_base": "https://opencode.ai/zen/go/v1",
		"extra_headers": '{"User-Agent": "opencode/1.18.3"}',
	},
]

DEFAULT_MODEL = "openrouter/anthropic/claude-sonnet-5"
SIMPLE_MODEL = "openrouter/google/gemini-3.5-flash"

# Moonshot rejects any temperature but 1 with a 400.
TEMPERATURE_OVERRIDES = {"opencode-go/kimi-k2.7-code": 1.0, "opencode-go/kimi-k2.6": 1.0}

MODELS = [
	{
		"provider": "OpenRouter",
		"model_id": "anthropic/claude-sonnet-5",
		"label": "Claude Sonnet 5",
		"max_tokens": 1000000,
		"input_price": 2.0,
		"output_price": 10.0,
		"supports_vision": 1,
	},
	{
		"provider": "OpenRouter",
		"model_id": "anthropic/claude-opus-4.8",
		"label": "Claude Opus 4.8",
		"max_tokens": 1000000,
		"input_price": 5.0,
		"output_price": 25.0,
		"supports_vision": 1,
	},
	{
		"provider": "OpenRouter",
		"model_id": "anthropic/claude-fable-5",
		"label": "Claude Fable 5",
		"max_tokens": 1000000,
		"input_price": 10.0,
		"output_price": 50.0,
		"supports_vision": 1,
	},
	{
		"provider": "OpenRouter",
		"model_id": "openai/gpt-5.5",
		"label": "GPT-5.5",
		"max_tokens": 1050000,
		"input_price": 5.0,
		"output_price": 30.0,
		"supports_vision": 1,
	},
	{
		"provider": "OpenRouter",
		"model_id": "google/gemini-3.1-pro-preview",
		"label": "Gemini 3.1 Pro",
		"max_tokens": 1048576,
		"input_price": 2.0,
		"output_price": 12.0,
		"supports_vision": 1,
	},
	{
		"provider": "OpenRouter",
		"model_id": "google/gemini-3.5-flash",
		"label": "Gemini 3.5 Flash",
		"max_tokens": 1048576,
		"input_price": 1.5,
		"output_price": 9.0,
		"supports_vision": 1,
	},
	{
		"provider": "OpenCode Go",
		"model_id": "kimi-k2.7-code",
		"label": "Kimi K2.7 Code (OpenCode Go)",
		"max_tokens": 256000,
		"input_price": 0.95,
		"output_price": 4.0,
		"supports_vision": 0,
	},
	{
		"provider": "OpenCode Go",
		"model_id": "kimi-k2.6",
		"label": "Kimi K2.6 (OpenCode Go)",
		"max_tokens": 256000,
		"input_price": 0.95,
		"output_price": 4.0,
		"supports_vision": 0,
	},
	{
		"provider": "OpenCode Zen",
		"model_id": "nemotron-3-ultra-free",
		"label": "Nemotron 3 Ultra (OpenCode, Free)",
		"max_tokens": 1000000,
		"input_price": 0.0,
		"output_price": 0.0,
		"supports_vision": 0,
	},
	{
		"provider": "OpenCode Zen",
		"model_id": "deepseek-v4-flash-free",
		"label": "DeepSeek V4 Flash (OpenCode, Free)",
		"max_tokens": 200000,
		"input_price": 0.0,
		"output_price": 0.0,
		"supports_vision": 0,
	},
	{
		"provider": "OpenCode Zen",
		"model_id": "north-mini-code-free",
		"label": "North Mini Code (OpenCode, Free)",
		"max_tokens": 256000,
		"input_price": 0.0,
		"output_price": 0.0,
		"supports_vision": 0,
	},
	{
		"provider": "OpenRouter",
		"model_id": "nvidia/nemotron-3-ultra-550b-a55b:free",
		"label": "Nemotron 3 Ultra (Free)",
		"max_tokens": 1000000,
		"input_price": 0.0,
		"output_price": 0.0,
		"supports_vision": 0,
	},
]


def execute():
	for spec in PROVIDERS:
		create_provider(spec)
	for spec in MODELS:
		create_model(spec)


def create_provider(spec: dict) -> None:
	if frappe.db.exists("Builder AI Provider", spec["provider_name"]):
		return
	# Keys are moved onto providers by move_ai_keys_to_providers, which runs next.
	frappe.get_doc({"doctype": "Builder AI Provider", "enabled": 1, **spec}).insert(ignore_permissions=True)


def create_model(spec: dict) -> None:
	prefix = frappe.db.get_value("Builder AI Provider", spec["provider"], "route_prefix")
	name = f"{prefix}/{spec['model_id']}"
	if frappe.db.exists("Builder AI Model", name):
		return
	frappe.get_doc(
		{
			"doctype": "Builder AI Model",
			"enabled": 1,
			"is_default": int(name == DEFAULT_MODEL),
			"is_simple": int(name == SIMPLE_MODEL),
			"temperature": TEMPERATURE_OVERRIDES.get(name),
			**spec,
		}
	).insert(ignore_permissions=True)
