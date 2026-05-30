"""Full-page generation tool.

`generate_page` is an *artifact* tool: the conversational model calls it with a
short `brief`, and the loop hands execution to `generate_page_yaml`, which
streams the full page YAML on the heavy model as content (so the canvas renders
live) and returns the canonical client op the frontend applies. The agent
calling this tool is the only trigger for generation — see agent/artifact.py.
"""

from builder.ai.agent.artifact import generate_page_yaml
from builder.ai.agent.registry import Tool

generate_page = Tool(
	name="generate_page",
	side="client",
	artifact="page_yaml",
	generator=generate_page_yaml,
	description=(
		"Build a complete web page from scratch and replace the entire page with it. "
		"Use this when the page is empty, or when the user asks to create a new page or "
		"fully redesign/restructure the existing one — but only AFTER the user has "
		"approved a proposed plan. When a plan is pending and the user approves it (any "
		"affirmative), call THIS — do not call propose_plan again. For small, targeted "
		"edits to an existing page, use the block tools (update_block, add_block, …) "
		"instead — do NOT regenerate the whole page for a minor change."
	),
	parameters={
		"type": "object",
		"properties": {
			"brief": {
				"type": "string",
				"description": (
					"A concise spec of the page to build, drawn from the approved plan and "
					"conversation: the brand/product name, positioning, audience, the section "
					"list, and the palette (with hex codes). Do NOT write the YAML yourself — "
					"the brief guides a dedicated generation step that produces the full page."
				),
			},
		},
		"required": ["brief"],
	},
)

TOOLS = [generate_page]
