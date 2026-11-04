# Copyright (c) 2026, Frappe Technologies Pvt Ltd and contributors
# For license information, please see license.txt

"""Hand the shipped model rows to discovery.

Before discovery, every model on a known provider (OpenRouter, Anthropic, OpenAI,
ChatGPT, Gemini) came from a shortlist in the code, seeded or upgraded by a
patch. Marking those rows discovered lets the first sync switch on the current
frontier and retire what it has replaced. Rows behind a custom gateway are left
as they are: a gateway lists its own models.

The sync itself runs in the background after migrate, since it needs the network.
"""

import frappe


def execute():
	known = frappe.get_all(
		"Builder AI Provider",
		filters={"api_base": ["is", "not set"], "litellm_provider": ["is", "set"]},
		pluck="name",
	)
	if not known:
		return
	frappe.db.set_value("Builder AI Model", {"provider": ["in", known]}, "discovered", 1)
	frappe.enqueue(
		"builder.ai.discovery.sync_stale_providers",
		queue="short",
		job_id="builder_ai_discovery",
		deduplicate=True,
		enqueue_after_commit=True,
	)
