# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from frappe.model.document import Document


class BuilderAIBatchTask(Document):
	"""One sub-agent task in a Builder AI Batch fan-out: an independent brief run by a
	headless AgentRunner, optionally targeting a page, with its own session and status."""

	pass
