# Copyright (c) 2026, Frappe Technologies Pvt Ltd and contributors
# For license information, please see license.txt

"""Move the AI keys onto the providers that use them.

The OpenRouter key lived on Builder Settings and the OpenCode key in
site_config, from when those were the only two gateways. A provider now carries
its own key, so every key sits in the same place and a new gateway needs no
special case.

Builder Settings keeps its field as a fallback (builder.ai.api.resolve_api_key),
so a site that never migrated still works.
"""

import frappe


def execute():
	drop_interim_keys_table()
	move_key(
		"OpenRouter",
		frappe.get_single("Builder Settings").get_password("ai_api_key", raise_exception=False),
	)
	for provider in ("OpenCode Zen", "OpenCode Go"):
		move_key(provider, frappe.conf.get("zen_api_key"))


def move_key(provider: str, key: str | None) -> None:
	if not key or not frappe.db.exists("Builder AI Provider", provider):
		return
	doc = frappe.get_doc("Builder AI Provider", provider)
	if doc.resolved_key():
		return  # already carries its own key
	doc.api_key = key
	doc.save(ignore_permissions=True)


def drop_interim_keys_table() -> None:
	"""A multi-key child table shipped briefly between these two patches; a
	provider has one key. Only ever present on a dev site that migrated in that
	window."""
	if frappe.db.exists("DocType", "Builder AI Provider Key"):
		frappe.delete_doc("DocType", "Builder AI Provider Key", ignore_missing=True, force=True)
