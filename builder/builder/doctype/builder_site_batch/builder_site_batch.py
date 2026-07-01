# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from frappe.model.document import Document


class BuilderSiteBatch(Document):
	"""Tracks one AI multi-page site generation run: the architect session, the page
	manifest, and per-page progress. It is the durable, queryable source of truth the
	review screen reads (realtime events are just the live nudge). Progress counters are
	bumped with atomic SQL increments from parallel sub-agents — never read-modify-write."""

	pass
