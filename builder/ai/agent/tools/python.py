"""run_python — the general read primitive.

The named read tools answer the common questions; this answers the rest. One
sandboxed snippet can count, aggregate, and cross-reference anything on the
site, so the agent orients itself on demand instead of depending on pre-baked
context or a bespoke tool per question. Frappe's server-script sandbox
(safe_exec) bounds what the code can reach; on top of it, raw SQL and direct
value writes are stripped from the namespace, and a savepoint rollback erases
anything a snippet nevertheless wrote — read-only by construction, not by
convention.
"""

import frappe

from builder.ai.agent.registry import Tool

RESULT_LIMIT = 6000
SAVEPOINT = "builder_ai_run_python"

# Beyond safe_exec's own rules: no raw SQL (server scripts may read any table,
# including auth internals — Bob's users aren't script authors) and no direct
# value writes. Commit/rollback are already blocked via restrict_commit_rollback.
STRIPPED_DB_METHODS = ("sql", "set_value", "add_index")


def sandbox_globals() -> dict:
	from frappe.utils.safe_exec import get_safe_globals

	safe = get_safe_globals()  # built per call — stripping keys touches only this copy
	for method in STRIPPED_DB_METHODS:
		safe["frappe"]["db"].pop(method, None)
	return safe


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
		safe_exec(script, sandbox_globals(), _locals, restrict_commit_rollback=True)
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
		"or record, cross-doctype questions. Available: frappe.get_all/get_list/get_doc, "
		"frappe.db.get_value/get_single_value/count/exists, frappe.utils date/format "
		"helpers, frappe.session.user, and `page_id` (the open page). No imports, no raw "
		"SQL; nothing it writes persists. Orient yourself with it instead of guessing or "
		"asking the user."
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
