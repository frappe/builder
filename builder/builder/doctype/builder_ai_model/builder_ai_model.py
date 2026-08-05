# Copyright (c) 2026, Frappe Technologies Pvt Ltd and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document


class BuilderAIModel(Document):
	def autoname(self):
		self.name = self.qualified_name()

	def qualified_name(self) -> str:
		"""`<route prefix>/<model id>`, the name the agent and every stored session
		use. Keeping it as the docname means a session's selected_model is a link
		to this row, not a duplicated string."""
		prefix = frappe.db.get_value("Builder AI Provider", self.provider, "route_prefix")
		return f"{prefix}/{(self.model_id or '').strip().strip('/')}"

	def validate(self):
		self.model_id = (self.model_id or "").strip().strip("/")
		if not self.model_id:
			frappe.throw(_("Model ID is required"))
		self.label = (self.label or "").strip() or self.model_id
		self.detect_metadata()
		if not self.is_new() and self.name != self.qualified_name():
			frappe.rename_doc(self.doctype, self.name, self.qualified_name(), force=True)
		self.enforce_single_flag("is_default", _("default model"))

	def detect_metadata(self) -> None:
		"""Fill in what can be looked up — context window, prices, vision — so adding
		a model only asks for its id. OpenRouter answers for its own models, litellm's
		model map for the rest. Anything already filled in is left alone, so an edit
		(or a model nobody knows) stands."""
		from builder.ai.models import lookup_metadata

		found = lookup_metadata(self.qualified_name(), self.model_id)
		if not found:
			return
		for field, key in (
			("max_tokens", "max_tokens"),
			("input_price", "input_price"),
			("output_price", "output_price"),
			("cache_read_price", "cache_read_price"),
		):
			if not self.get(field) and found.get(key) is not None:
				self.set(field, found[key])
		if not self.supports_vision and found.get("vision"):
			self.supports_vision = 1

	def enforce_single_flag(self, fieldname: str, description: str) -> None:
		"""Only one model can be the default (or the lightweight one) — set the flag
		here and it clears everywhere else, rather than erroring and making the user
		go find the other row."""
		if not self.get(fieldname):
			return
		others = frappe.get_all(self.doctype, filters={fieldname: 1, "name": ["!=", self.name]}, pluck="name")
		for other in others:
			frappe.db.set_value(self.doctype, other, fieldname, 0)
		if others:
			frappe.msgprint(
				_("{0} is now the {1} (was {2})").format(self.label or self.name, description, others[0]),
				indicator="green",
				alert=True,
			)

	def on_update(self):
		self.clear_registry_cache()

	def on_trash(self):
		self.clear_registry_cache()

	def clear_registry_cache(self) -> None:
		from builder.ai.models import ModelRegistry

		ModelRegistry.clear_cache()
