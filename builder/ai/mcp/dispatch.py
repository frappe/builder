"""Execute one MCP tool call in the current request context: resolve the
page, take the page lock for mutations, route to the right apply path, and
shape the result as MCP content blocks."""

import frappe

from builder.ai import locks
from builder.ai.agent.pending import apply_pending_action
from builder.ai.mcp import tools as surface
from builder.ai.mcp.ctx import CaptureCtx, McpCtx

logger = frappe.logger("builder.ai.mcp")


def call_tool(name: str, arguments: dict) -> tuple[list[dict], bool]:
	result = execute(name, dict(arguments or {}))
	content = to_content(result)
	is_error = bool(content) and content[0]["type"] == "text" and content[0]["text"].startswith("FAILED")
	return content, is_error


def execute(name: str, args: dict) -> str | list:
	tool = surface.TOOLS[name]
	if name not in surface.READ_ONLY and not frappe.has_permission("Builder Page", "write"):
		return "FAILED: your account lacks write access to Builder Pages."
	page = None
	if name in surface.PAGE_TAKING:
		page = str(args.pop("page", "") or "").strip()
		if not page or not frappe.db.exists("Builder Page", page):
			return f"FAILED: page '{page or '(missing)'}' not found. Call list_pages for page ids."
	ctx = McpCtx(page)
	lock_token = None
	if page and name not in surface.READ_ONLY:
		# The in-app agent holds this lock for whole turns; a busy page fails fast.
		lock_token = locks.acquire(locks.page_key(page), surface.MCP_LOCK_TTL)
		if lock_token is None:
			return f"FAILED: page {page} is being edited by the site's AI assistant right now. Try again in a minute."
		ctx.arm_snapshot()
	try:
		return route(tool, name, ctx, args)
	finally:
		if lock_token:
			locks.release(locks.page_key(page), lock_token)


def route(tool, name: str, ctx: McpCtx, args: dict) -> str | list:
	if name in surface.CLIENT_OPS:
		return ctx.apply_block_op(name, args)
	# A crashed handler must not ride the end-of-request commit half-applied
	# (same guard as AgentRunner.run_handler).
	frappe.db.savepoint("mcp_tool")
	try:
		if name in surface.CONFIRM_KINDS:
			return confirm_dispatch(tool, ctx, args)
		result = tool.handler(ctx, args)
	except Exception as e:
		frappe.db.rollback(save_point="mcp_tool")
		logger.warning(f"mcp tool {name} raised: {e}", exc_info=True)
		return f"FAILED: {name} errored ({type(e).__name__}: {e})."
	if name in surface.SCRIPT_TWINS and not str(result).startswith("FAILED"):
		ctx.ensure_revert_snapshot()
		ctx.emit("tool_batch", operations=[{"tool_name": name, "args": {**args, "server_applied": True}}])
	ctx.drain_queued_ops()
	return result


def confirm_dispatch(tool, ctx: McpCtx, args: dict) -> str:
	capture = CaptureCtx(ctx.page_id)
	declined = tool.handler(capture, args)
	if isinstance(declined, str):
		return declined
	if not capture.captured:
		return f"FAILED: {tool.name} proposed no action."
	return apply_pending_action(capture.captured["kind"], capture.captured["payload"])


def to_content(result) -> list[dict]:
	if isinstance(result, list):
		return result
	return [{"type": "text", "text": str(result if result is not None else "Done.")}]
