# Copyright (c) 2026, Frappe Technologies Pvt Ltd and contributors
# For license information, please see license.txt

import re

import frappe
from frappe import _
from frappe.model.document import Document


class BuilderAIProvider(Document):
	def validate(self):
		self.guard_site_config_row()
		self.derive_routing()

	def guard_site_config_row(self):
		"""Site config owns the Frappe provider (builder/ai/presets.py): only syncing it with site config
		changes it, and no other row can claim to be it. Administrator, from the bench, still can."""
		from builder.ai.presets import may_change_site_provider

		before = None if self.is_new() else self.get_doc_before_save()
		owned = self.from_site_config or (before and before.from_site_config)
		if owned and not may_change_site_provider():
			frappe.throw(
				_(
					"{0} comes with this site, so it can't be changed or removed. You can still connect providers of your own."
				).format(self.provider_name or self.name),
				frappe.PermissionError,
			)

	def derive_routing(self):
		"""Only the name and (for a custom endpoint) the API base are worth asking
		for. The prefix is a slug of the name, and a provider with a base URL is an
		OpenAI-compatible gateway by definition — both stay editable for the rare
		case that needs something else."""
		self.route_prefix = (self.route_prefix or "").strip().strip("/")
		if not self.route_prefix:
			self.route_prefix = self.unique_prefix(slugify(self.provider_name))
		if not self.litellm_provider:
			self.litellm_provider = "openai" if self.api_base else "openrouter"

	def unique_prefix(self, base: str) -> str:
		prefix, suffix = base, 2
		while frappe.db.exists("Builder AI Provider", {"route_prefix": prefix, "name": ["!=", self.name]}):
			prefix, suffix = f"{base}-{suffix}", suffix + 1
		return prefix

	def resolved_key(self) -> str | None:
		"""This provider's key, or None when it has none. Site config owns the Frappe provider's key.
		A cached config can miss a key that a fresh read just connected, so a miss reads the files."""
		if self.from_site_config:
			from builder.ai.presets import get_site_ai_key

			return (get_site_ai_key() or get_site_ai_key(fresh=True) or {}).get("api_key")
		return self.get_password("api_key", raise_exception=False)

	def base_url(self) -> str | None:
		"""Where this provider's API is. For the Frappe provider that is the gateway site config names,
		never the stored api_base, so an edited row cannot send the site's key anywhere else."""
		if self.from_site_config:
			from builder.ai.presets import site_gateway_base

			return site_gateway_base()
		return self.api_base

	@property
	def credits_url(self) -> str | None:
		"""Where the gateway reports its balance."""
		if self.from_site_config:
			from builder.ai.presets import get_credits_url, get_site_ai_key

			entry = get_site_ai_key() or get_site_ai_key(fresh=True)
			return get_credits_url(entry["gateway_url"]) if entry else None
		return f"{self.api_base.rstrip('/')}/credits"

	def before_rename(self, old, new, merge=False):
		self.guard_site_config_row()

	def on_update(self):
		clear_registry_cache()

	def on_trash(self):
		self.guard_site_config_row()
		if models := frappe.get_all("Builder AI Model", filters={"provider": self.name}, pluck="name"):
			frappe.throw(
				_("{0} models still use this provider: {1}").format(len(models), ", ".join(models[:5]))
			)
		clear_registry_cache()


def slugify(value: str) -> str:
	return re.sub(r"[^a-z0-9]+", "-", (value or "").strip().lower()).strip("-") or "provider"


def clear_registry_cache() -> None:
	from builder.ai.models import ModelRegistry

	ModelRegistry.clear_cache()
