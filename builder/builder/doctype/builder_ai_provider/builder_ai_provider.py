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
		"""This provider's key, or None to fall back to the caller's."""
		return self.get_password("api_key", raise_exception=False)

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
