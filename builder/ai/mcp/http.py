"""HTTP endpoint: POST /mcp, a stateless MCP server served by the site.

A page renderer rather than a whitelisted method: full control over the raw
response (JSON-RPC bodies, a 401 with no login redirect) and a clean URL.
Registered ahead of BuilderPageRenderer in hooks.py so a Builder Page routed
"mcp" can never shadow the endpoint. Authentication happens upstream in
frappe.validate_auth (api key/secret or OAuth bearer); an unauthenticated
request gets a plain 401, which carries the WWW-Authenticate header core
attaches and starts the client's OAuth discovery.

This module is imported for every website request (renderer resolution), so
the heavy MCP modules load lazily inside render().
"""

import json

import frappe
from werkzeug.wrappers import Response

MCP_PATH = "/mcp"


class McpPageRenderer:
	def __init__(self, path: str, http_status_code: int | None = None):
		self.path = path

	def can_render(self) -> bool:
		return bool(frappe.request) and frappe.request.path.rstrip("/") == MCP_PATH

	def render(self) -> Response:
		from builder.ai.mcp import rpc

		if frappe.request.method != "POST":
			payload = rpc.error(None, -32000, "Method Not Allowed: POST a single JSON-RPC message")
			return json_response(405, payload, headers={"Allow": "POST"})
		if frappe.session.user == "Guest":
			return json_response(401, {"error": "authentication required"})
		if not frappe.has_permission("Builder Page", "read"):
			return json_response(403, {"error": "this account has no access to Builder Pages"})
		status, payload = rpc.handle(frappe.request.get_data())
		return json_response(status, payload)


def json_response(status: int, payload: dict | None, headers: dict | None = None) -> Response:
	body = "" if payload is None else json.dumps(payload)
	return Response(body, status=status, mimetype="application/json", headers=headers)
