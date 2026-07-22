# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from frappe.model.document import Document


class BuilderAIBatch(Document):
	"""Tracks one fan-out of parallel AI sub-agents: the parent chat session that
	spawned it, one child task row per sub-agent, and per-task progress. It is the
	durable, queryable source of truth the chat's task-group card reads (realtime
	events are just the live nudge). Progress counters are bumped with atomic SQL
	increments from parallel workers — never read-modify-write."""

	pass
