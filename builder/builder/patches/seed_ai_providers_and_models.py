# Copyright (c) 2026, Frappe Technologies Pvt Ltd and contributors
# For license information, please see license.txt

"""Seed the shipped provider/model shortlist into Builder AI Provider and
Builder AI Model.

Only ever creates what is missing, so a site that has renamed, disabled or added
models keeps them. A patch runs once per site, so a row deleted afterwards stays
deleted. The chat's picker starts on the first model here.
"""

import frappe

PROVIDERS = [
	{
		"provider_name": "OpenRouter",
		"route_prefix": "openrouter",
		"litellm_provider": "openrouter",
		"api_base": None,
	},
]

MODELS = [
	{
		"provider": "OpenRouter",
		"model_id": "anthropic/claude-sonnet-5",
		"label": "Claude Sonnet 5",
		"max_tokens": 1000000,
		"supports_vision": 1,
	},
	{
		"provider": "OpenRouter",
		"model_id": "openai/gpt-5.5",
		"label": "GPT-5.5",
		"max_tokens": 1050000,
		"supports_vision": 1,
	},
	{
		"provider": "OpenRouter",
		"model_id": "google/gemini-3.1-pro-preview",
		"label": "Gemini 3.1 Pro",
		"max_tokens": 1048576,
		"supports_vision": 1,
	},
	{
		"provider": "OpenRouter",
		"model_id": "google/gemini-3.5-flash",
		"label": "Gemini 3.5 Flash",
		"max_tokens": 1048576,
		"supports_vision": 1,
	},
	{
		"provider": "OpenRouter",
		"model_id": "openai/gpt-5.6-terra",
		"label": "GPT-5.6 Terra",
		"max_tokens": 1050000,
		"supports_vision": 1,
	},
	{
		"provider": "OpenRouter",
		"model_id": "openai/gpt-5.6-luna",
		"label": "GPT-5.6 Luna",
		"max_tokens": 1050000,
		"supports_vision": 1,
	},
	{
		"provider": "OpenRouter",
		"model_id": "xiaomi/mimo-v2.5",
		"label": "MiMo V2.5",
		"max_tokens": 1050000,
		"supports_vision": 1,
	},
	{
		"provider": "OpenRouter",
		"model_id": "nvidia/nemotron-3-ultra-550b-a55b:free",
		"label": "Nemotron 3 Ultra (Free)",
		"max_tokens": 1000000,
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
			**spec,
		}
	).insert(ignore_permissions=True)
