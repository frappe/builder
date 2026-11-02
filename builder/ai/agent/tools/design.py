import json

import frappe

from builder.ai.agent.registry import Tool
from builder.ai.brief import STAGES, TEXT_FIELDS, DesignBrief


def create_directions(ctx, args):
	import json

	from builder.ai.design import create_direction

	directions = args.get("directions") or []
	if not 1 <= len(directions) <= 3:
		return "FAILED: create one to three directions per shortlist."
	options = [create_direction(ctx.page_id, spec, getattr(ctx, "run_id", None)) for spec in directions]
	return json.dumps(
		{
			"choices": options,
			"next": "Present these image choices with present_ui. After selection use apply_design_direction; do not regenerate the selected composition.",
		}
	)


def apply_direction(ctx, args):
	from builder.ai.design import apply_direction as apply

	return apply(ctx, args["variant_id"])


def update_brief(ctx, args: dict) -> str:
	if not ctx.page_id:
		return "FAILED: open a page first."
	source = None
	if getattr(ctx, "run_id", None):
		source = frappe.db.get_value("Builder AI Run", ctx.run_id, "user_message")
	return json.dumps(DesignBrief(ctx.page_id).update(args, source), ensure_ascii=False)


TOOLS = [
	Tool(
		name="create_design_directions",
		side="server",
		handler=create_directions,
		description="Render one to three real desktop/mobile WebP previews from editable Builder layouts. Reuses cached variants. Supply real copy/assets; optional recipes editorial/split/compact/stage, or candidate YAML. No SVG previews. Pass returned choices to present_ui.",
		parameters={
			"type": "object",
			"properties": {
				"directions": {
					"type": "array",
					"minItems": 1,
					"maxItems": 3,
					"items": {
						"type": "object",
						"properties": {
							key: {"type": "string"}
							for key in (
								"label",
								"rationale",
								"recipe",
								"headline",
								"description",
								"action",
								"action_url",
								"section_title",
								"section_copy",
								"asset_id",
								"font",
								"yaml",
							)
						}
						| {
							"palette": {
								"type": "object",
								"properties": {
									role: {"type": "string"} for role in ("background", "text", "accent")
								},
							}
						},
						"required": ["label"],
					},
				}
			},
			"required": ["directions"],
		},
	),
	Tool(
		name="apply_design_direction",
		side="server",
		handler=apply_direction,
		description="Apply the user's selected rendered direction as editable blocks. Preserves its exact composition and verifies brief/page revisions. Use its variant_id; continue building from the selected draft.",
		parameters={
			"type": "object",
			"properties": {"variant_id": {"type": "string"}},
			"required": ["variant_id"],
		},
	),
	Tool(
		name="update_design_brief",
		side="server",
		handler=update_brief,
		description="Save page-specific user facts and agreed design decisions across chats. Supply only changed fields; an empty string clears a field. Keep hypotheses in open_questions, never invent business facts. Store exact selected asset URLs in visual_direction or content. The brief is included every turn. Facts and decisions are proposed records with source provenance; the user accepts or rejects them in the brief. Never change an accepted user decision implicitly.",
		parameters={
			"type": "object",
			"properties": {
				**{field: {"type": "string", "maxLength": 1500} for field in TEXT_FIELDS},
				**{
					field: {
						"type": "array",
						"maxItems": 30,
						"items": {
							"type": "object",
							"properties": {
								"id": {"type": "string"},
								"label": {"type": "string"},
								"value": {"type": "string", "maxLength": 1000},
							},
							"required": ["value"],
						},
					}
					for field in ("facts", "decisions")
				},
				"stage": {"type": "string", "enum": list(STAGES)},
			},
			"additionalProperties": False,
		},
	),
]
