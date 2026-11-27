# Copyright (c) 2026, Frappe Technologies Pvt Ltd and Contributors
# See license.txt

"""Stand-ins for what a hosting app answers through Builder's hooks, as frappe.page does on its own site.

`hosting_hooks(builder_can_serve_page=[refuse])` registers them for the length of a block; every other
hook resolves as the site has it.
"""

from contextlib import contextmanager
from unittest.mock import patch

import frappe


def refuse(page, path):
	return False


def refuse_every_request(page, path):
	"""Refuses only the question about every request, the one asked with no path"""
	return path is not None


def no_say(*args):
	return None


def isolate():
	return True


def refuse_template_syntax(doc, rendering):
	"""Refuses a page or component that carries Jinja, as frappe.page does on its own site; asked again,
	with rendering True, before a preview renders"""
	fields = ("blocks", "draft_blocks", "block", "head_html", "body_html", "page_data_script")
	if any("{{" in (doc.get(field) or "") for field in fields):
		return [f"{doc.name} carries template syntax"]
	return []


def page_tools():
	return ["read_page", "edit_page"]


def preview_tools():
	return ["preview_page"]


def search_tools():
	return ["run_python"]


def without_save_hooks():
	"""No installed app's doc_events, for a test of Builder's own save path whatever a host refuses on save.
	Frappe rebuilds an empty map from the hooks, so this one holds an empty entry."""
	return patch.object(frappe.local, "doc_events_hooks", {"*": {}}, create=True)


@contextmanager
def hosting_hooks(**hooks):
	"""Answer each named hook with the given functions, as if an installed app registered them."""
	get_hooks = frappe.get_hooks

	def patched(hook=None, *args, **kwargs):
		if hook in hooks:
			return [f"{__name__}.{function.__name__}" for function in hooks[hook]]
		return get_hooks(hook, *args, **kwargs)

	with patch("frappe.get_hooks", patched):
		yield
