"""Assemble the MCP tool surface: agent registry tools plus MCP-native page
tools.

Registry Tool objects are module-level singletons shared with the in-app
agent, so their schemas are deep-copied before the `page` parameter is
injected; mutating them in place would corrupt the in-app agent's schemas.
"""

from copy import deepcopy

from builder.ai.agent.registry import Tool, build_default_registry
from builder.ai.mcp import pages
from builder.ai.mcp.pages import PAGE_PARAM

# Per call, not per turn: a crashed call must not wedge the page for long.
MCP_LOCK_TTL = 120

CLIENT_OPS = {"update_block", "update_blocks", "add_block", "remove_block", "move_block"}

# Script tools apply through their server handlers, then mirror the op flagged
# server_applied so an open editor does no DB work (loop.py SCRIPT_TWIN_TOOLS).
SCRIPT_TWINS = {"set_page_script", "update_script"}

# Terminal (confirm-gated) tools and their pending-action kind. Dispatch runs
# the handler for validation only, then applies directly: the MCP client's own
# permission prompt is the confirmation step.
CONFIRM_KINDS = {
	"set_home_page": "home_page",
	"edit_global_settings": "global_settings",
	"create_doctype": "create_doctype",
	"seed_sample_data": "seed_sample_data",
	"connect_form": "connect_form",
}

REGISTRY_ORDER = [
	"query_blocks",
	"read_block",
	"update_block",
	"update_blocks",
	"add_block",
	"remove_block",
	"move_block",
	"set_page_script",
	"update_script",
	"get_page_scripts",
	"set_page_settings",
	"set_design_token",
	"extract_component",
	"list_doctypes",
	"get_doctype_schema",
	"query_records",
	"get_document",
	"write_page_data_script",
	"create_doctype",
	"seed_sample_data",
	"connect_form",
	"search_images",
	"set_home_page",
	"edit_global_settings",
]

# Registry tools that act on one page. The in-app agent resolves the page from
# the editor session; over MCP each gets an injected required `page` param.
PAGE_SCOPED = (
	CLIENT_OPS
	| SCRIPT_TWINS
	| {
		"query_blocks",
		"read_block",
		"get_page_scripts",
		"set_page_settings",
		"write_page_data_script",
		"extract_component",
		"connect_form",
	}
)

PAGE_TAKING = PAGE_SCOPED | pages.PAGE_TAKING

READ_ONLY = {
	"query_blocks",
	"read_block",
	"get_page_scripts",
	"list_doctypes",
	"get_doctype_schema",
	"query_records",
	"get_document",
	"search_images",
	"list_pages",
	"read_page",
	"preview_page",
}

DESTRUCTIVE = {
	"remove_block",
	"update_script",
	"write_page_data_script",
	"delete_page",
	"revert_page",
	"copy_page_design",
	"publish_page",
	"unpublish_page",
	"set_home_page",
	"edit_global_settings",
	"seed_sample_data",
}


def with_page_param(parameters: dict) -> dict:
	params = deepcopy(parameters)
	params.setdefault("properties", {})["page"] = PAGE_PARAM
	required = list(params.get("required") or [])
	if "page" not in required:
		required.append("page")
	params["required"] = required
	return params


def build_tools() -> dict[str, Tool]:
	registry = build_default_registry()
	tools: dict[str, Tool] = {tool.name: tool for tool in pages.TOOLS}
	for name in REGISTRY_ORDER:
		tool = registry.get(name)
		if tool is None:
			continue
		params = with_page_param(tool.parameters) if name in PAGE_SCOPED else deepcopy(tool.parameters)
		tools[name] = Tool(
			name=tool.name,
			side=tool.side,
			description=tool.description,
			parameters=params,
			handler=tool.handler,
		)
	return tools


def annotations(name: str) -> dict:
	return {"readOnlyHint": name in READ_ONLY, "destructiveHint": name in DESTRUCTIVE}


TOOLS = build_tools()
