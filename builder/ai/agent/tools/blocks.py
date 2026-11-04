"""Block editing: one client-side tool taking a markup edit script (agent/edits.py).
The loop applies it to the WorkingTree and mirrors the accepted ops to the canvas."""

from builder.ai.agent.registry import Tool

EDIT_OPS_DOC = (
	"One op per line, applied in order:\n"
	"@ref <segments>: patch the block. Styles and attrs merge; text, classes and tag replace; "
	"`prop:` with no value removes a style, [-attr] an attribute; `// Name` renames. Several "
	"@refs on one line take the same patch.\n"
	"add @parent [n] | add after @ref | add before @ref: the new blocks indented below "
	"(a whole section with its children is one op).\n"
	"replace @ref: its new version indented below.\n"
	"move @ref to @parent [n] | move @ref after @ref | move @ref before @ref\n"
	"remove @ref [@ref ...]\n"
	"$name {css}: a style set for the lines after it (sets read_page showed work too)."
)

edit_page = Tool(
	name="edit_page",
	side="client",
	description=(
		"Change the open page's blocks with a markup script. Put every edit of the round in "
		"ONE script: each round costs a model call, so a section, a restyle of twenty "
		"blocks or a page-wide translation is one call. Never add script or style "
		"elements, or code in a block's text: JS and CSS go through set_page_script.\n" + EDIT_OPS_DOC
	),
	parameters={
		"type": "object",
		"properties": {
			"ops": {"type": "string", "description": "The edit script."},
			"reply": {
				"type": "string",
				"description": (
					"Your final reply, only when this script is the last thing the request needs: the "
					"turn ends here if every op applies (a failure comes back to you instead). Leave it "
					"out while anything is left (another tool, a preview, a next step); it is never a "
					"progress note like 'next I'll wire the form'."
				),
			},
		},
		"required": ["ops"],
	},
)

TOOLS = [edit_page]
