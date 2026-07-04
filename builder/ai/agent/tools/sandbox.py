"""General-purpose sandboxed Python tool — do anything, within guardrails.

THE editing primitive: the model writes a short script, Frappe's safe_exec runs
it under RestrictedPython (no imports, no file/network access, permission-
checked frappe.get_list/get_doc, site user privileges). The current page tree
is bound as `page` — a plain dict the script can read AND mutate. If the script
changed the tree, the new tree is queued as a set_page_blocks client op and the
canvas applies it wholesale (blockIds are preserved, so refs stay stable). One
primitive replaces the whole update/add/remove/move/query tool family.
"""

import contextlib
import copy
import json
import signal

from builder.ai.agent.registry import Tool

MAX_OUTPUT_CHARS = 6000
TIMEOUT_SECONDS = 10


def run_python(ctx, args: dict) -> str:
	script = (args.get("script") or "").strip()
	if not script:
		return "Pass a non-empty script."
	from frappe.utils.safe_exec import is_safe_exec_enabled, safe_exec

	if not is_safe_exec_enabled():
		return "run_python is disabled on this site (server_script_enabled is off). Use the other tools."

	logs: list[str] = []
	root = live_tree(ctx)
	# Single namespace (globals only): with a separate _locals dict, functions the
	# script defines can't see its top-level variables — exec scoping — and the
	# model writes helper functions all the time.
	script_globals = {
		"page": copy.deepcopy(root),
		"page_id": getattr(ctx, "page_id", None),
		"result": None,
		"log": lambda *a: logs.append(" ".join(str(x) for x in a)),
		"progress": make_progress(ctx),
	}
	try:
		with time_limit(TIMEOUT_SECONDS):
			exec_globals, _ = safe_exec(
				script,
				_globals=script_globals,
				restrict_commit_rollback=True,
				script_filename="builder_ai_run_python",
			)
	except TimeoutError:
		return f"Script exceeded the {TIMEOUT_SECONDS}s limit. Simplify it — no heavy loops."
	except Exception as e:
		return f"Script error: {type(e).__name__}: {e}"
	status = apply_mutation(ctx, root, exec_globals.get("page"))
	return status + render_output(logs, exec_globals.get("result"))


def make_progress(ctx):
	"""progress('…') inside a script surfaces live in the chat UI — feedback the
	user watches during a long multi-page operation."""
	if not hasattr(ctx, "emit"):
		return lambda msg: None
	return lambda msg: ctx.emit("progress", message=str(msg)[:200])


def live_tree(ctx) -> dict | None:
	"""The tree as of the LAST applied edit this turn (mirror), falling back to the
	turn-start context — a second run_python must see its own earlier mutation."""
	tree = getattr(ctx, "tree", None) if ctx else None
	if tree is not None and tree.root is not None:
		return tree.root
	return ctx.page_root() if ctx else None


def apply_mutation(ctx, before: dict | None, after) -> str:
	"""Queue the mutated tree as a set_page_blocks client op. Returns a status line
	for the tool result ('' when the script only read)."""
	if after == before or not hasattr(ctx, "queue_client_op"):
		return ""
	if not isinstance(after, dict) or not isinstance(after.get("children"), list):
		return (
			"Page NOT updated: `page` must stay a block dict with a 'children' list "
			f"(got {type(after).__name__}). Fix the script and rerun.\n"
		)
	ctx.queue_client_op({"tool_name": "set_page_blocks", "args": {"blocks": after}})
	return "Page tree updated and applied to the canvas.\n"


def render_output(logs: list[str], result) -> str:
	parts = []
	if logs:
		parts.append("\n".join(logs))
	if result is not None:
		try:
			parts.append("result = " + json.dumps(result, indent=1, default=str))
		except (TypeError, ValueError):
			parts.append("result = " + str(result))
	if not parts:
		return "Script ran but produced no output — call log(...) or set `result`."
	out = "\n".join(parts)
	if len(out) > MAX_OUTPUT_CHARS:
		out = out[:MAX_OUTPUT_CHARS] + "\n… output truncated. Narrow what you log/return."
	return out


@contextlib.contextmanager
def time_limit(seconds: int):
	"""Best-effort wall-clock cap; SIGALRM only works on the main thread, so
	elsewhere (tests, gevent) the script simply runs unguarded."""

	def on_alarm(signum, frame):
		raise TimeoutError

	try:
		previous = signal.signal(signal.SIGALRM, on_alarm)
	except ValueError:
		yield
		return
	signal.alarm(seconds)
	try:
		yield
	finally:
		signal.alarm(0)
		signal.signal(signal.SIGALRM, previous)


run_python_tool = Tool(
	name="run_python",
	side="server",
	handler=run_python,
	description=(
		"THE editing primitive: run a short sandboxed Python script server-side with the "
		"current page tree bound as `page` — a plain dict you can READ and MUTATE. Any "
		"mutation to `page` is applied to the canvas when the script finishes. Block dicts "
		"carry blockId/element/innerHTML/baseStyles/mobileStyles/tabletStyles/attributes/"
		"classes/children (read Builder's source via read_source frontend/src/block.ts when "
		"unsure). Never invent a blockId for a block you add — omit it, the editor assigns "
		"one. Bound: `page`, `page_id` (current Builder Page doc name), log(...), "
		"progress('msg') (shows live in the chat UI — call it between steps of a long "
		"operation), `result`. Also available: the permission-checked frappe API "
		"(get_list/get_doc/db.set_value, doc.save()) and json — this is how you manage the "
		"WHOLE SITE: SEO/meta fields on Builder Page docs (page_title, meta_description, "
		"meta_image, route, dynamic_route, published, disable_indexing), redirects "
		"(Website Settings child table route_redirects: source/target), and OTHER pages' "
		"content (their tree is json in the doc's draft_blocks field — same block shape). "
		"NEVER edit the CURRENT page via its doc — mutate `page` instead; doc edits to the "
		"open page get overwritten by the editor. NOT available: files, network, and "
		"imports — never write `import x`, it always fails; json and frappe are pre-bound."
	),
	parameters={
		"type": "object",
		"properties": {
			"script": {
				"type": "string",
				"description": "Python source. No imports. Use log(...) for output and set `result` for the final value.",
			},
		},
		"required": ["script"],
	},
)

TOOLS = [run_python_tool]
