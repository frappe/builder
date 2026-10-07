# Copyright (c) 2026, Frappe Technologies Pvt Ltd and contributors
# For license information, please see license.txt

"""Move a site's saved models onto the current shortlist.

Every enabled model Builder used to offer that is now superseded or a cheap tier
is switched off, and its successor on the same provider switched on. Rows are
disabled, not deleted: sessions link to them, and a site can turn one back on.
Models a site added itself, and anything behind a custom gateway, are left alone.
"""

import frappe

from builder.ai.models import ModelRegistry
from builder.ai.presets import PRESETS, add_model

# litellm provider -> retired model id -> its successor
SUCCESSORS = {
	"openrouter": {
		"anthropic/claude-sonnet-5": "anthropic/claude-sonnet-5.5",
		"openai/gpt-5.5": "openai/gpt-6.1-sol",
		"openai/gpt-5.6-luna": "openai/gpt-6.1-sol",
		"google/gemini-3.5-flash": "google/gemini-3.8-flash",
		"google/gemini-3.6-flash": "google/gemini-3.8-flash",
		"nvidia/nemotron-3-ultra-550b-a55b:free": "anthropic/claude-sonnet-5.5",
		"xiaomi/mimo-v2.5": "anthropic/claude-sonnet-5.5",
	},
	"anthropic": {
		"claude-sonnet-5": "claude-sonnet-5-5",
		"claude-haiku-4.5": "claude-sonnet-5-5",
	},
	"openai": {
		"gpt-5.5": "gpt-6.1-sol",
		"gpt-5.6-sol": "gpt-6.1-sol",
		"gpt-5.6-terra": "gpt-6.1-sol",
		"gpt-5.6-luna": "gpt-6.1-sol",
	},
	"codex": {
		"gpt-5.5": "gpt-6-luna",
		"gpt-5.6-luna": "gpt-6-luna",
		"gpt-5.3-codex": "gpt-6-luna",
	},
	"gemini": {
		"gemini-3.6-flash": "gemini-3.8-flash",
		"gemini-3.1-flash-lite": "gemini-3.8-flash",
	},
}


def execute():
	providers = frappe.get_all(
		"Builder AI Provider",
		filters={"litellm_provider": ["in", list(SUCCESSORS)], "api_base": ["is", "not set"]},
		fields=["name", "route_prefix", "litellm_provider"],
	)
	for provider in providers:
		upgrade_provider(provider)
	ModelRegistry.clear_cache()


def upgrade_provider(provider) -> None:
	successors = SUCCESSORS[provider.litellm_provider]
	retired = frappe.get_all(
		"Builder AI Model",
		filters={"provider": provider.name, "enabled": 1, "model_id": ["in", list(successors)]},
		fields=["name", "model_id", "creation"],
		order_by="creation asc",
	)
	for row in retired:
		successor = f"{provider.route_prefix}/{successors[row.model_id]}"
		# A successor the site switched off is a choice to keep the model it replaces
		if frappe.db.get_value("Builder AI Model", successor, "enabled") == 0:
			continue
		frappe.db.set_value("Builder AI Model", row.name, "enabled", 0)
		if not frappe.db.exists("Builder AI Model", successor):
			add_successor(provider, successors[row.model_id], row.creation)


def add_successor(provider, model_id: str, creation) -> None:
	add_model(provider.name, provider.route_prefix, model_id, label_for(provider.litellm_provider, model_id))
	# The picker and the agent default to the oldest model, so the successor takes the retired row's place
	frappe.db.set_value(
		"Builder AI Model", f"{provider.route_prefix}/{model_id}", "creation", creation, update_modified=False
	)


def label_for(litellm_provider: str, model_id: str) -> str:
	for preset in PRESETS:
		if preset["litellm_provider"] == litellm_provider:
			return next((m[1] for m in preset["models"] if m[0] == model_id), model_id)
	return model_id
