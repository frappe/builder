# Copyright (c) 2026, Frappe Technologies Pvt Ltd and contributors
# For license information, please see license.txt

from frappe.model.document import Document


class BuilderAIMemory(Document):
	def validate(self):
		from builder.ai.memory import validate

		validate(self)
