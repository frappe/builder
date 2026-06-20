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
				"description": "The target block's 'ref' value (from the page YAML).",
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
				"description": "HTML attributes to merge (e.g. {href: '/about', target: '_blank'} for links, {src: '...', alt: '...'} for images, {id: 'hero-section'} for HTML id). attrs.id sets the HTML id; the block's ref (passed as block_id) is its editor handle — separate things.",
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
		"Use this to add sections, components, or elements anywhere in the page tree. "
		"NOT for JavaScript or CSS: never add a <script> or <style> block, and never put "
		"code in the block's text/innerHTML — use set_page_script for that. A script added "
		"as a block does not execute in the editor and bypasses the page's script system."
	),
	parameters={
		"type": "object",
		"properties": {
			"parent_block_id": {
				"type": "string",
				"description": "The 'ref' value of the parent block that will contain the new block.",
			},
			"block": {
				"type": "object",
				"description": "The new block definition. Do NOT include a 'ref' or 'id' field — the editor assigns block ids automatically.",
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
				"description": "Insert the new block immediately after this sibling's 'ref'. Takes precedence over 'index'.",
			},
			"index": {
				"type": "integer",
				"description": "Zero-based position in the parent's children list. Defaults to appending at the end.",
			},
		},
		"required": ["parent_block_id", "block"],
	},
)

update_blocks = Tool(
	name="update_blocks",
	side="client",
	description=(
		"Apply edits to MANY blocks in ONE call — the right tool for page-wide changes "
		"(translate every text block, restyle all buttons, recolour all headings). Pair it "
		"with query_blocks: query the set, then update it here in a single call. Two modes:\n"
		"• UNIFORM — set 'block_ids' (a list of refs) plus any of base_styles / mobile_styles / "
		"tablet_styles / attributes / classes / element. The SAME change is merged into every "
		"listed block. Use this when the change is identical (e.g. colour all headings red).\n"
		"• PER-BLOCK — set 'patches', a list where each item is {block_id, …same fields as "
		"update_block}. Each block gets its OWN values. Use this for translation/rewrites where "
		"the new text differs per block.\n"
		"If 'patches' is given it takes precedence and the uniform fields are ignored. Style "
		"merging follows update_block (merges, does not replace)."
	),
	parameters={
		"type": "object",
		"properties": {
			"block_ids": {
				"type": "array",
				"items": {"type": "string"},
				"description": "UNIFORM mode: the refs to apply the same change to. Ignored if 'patches' is set.",
			},
			"base_styles": {
				"type": "object",
				"description": "UNIFORM mode: desktop styles to merge into every listed block.",
			},
			"mobile_styles": {
				"type": "object",
				"description": "UNIFORM mode: mobile style overrides to merge.",
			},
			"tablet_styles": {
				"type": "object",
				"description": "UNIFORM mode: tablet style overrides to merge.",
			},
			"attributes": {
				"type": "object",
				"description": "UNIFORM mode: HTML attributes to merge into every listed block.",
			},
			"classes": {
				"type": "array",
				"items": {"type": "string"},
				"description": "UNIFORM mode: replace the classes array on every listed block.",
			},
			"element": {
				"type": "string",
				"description": "UNIFORM mode: change the HTML tag on every listed block.",
			},
			"patches": {
				"type": "array",
				"description": "PER-BLOCK mode: one object per block, each with 'block_id' plus the fields to change on that block.",
				"items": {
					"type": "object",
					"properties": {
						"block_id": {"type": "string", "description": "The target block's ref."},
						"base_styles": {"type": "object"},
						"mobile_styles": {"type": "object"},
						"tablet_styles": {"type": "object"},
						"attributes": {"type": "object"},
						"inner_text": {
							"type": "string",
							"description": "Replace the block's text (plain text).",
						},
						"inner_html": {"type": "string", "description": "Replace the block's inner HTML."},
						"element": {"type": "string"},
						"classes": {"type": "array", "items": {"type": "string"}},
					},
					"required": ["block_id"],
				},
			},
		},
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
				"description": "The 'ref' of the block to delete.",
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
				"description": "The 'ref' of the block to move.",
			},
			"new_parent_block_id": {
				"type": "string",
				"description": "The 'ref' of the new parent block.",
			},
			"after_block_id": {
				"type": "string",
				"description": "Place the block immediately after this sibling's 'ref' in the new parent. Takes precedence over 'index'.",
			},
			"index": {
				"type": "integer",
				"description": "Zero-based position in the new parent's children list. Defaults to appending at the end.",
			},
		},
		"required": ["block_id", "new_parent_block_id"],
	},
)

TOOLS = [update_block, update_blocks, add_block, remove_block, move_block]
