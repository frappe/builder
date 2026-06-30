"""Selector tool: find blocks by structural filters.

`query_blocks` is server-side — it walks the turn-start page tree the frontend
shipped and returns the matching blocks' refs (+ element and full text). This
grounds bulk edits: instead of scanning the page context and hoping it catches
every block, the model asks for the exact set ("all text", "all h2", "every
button") and gets it deterministically, then applies one `update_blocks` call.
Text is returned in FULL — translation/rewrite needs every block's real copy.
"""

from builder.ai.agent.registry import Tool
from builder.ai.agent.selectors import block_text, find_block, match_block, walk_blocks
from builder.ai.block_codec import BlockCodec
from builder.utils import to_compact_yaml


def run_query_blocks(ctx, args: dict) -> str:
	root = ctx.page_root()
	if root is None:
		return "The page is empty — nothing to select."

	scope = args.get("within")
	start = root
	if scope:
		start = find_block(root, scope)
		if start is None:
			return f"No block found with ref {scope}."

	element = args.get("element")
	text_only = bool(args.get("text_only"))
	contains = args.get("contains")
	class_name = args.get("class_name")

	matches = []
	for block, _depth in walk_blocks(start):
		if match_block(
			block,
			element=element,
			text_only=text_only,
			contains=contains,
			class_name=class_name,
		):
			ref = block.get("blockId")
			if not ref:
				continue
			entry = {"ref": ref, "el": block.get("element") or "div"}
			if text := block_text(block):
				entry["text"] = text  # full text, never truncated — needed for translate/rewrite
			if classes := block.get("classes"):
				entry["classes"] = classes
			matches.append(entry)

	if not matches:
		return "No blocks matched. Loosen the filters or check the page outline."
	header = f"{len(matches)} block(s) matched (page as it was at the start of this turn):\n"
	return header + to_compact_yaml(matches)


query_blocks = Tool(
	name="query_blocks",
	side="server",
	handler=run_query_blocks,
	description=(
		"Find blocks on the current page by structural filters, returning each match's "
		"'ref' (its block_id), element, and FULL text. Use this before any change that "
		"affects MANY blocks — translate the page, restyle every button, rewrite all "
		"headings — so you act on the complete, exact set instead of guessing from the "
		"outline. Filters AND together. Then apply the change with ONE update_blocks call. "
		"Results reflect the page at the start of this turn (edits you make mid-turn are not "
		"re-queried)."
	),
	parameters={
		"type": "object",
		"properties": {
			"element": {
				"type": "string",
				"description": "Match only this HTML tag (e.g. 'h2', 'button', 'p').",
			},
			"text_only": {
				"type": "boolean",
				"description": "Match only text-bearing blocks (headings, paragraphs, labels, buttons, list items…). Use this for translate/rewrite-all requests.",
			},
			"contains": {
				"type": "string",
				"description": "Match only blocks whose text contains this substring (case-insensitive).",
			},
			"class_name": {
				"type": "string",
				"description": "Match only blocks carrying this CSS class.",
			},
			"within": {
				"type": "string",
				"description": "Limit the search to the subtree under this block's ref. Defaults to the whole page.",
			},
		},
	},
)


def run_read_block(ctx, args: dict) -> str:
	root = ctx.page_root()
	if root is None:
		return "The page is empty."
	ref = args.get("block_id")
	block = find_block(root, ref) if ref else None
	if block is None:
		return f"No block found with ref {ref}."
	detail = to_compact_yaml(BlockCodec.compress(block, depth=0, task_tier="complex"))
	return f"Block {ref} (full styles/attributes/children, as of the start of this turn):\n{detail}"


read_block = Tool(
	name="read_block",
	side="server",
	handler=run_read_block,
	description=(
		"Return a block's FULL detail — its styles, attributes, text, and child subtree — "
		"by ref. Use this on a large page (where the context is only an outline) before "
		"editing a block whose current styles you need to see, or to match the styling of an "
		"existing section. Reflects the page at the start of this turn."
	),
	parameters={
		"type": "object",
		"properties": {
			"block_id": {"type": "string", "description": "The ref of the block to inspect."},
		},
		"required": ["block_id"],
	},
)

TOOLS = [query_blocks, read_block]
