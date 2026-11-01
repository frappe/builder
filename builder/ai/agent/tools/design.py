import json

import frappe

from builder.ai.agent.registry import Tool
from builder.ai.brief import STAGES, TEXT_FIELDS, DesignBrief


def update_brief(ctx, args: dict) -> str:
	if not ctx.page_id:
		return "FAILED: open a page first."
	source = None
	if getattr(ctx, "run_id", None):
		source = frappe.db.get_value("Builder AI Run", ctx.run_id, "user_message")
	return json.dumps(DesignBrief(ctx.page_id).update(args, source), ensure_ascii=False)


TOOLS = [
	Tool(
		name="update_design_brief",
		side="server",
		handler=update_brief,
		description="Save page-specific user facts and agreed design decisions across chats. Supply only changed fields; an empty string clears a field. Keep hypotheses in open_questions, never invent business facts. Store exact selected asset URLs in visual_direction or content. The brief is included every turn.",
		parameters={
			"type": "object",
			"properties": {
				**{field: {"type": "string", "maxLength": 1500} for field in TEXT_FIELDS},
				"stage": {"type": "string", "enum": list(STAGES)},
			},
			"additionalProperties": False,
		},
	)
]
