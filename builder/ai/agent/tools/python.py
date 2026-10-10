"""run_python — the general read primitive.

The named read tools answer the common questions; this answers the rest. One
sandboxed snippet can count, aggregate, and cross-reference anything on the
site, so the agent orients itself on demand instead of depending on pre-baked
context or a bespoke tool per question. The namespace is Frappe's render-safe
subset (what Jinja templates get) rather than the server-script one, minus the
query builder, raw SQL, outbound requests and template rendering, so there is
nothing to enqueue, mail, call, request, insert or delete with. Every read
answers with the session user's own permissions, and documents come back as
plain dicts, since a live Document's save() runs hooks that can commit. A
savepoint rollback still erases anything a snippet manages to write.
"""

import frappe

from builder.ai.agent.registry import Tool

RESULT_LIMIT = 6000
SAVEPOINT = "builder_ai_run_python"

# Still in the render-safe set: qb and db.sql read any table (auth internals
# included), make_get_request can carry data off-site in its URL,
# render_template and get_last_doc read without permission checks, and
# log_error and response write.
STRIPPED_FRAPPE_KEYS = ("qb", "make_get_request", "render_template", "get_last_doc", "log_error", "response")
STRIPPED_DB_METHODS = ("sql",)

# get_list switches that widen a read past the session user's own permissions.
UNSCOPING_LIST_ARGS = ("ignore_permissions", "ignore_user_permissions", "user")


def sandbox_globals() -> dict:
	from frappe.utils.safe_exec import render_safe_globals

	safe = render_safe_globals()  # built per call, so rebinding keys touches only this copy
	fr = safe["frappe"]
	for key in STRIPPED_FRAPPE_KEYS:
		fr.pop(key, None)
	for method in STRIPPED_DB_METHODS:
		fr["db"].pop(method, None)
	scope_reads_to_user(fr)
	hide_exec_only_globals(safe)
	return safe


def scope_reads_to_user(fr) -> None:
	"""Render-safe reads skip permission checks. Every read here answers with the
	session user's OWN permissions: Bob sees exactly what the person driving it
	could open in Desk."""
	db = fr["db"]
	fr["get_all"] = fr["get_list"] = db["get_all"] = db["get_list"] = user_get_list
	fr["get_doc"] = fr["get_cached_doc"] = guarded_get_doc
	for method in ("get_value", "get_single_value", "exists", "count"):
		db[method] = read_guarded(getattr(frappe.db, method))


def hide_exec_only_globals(safe: dict) -> None:
	"""safe_exec lays these globals over its full server-script namespace, so a
	top-level name left out here (FrappeClient, run_script) would still resolve."""
	from frappe.utils.safe_exec import get_safe_globals

	for key in get_safe_globals().keys() - safe.keys():
		safe[key] = None


def user_get_list(doctype, fields=None, filters=None, **kwargs):
	for key in UNSCOPING_LIST_ARGS:
		kwargs.pop(key, None)
	return frappe.get_list(doctype, fields=fields, filters=filters, **kwargs)


def guarded_get_doc(*args, **kwargs):
	from frappe.utils.safe_exec import SafeDoc

	doc = frappe.get_doc(*args, **kwargs)
	if not doc.has_permission():
		frappe.throw(f"No permission to read {doc.doctype}", frappe.PermissionError)
	doc.apply_fieldlevel_read_permissions()
	return SafeDoc(doc.as_dict())


def read_guarded(fn):
	def checked(doctype, *args, **kwargs):
		frappe.has_permission(doctype, throw=True)
		return fn(doctype, *args, **kwargs)

	return checked


def run_python(ctx, args: dict) -> str:
	from frappe.utils.safe_exec import is_safe_exec_enabled, safe_exec

	script = (args.get("script") or "").strip()
	if not script:
		return "FAILED: pass `script` — Python that assigns the answer to `result`."
	if not is_safe_exec_enabled():
		return "FAILED: the script sandbox is disabled on this bench — use the other read tools."
	_locals = {"page_id": ctx.page_id, "result": None}
	frappe.db.savepoint(SAVEPOINT)
	try:
		# Audited dynamic execution, the point of this tool. Read-only namespace
		# (sandbox_globals), commits blocked, and the savepoint rollback below
		# discards anything a snippet wrote.
		safe_exec(script, sandbox_globals(), _locals, restrict_commit_rollback=True)  # nosemgrep
	except Exception as e:
		return f"FAILED: {type(e).__name__}: {e}"
	finally:
		# This tool READS. A write that slipped past the sandbox vanishes here.
		frappe.db.rollback(save_point=SAVEPOINT)
	result = _locals.get("result")
	if result is None:
		return "Ran, but `result` was never assigned — set result = <the answer> and run again."
	out = result if isinstance(result, str) else frappe.as_json(result)
	if len(out) > RESULT_LIMIT:
		out = out[:RESULT_LIMIT] + "… (truncated — narrow the query)"
	return out


run_python_tool = Tool(
	name="run_python",
	side="server",
	handler=run_python,
	description=(
		"Figure out ANYTHING about this site with a short READ-ONLY Python snippet, run "
		"server-side in the script sandbox. Assign the answer to `result`. This is your "
		"general fallback whenever no other tool answers directly: counts and aggregates, "
		"which page owns a route, the site's own URL (frappe.utils.get_url()), any setting "
		"or record, cross-doctype questions. Available: frappe.get_all/get_list, "
		"frappe.get_doc (returns a read-only dict of the record), frappe.get_meta, "
		"frappe.db.get_value/get_single_value/count/exists, frappe.utils date/format "
		"helpers, frappe.utils.get_url, frappe.session.user, json, and `page_id` (the open "
		"page). No imports, raw SQL, query builder, network requests, emails or background "
		"jobs, and documents cannot be saved; reads answer with the current user's own "
		"permissions. Orient yourself with it instead of guessing or asking the user."
	),
	parameters={
		"type": "object",
		"properties": {
			"script": {
				"type": "string",
				"description": "Python statements; assign the answer to `result`.",
			},
		},
		"required": ["script"],
	},
)

TOOLS = [run_python_tool]
