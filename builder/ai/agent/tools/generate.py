"""Full-page generation tool.

`generate_page` is an *artifact* tool: the agent calls it with a `brief`, and the
loop hands execution to `generate_page_yaml`, which streams the page YAML as
content (so the canvas renders live) and returns the client op that applies it.
See agent/artifact.py.
"""

from builder.ai.agent.artifact import generate_page_yaml
from builder.ai.agent.registry import Tool

generate_page = Tool(
	name="generate_page",
	side="client",
	artifact="page_yaml",
	generator=generate_page_yaml,
	description=(
		"Build a complete web page from a brief and replace the entire page with it. Use it "
		"when the page is empty, or the user asks for a new page or a full redesign. If the "
		"page must match a reference page of this site, read_page that reference this turn "
		"and carry its exact values (var(--id) handles, font names, section structure) into "
		"the brief: a brief written from memory of a page you didn't read produces an "
		"unrelated design. Targeted edits to an existing page use the block tools "
		"(update_block, add_block, …), never a regeneration."
	),
	parameters={
		"type": "object",
		"properties": {
			"brief": {
				"type": "string",
				"description": (
					"The page spec, drawn from the conversation: the design direction (layout "
					"system, signature move, imagery treatment), the brand name and one-line "
					"positioning, the section list with real copy intent, the palette and fonts "
					"(token handles plus values), and any image url marker lines. Specific enough "
					"that the generation step needn't re-infer sizes and weights from adjectives. "
					"Not YAML: a separate generation step writes the page from it."
				),
			},
		},
		"required": ["brief"],
	},
)

TOOLS = [generate_page]
