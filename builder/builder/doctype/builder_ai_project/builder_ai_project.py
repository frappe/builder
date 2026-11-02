from frappe.model.document import Document


class BuilderAIProject(Document):
	def validate(self):
		from builder.ai.projects import validate_project

		validate_project(self)
