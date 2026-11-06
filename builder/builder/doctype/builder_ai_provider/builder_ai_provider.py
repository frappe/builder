# Copyright (c) 2026, Frappe Technologies Pvt Ltd and contributors
# For license information, please see license.txt

import re

import frappe
from frappe import _
from frappe.model.document import Document


class BuilderAIProvider(Document):
	def validate(self):
		self.derive_routing()

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

	@property
	def credits_url(self) -> str:
		"""Where the gateway reports its balance."""
		if self.from_site_config:
			from builder.ai.presets import get_credits_url

			return get_credits_url(self.api_base)
		return f"{self.api_base.rstrip('/')}/credits"

	def on_update(self):
		clear_registry_cache()

	def on_trash(self):
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
