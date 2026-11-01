"""Load infrequent tool schemas only when a task needs them."""

from builder.ai.agent.registry import Tool

TOOLSETS = {
	"design": (
		"generate_page",
		"add_block",
		"remove_block",
		"move_block",
		"set_design_token",
		"set_page_settings",
		"preview_page",
		"acquire_asset",
	),
	"data": (
		"list_doctypes",
		"get_doctype_schema",
		"get_document",
		"write_page_data_script",
		"create_doctype",
		"seed_sample_data",
		"connect_form",
		"run_python",
	),
	"scripts": ("get_page_scripts", "set_page_script", "attach_page_script", "update_script"),
	"components": ("edit_component", "extract_component", "get_document"),
	"settings": ("edit_global_settings", "set_home_page", "remember"),
	"research": ("read_url", "research"),
	"plugins": ("write_plugin", "read_plugin", "read_editor_source"),
}
CORE_TOOLS = {
	"load_tools",
	"present_ui",
	"update_design_brief",
	"query_blocks",
	"read_block",
	"update_block",
	"update_blocks",
	"read_page",
	"query_records",
	"search_images",
}


def load_tools(ctx, args: dict) -> str:
	groups = args.get("groups") or []
	if not groups or any(group not in TOOLSETS for group in groups):
		return "FAILED: choose one or more available groups."
	names = {name for group in groups for name in TOOLSETS[group]}
	ctx.registry.activate(names)
	return "Tools now available: " + ", ".join(sorted(names))


TOOLS = [
	Tool(
		name="load_tools",
		side="server",
		handler=load_tools,
		description="Enable tool groups for your next round: design (generation, structure, tokens, preview), data (documents, forms, Python), scripts, components, settings (global settings/memory), research (web), plugins (editor extensions). Load the groups needed for the task together. Tool schemas remain available this turn.",
		parameters={
			"type": "object",
			"properties": {"groups": {"type": "array", "items": {"type": "string", "enum": list(TOOLSETS)}}},
			"required": ["groups"],
		},
	)
]
