"""JSON-RPC layer: parse one MCP message, dispatch, shape the reply.

Stateless by design (SEP-2575): no handshake state, no session ids; every
request is served on its own. Legacy streamable-HTTP clients work too
because `initialize` is answered statelessly and notifications are simply
accepted with 202.
"""

import json

import frappe

import builder
from builder.ai.mcp import dispatch
from builder.ai.mcp import tools as surface

PROTOCOL_VERSIONS = ("2025-06-18", "2025-03-26")

INSTRUCTIONS = """Frappe Builder MCP server: build and manage this site's web pages.

Workflow: list_pages to find page ids, read_page before editing, then edit. Every page-scoped tool takes a `page` argument.

Block model:
- A page is a tree of blocks. read_page returns compact YAML where each block shows a ref; pass that ref as block_id to edit it. update_block merges base_styles / mobile_styles / tablet_styles / attributes / text changes into a block; add_block inserts a complete new block (no ref) under a parent, nesting children via `c`.
- Styles are camelCase CSS properties with explicit units, e.g. base_styles: {paddingTop: "96px", justifyContent: "space-between"}. Mobile and tablet styles override base styles at those breakpoints.
- Text lives in semantic elements (h1..h6, p, span, a). Icons are Lucide icon blocks, never emoji glyphs.
- Never write moustache templates in attributes or innerHTML. Data binding uses block `bind` keys with a page data script (write_page_data_script).
- fontFamily takes a bare family name like "Inter". Prefer design tokens: set_design_token returns a var(--token) handle to use in style values.
- Client scripts (set_page_script) target class or id hooks you add to blocks via update_block, never a block ref.

Safety: a revert snapshot is saved automatically before the first edit of each mutating call; revert_page restores the latest one. Destructive tools are annotated, so your client asks before running them. After building, call preview_page and check the screenshots for breakage before reporting done."""


class RpcError(Exception):
	def __init__(self, code: int, message: str):
		self.code = code
		self.message = message


def handle(raw: bytes) -> tuple[int, dict | None]:
	"""Serve one MCP message. Returns (http_status, json payload or None)."""
	try:
		message = json.loads(raw or b"null")
	except Exception:
		return 200, error(None, -32700, "Parse error: body must be a JSON object")
	if isinstance(message, list):
		return 200, error(None, -32600, "Batching is not supported: send one message per request")
	if not isinstance(message, dict) or message.get("jsonrpc") != "2.0":
		return 200, error(None, -32600, "Invalid JSON-RPC message")
	if "id" not in message:
		# Notification (initialized, cancelled, ...) or a stray client response:
		# nothing is tracked between requests, accept and drop.
		return 202, None
	handler = METHODS.get(message.get("method"))
	if handler is None:
		return 200, error(message["id"], -32601, f"Method not found: {message.get('method')}")
	try:
		return 200, result(message["id"], handler(message.get("params") or {}))
	except RpcError as e:
		return 200, error(message["id"], e.code, e.message)
	except Exception:
		frappe.logger("builder.ai.mcp").error("mcp rpc crashed", exc_info=True)
		return 200, error(message["id"], -32603, "Internal error")


def result(request_id, payload: dict) -> dict:
	return {"jsonrpc": "2.0", "id": request_id, "result": payload}


def error(request_id, code: int, message: str) -> dict:
	return {"jsonrpc": "2.0", "id": request_id, "error": {"code": code, "message": message}}


def server_info() -> dict:
	return {"name": "frappe-builder", "version": builder.__version__}


def handle_initialize(params: dict) -> dict:
	requested = params.get("protocolVersion")
	return {
		"protocolVersion": requested if requested in PROTOCOL_VERSIONS else PROTOCOL_VERSIONS[0],
		"capabilities": {"tools": {}},
		"serverInfo": server_info(),
		"instructions": INSTRUCTIONS,
	}


def handle_discover(params: dict) -> dict:
	return {
		"supportedVersions": list(PROTOCOL_VERSIONS),
		"capabilities": {"tools": {}},
		"serverInfo": server_info(),
		"instructions": INSTRUCTIONS,
	}


def handle_tools_list(params: dict) -> dict:
	return {
		"tools": [
			{
				"name": tool.name,
				"description": tool.description,
				"inputSchema": tool.parameters,
				"annotations": surface.annotations(tool.name),
			}
			for tool in surface.TOOLS.values()
		]
	}


def handle_tools_call(params: dict) -> dict:
	name = params.get("name")
	if name not in surface.TOOLS:
		raise RpcError(-32602, f"Unknown tool: {name}")
	arguments = params.get("arguments") or {}
	if not isinstance(arguments, dict):
		raise RpcError(-32602, "arguments must be an object")
	content, is_error = dispatch.call_tool(name, arguments)
	return {"content": content, "isError": is_error}


METHODS = {
	"initialize": handle_initialize,
	"server/discover": handle_discover,
	"ping": lambda params: {},
	"tools/list": handle_tools_list,
	"tools/call": handle_tools_call,
}
