"""Block-editing tools. All are client-side: the loop batches the operations
and the frontend applies them to the canvas block tree."""

from builder.ai.agent.registry import Tool

update_block = Tool(
	name="update_block",
	side="client",
	description=(
		"Merge style, attribute, or content changes into an existing block. "
		"Use this to change colours, fonts, spacing, text, HTML attributes, "
		"element type, or class names on ANY block at any nesting depth. "
		"Make sure to set units on style values (e.g. padding: '10px' not just 10)."
	),
	parameters={
		"type": "object",
		"properties": {
			"block_id": {
				"type": "string",
				"description": "The blockId of the target block (from the page YAML).",
			},
			"base_styles": {
				"type": "object",
				"description": "CSS-in-JS camelCase style properties to merge into baseStyles (desktop). E.g. {backgroundColor: '#ff0000'}.",
			},
			"mobile_styles": {
				"type": "object",
				"description": "CSS-in-JS style properties to merge into mobileStyles.",
			},
			"tablet_styles": {
				"type": "object",
				"description": "CSS-in-JS style properties to merge into tabletStyles.",
			},
			"attributes": {
				"type": "object",
				"description": "HTML attributes to merge (e.g. {href: '/about', target: '_blank'} for links, {src: '...', alt: '...'} for images, {id: 'hero-section'} for HTML id). Do not use this for block identity; block_id is separate.",
			},
			"inner_text": {
				"type": "string",
				"description": "Replace the text content of the block (plain text).",
			},
			"inner_html": {
				"type": "string",
				"description": "Replace the inner HTML of the block (use for rich content).",
			},
			"element": {
				"type": "string",
				"description": "Change the HTML element tag (e.g. 'h1', 'button', 'a').",
			},
			"classes": {
				"type": "array",
				"items": {"type": "string"},
				"description": "Replace the classes array on the block.",
			},
		},
		"required": ["block_id"],
	},
)

add_block = Tool(
	name="add_block",
	side="client",
	description=(
		"Insert a new block as a child of an existing block. "
		"Use this to add sections, components, or elements anywhere in the page tree."
	),
	parameters={
		"type": "object",
		"properties": {
			"parent_block_id": {
				"type": "string",
				"description": "The blockId of the parent block that will contain the new block.",
			},
			"block": {
				"type": "object",
				"description": "The new block definition. Do NOT include an 'id' field — one will be auto-assigned.",
				"properties": {
					"el": {
						"type": "string",
						"description": "HTML element tag (e.g. section, div, h1, p, button, img, a).",
					},
					"name": {
						"type": "string",
						"description": "Human-readable label for this block.",
					},
					"style": {
						"type": "object",
						"description": "CSS-in-JS camelCase desktop styles (e.g. {backgroundColor: '#fff', padding: '40px'}).",
					},
					"m_style": {
						"type": "object",
						"description": "Mobile style overrides (same format as style).",
					},
					"t_style": {
						"type": "object",
						"description": "Tablet style overrides (same format as style).",
					},
					"attrs": {
						"type": "object",
						"description": "HTML attributes (e.g. {src: '...', alt: '...', href: '/', id: 'features'}).",
					},
					"text": {
						"type": "string",
						"description": "Text content of the element.",
					},
					"classes": {
						"type": "array",
						"items": {"type": "string"},
						"description": "CSS class names to apply.",
					},
					"c": {
						"type": "array",
						"description": "Child blocks (same schema, recursively).",
						"items": {"type": "object"},
					},
				},
				"required": ["el"],
			},
			"after_block_id": {
				"type": "string",
				"description": "Insert the new block immediately after this sibling blockId. Takes precedence over 'index'.",
			},
			"index": {
				"type": "integer",
				"description": "Zero-based position in the parent's children list. Defaults to appending at the end.",
			},
		},
		"required": ["parent_block_id", "block"],
	},
)

remove_block = Tool(
	name="remove_block",
	side="client",
	description="Delete an existing block (and all its descendants) from the page.",
	parameters={
		"type": "object",
		"properties": {
			"block_id": {
				"type": "string",
				"description": "The blockId of the block to delete.",
			},
		},
		"required": ["block_id"],
	},
)

move_block = Tool(
	name="move_block",
	side="client",
	description="Move an existing block to a different parent, or reorder it within the same parent.",
	parameters={
		"type": "object",
		"properties": {
			"block_id": {
				"type": "string",
				"description": "The blockId of the block to move.",
			},
			"new_parent_block_id": {
				"type": "string",
				"description": "The blockId of the new parent block.",
			},
			"after_block_id": {
				"type": "string",
				"description": "Place the block immediately after this sibling blockId in the new parent. Takes precedence over 'index'.",
			},
			"index": {
				"type": "integer",
				"description": "Zero-based position in the new parent's children list. Defaults to appending at the end.",
			},
		},
		"required": ["block_id", "new_parent_block_id"],
	},
)

TOOLS = [update_block, add_block, remove_block, move_block]
