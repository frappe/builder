"""run_python — the general read primitive.

The named read tools answer the common questions; this answers the rest. One
sandboxed snippet can count, aggregate, and cross-reference anything on the
site, so the agent orients itself on demand instead of depending on pre-baked
context or a bespoke tool per question. It runs on Frappe's render-safe
namespace (what Jinja templates get), trimmed further, so it can only read, with
the session user's own permissions. A savepoint rollback erases any write.
"""

import functools

import frappe

from builder.ai.agent.registry import Tool

RESULT_LIMIT = 6000
SAVEPOINT = "builder_ai_run_python"

# Still in the render-safe set: qb and db.sql read any table (auth internals
# included), make_get_request can carry data off-site in its URL,
# render_template and get_last_doc read without permission checks, and
# log_error and response write.
STRIPPED_FRAPPE_KEYS = ("qb", "make_get_request", "render_template", "get_last_doc", "log_error", "response")
# These utils read file contents straight off disk, with no File permission check.
STRIPPED_UTILS = (
	"pdf_to_base64",
	"image_to_base64",
	"get_thumbnail_base64_for_image",
	"get_image_thumbnail_uri",
)

# get_list switches that widen a read past the session user's own permissions.
UNSCOPING_LIST_ARGS = ("ignore_permissions", "ignore_user_permissions", "user")


def sandbox_globals() -> dict:
	from frappe.utils.safe_exec import render_safe_globals

	safe = render_safe_globals()  # built per call, so rebinding keys touches only this copy
	fr = safe["frappe"]
	for key in STRIPPED_FRAPPE_KEYS:
		fr.pop(key, None)
	fr["db"].pop("sql", None)
	for util in STRIPPED_UTILS:
		fr["utils"].pop(util, None)
	scope_reads_to_user(fr)
	hide_exec_only_globals(safe)
	return safe


def scope_reads_to_user(fr) -> None:
	"""Render-safe reads skip permission checks. These answer with the session user's
	own, through get_list, so owner-only roles and User Permissions apply too."""
	db = fr["db"]
	fr["get_all"] = fr["get_list"] = db["get_all"] = db["get_list"] = user_get_list
	fr["get_doc"] = fr["get_cached_doc"] = guarded_get_doc
	db["get_value"] = user_get_value
	db["exists"] = user_exists
	db["count"] = user_count
	db["get_single_value"] = read_guarded(db["get_single_value"])


def hide_exec_only_globals(safe: dict) -> None:
	"""safe_exec lays these globals over its full server-script namespace, so a
	top-level name left out here (FrappeClient, run_script) would still resolve."""
	for key in exec_only_globals():
		safe[key] = None


@functools.cache
def exec_only_globals() -> frozenset:
	from frappe.utils.safe_exec import get_safe_globals, render_safe_globals

	return frozenset(get_safe_globals().keys() - render_safe_globals().keys())


def user_get_list(doctype, fields=None, filters=None, **kwargs):
	from frappe.utils.safe_exec import remove_unsafe_fields

	for key in UNSCOPING_LIST_ARGS:
		kwargs.pop(key, None)
	if isinstance(fields, list):
		fields = remove_unsafe_fields(fields)
	# Always rows, never a query object, as frappe's own safe_get_list insists.
	kwargs["run"] = True
	return frappe.get_list(doctype, fields=fields, filters=filters, **kwargs)


def user_get_value(doctype, filters=None, fieldname="name", *args, as_dict=False, **kwargs):
	if frappe.get_meta(doctype).issingle:
		return read_guarded(frappe.db.get_value)(doctype, filters, fieldname, as_dict=as_dict)
	fields = list(fieldname) if isinstance(fieldname, list | tuple) else [fieldname]
	rows = user_get_list(doctype, fields=fields, filters=by_name(filters), limit=1, as_list=not as_dict)
	if not rows:
		return None
	return rows[0] if as_dict or len(fields) > 1 else rows[0][0]


def user_exists(doctype, filters=None, *args, **kwargs):
	names = user_get_list(doctype, filters=by_name(filters), limit=1, pluck="name")
	return names[0] if names else None


def user_count(doctype, filters=None, *args, **kwargs):
	return len(user_get_list(doctype, filters=filters, limit=0, pluck="name"))


def by_name(filters):
	return {"name": filters} if isinstance(filters, str | int) else filters


def guarded_get_doc(*args, **kwargs):
	from frappe.utils.safe_exec import SafeDoc

	doc = frappe.get_doc(*args, **kwargs)
	doc.check_permission("read")
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
