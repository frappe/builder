"""Everything a connected provider serves, for adding a model by hand.

Discovery keeps the picker to the frontier; this is the way past it, for a model
the policy leaves out, like an open-weights one. A model added here is the
user's own: discovery never switches it off.
"""

import frappe
from frappe import _

from builder.ai.discovery import Discovery
from builder.ai.listings import list_models
from builder.ai.models import NON_CHAT_MARKERS, GatewayListing, ModelRegistry, fetch_listing


class ProviderCatalog:
	def __init__(self, provider):
		self.provider = provider
		self.discovery = Discovery(provider)

	def offered(self) -> list[dict]:
		"""What Bob could drive on this provider and isn't offering yet, newest first."""
		enabled = set(
			frappe.get_all(
				"Builder AI Model", filters={"provider": self.provider.name, "enabled": 1}, pluck="model_id"
			)
		)
		models = [m for m in self.models() if m["id"] not in enabled]
		return sorted(models, key=lambda m: m.get("released") or "", reverse=True)

	def add(self, model_id: str) -> dict:
		"""Switch the model on as the user's own; it must be one the provider serves."""
		model = next((m for m in self.models() if m["id"] == model_id), None)
		if not model:
			frappe.throw(_("{0} doesn't serve {1}").format(self.provider.name, model_id))
		name = f"{self.provider.route_prefix}/{model_id}"
		if frappe.db.exists("Builder AI Model", name):
			doc = frappe.get_doc("Builder AI Model", name)
			doc.update({"enabled": 1, "discovered": 0})
			doc.save(ignore_permissions=True)
		else:
			doc = frappe.get_doc(
				{
					"doctype": "Builder AI Model",
					"provider": self.provider.name,
					"model_id": model_id,
					"label": model["label"],
					"max_tokens": model.get("context") or None,
					"supports_vision": int("image" in (model.get("input") or [])),
					"enabled": 1,
				}
			).insert(ignore_permissions=True)
		ModelRegistry.clear_cache()
		return {"name": doc.name, "label": doc.label}

	def models(self) -> list[dict]:
		"""Every chat model the provider serves. Where models.dev describes them, only
		those that call tools: Bob does all its work through tools."""
		if self.provider.api_base:
			return [{"id": i, "label": i.rsplit("/", 1)[-1]} for i in self.gateway_ids()]
		if not self.discovery.preset:
			return []
		listed = list_models(self.discovery.preset, self.discovery.credential())
		return [
			m
			for m in self.discovery.candidates(listed)
			if m.get("tools") and "text" in (m.get("output") or ["text"])
		]

	def gateway_ids(self) -> list[str]:
		listed = fetch_listing(GatewayListing(self.provider).request())
		if isinstance(listed, Exception):
			raise listed
		return [i for i in listed if not any(m in i.lower() for m in NON_CHAT_MARKERS)]
