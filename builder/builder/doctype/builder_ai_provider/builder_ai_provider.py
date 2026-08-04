# Copyright (c) 2026, Frappe Technologies Pvt Ltd and contributors
# For license information, please see license.txt

import json

import frappe
from frappe import _
from frappe.model.document import Document


class BuilderAIProvider(Document):
	def validate(self):
		self.route_prefix = (self.route_prefix or "").strip().strip("/")
		if not self.route_prefix:
			frappe.throw(_("Route Prefix is required"))
		self.validate_json("extra_headers")
		self.validate_json("extra_body")

	def validate_json(self, fieldname: str) -> None:
		raw = (self.get(fieldname) or "").strip()
		if not raw:
			return
		try:
			parsed = json.loads(raw)
		except ValueError as e:
			frappe.throw(_("{0} is not valid JSON: {1}").format(_(self.meta.get_label(fieldname)), str(e)))
		if not isinstance(parsed, dict):
			frappe.throw(_("{0} must be a JSON object").format(_(self.meta.get_label(fieldname))))

	def on_update(self):
		clear_registry_cache()

	def on_trash(self):
		if models := frappe.get_all("Builder AI Model", filters={"provider": self.name}, pluck="name"):
			frappe.throw(
				_("{0} models still use this provider: {1}").format(len(models), ", ".join(models[:5]))
			)
		clear_registry_cache()

	def parsed(self, fieldname: str) -> dict:
		raw = (self.get(fieldname) or "").strip()
		return json.loads(raw) if raw else {}

	def resolved_key(self) -> str | None:
		return self.get_password("api_key", raise_exception=False)


def clear_registry_cache() -> None:
	from builder.ai.models import ModelRegistry

	ModelRegistry.clear_cache()
