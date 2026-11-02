"""Load infrequent tool schemas only when a task needs them."""

from builder.ai.agent.registry import Tool

TOOLSETS = {
	"project": ("read_project", "update_project", "create_project_page", "remember"),
	"media": (
		"prepare_uploaded_asset",
		"generate_artwork",
		"transform_asset",
		"acquire_paid_asset",
		"asset_contact_sheet",
		"acquire_asset",
		"search_images",
	),
	"design": (
		"create_design_directions",
		"read_design_direction",
		"apply_design_direction",
		"generate_page",
		"add_block",
		"remove_block",
		"move_block",
		"set_design_token",
		"set_page_settings",
		"preview_page",
		"verify_page",
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
	"scripts": (
		"get_interaction_recipe",
		"get_page_scripts",
		"set_page_script",
		"attach_page_script",
		"update_script",
	),
	"components": ("edit_component", "extract_component", "get_document"),
	"settings": ("edit_global_settings", "set_home_page", "remember"),
	"research": ("read_url", "research", "inspect_reference"),
	"plugins": ("write_plugin", "read_plugin", "read_editor_source"),
}
CORE_TOOLS = {
	"read_artifact",
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
	ctx.loaded_groups = set(getattr(ctx, "loaded_groups", ())) | set(groups)
	from builder.ai.policies import GROUPS

	instructions = "\n\n".join(GROUPS[group] for group in groups)
	return "Tools now available: " + ", ".join(sorted(names)) + "\n\n" + instructions


TOOLS = [
	Tool(
		name="load_tools",
		side="server",
		handler=load_tools,
		description="Enable tool groups for your next round: design (generation, structure, tokens, preview), data (documents, forms, Python), scripts, components, settings (global settings/memory), project (multipage plan/routes/memory), research (web), media (generated artwork, licensed stock, crops, contact sheets), plugins (editor extensions). Load the groups needed for the task together. Tool schemas remain available this turn.",
		parameters={
			"type": "object",
			"properties": {"groups": {"type": "array", "items": {"type": "string", "enum": list(TOOLSETS)}}},
			"required": ["groups"],
		},
	)
]
