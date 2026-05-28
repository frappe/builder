"""Full-page generation tool.

`generate_page` is a client-side tool whose `yaml` argument is *streamed*: as the
model writes the page YAML, the loop decodes the partial tool-call arguments and
emits the YAML incrementally so the frontend can render sections live (preserving
the original page-generation UX). The final operation is also delivered in the
tool batch so the frontend can apply the authoritative, complete page.
"""

from builder.ai.agent.registry import Tool

generate_page = Tool(
	name="generate_page",
	side="client",
	stream_arg="yaml",
	description=(
		"Build a complete web page from scratch and replace the entire page with it. "
		"Use this when the page is empty, or when the user asks to create a new page or "
		"fully redesign/restructure the existing one. For small, targeted edits to an "
		"existing page, use the block tools (update_block, add_block, …) instead — do NOT "
		"regenerate the whole page for a minor change."
	),
	parameters={
		"type": "object",
		"properties": {
			"yaml": {
				"type": "string",
				"description": (
					"The full page as a compact YAML document. A single root block "
					"(el: div, id: root, name: body) whose 'c' array holds the page "
					"sections. Follow the schema and styling rules from the system prompt."
				),
			},
		},
		"required": ["yaml"],
	},
)

TOOLS = [generate_page]
