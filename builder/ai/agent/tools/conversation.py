"""Conversation tools — the agent's way of pausing the loop to talk to the user.

Both are *terminal*: calling one ends the turn and hands control back to the
user. They replace the old approach of smuggling clarification/plan JSON inside
the model's text and regex-parsing it out, plus the `✓ APPROVED` magic string.
Approval is now just the user's next ordinary message.
"""

import frappe

from builder.ai.agent.registry import Tool
from builder.ai.session import AISession


def _ask_clarification(ctx, args: dict) -> None:
	question = (args.get("question") or "Could you clarify?").strip()
	options = [str(o).strip() for o in (args.get("options") or []) if str(o).strip()]
	previews = _clean_previews(args.get("previews"), len(options))
	# Persist + commit BEFORE emitting: the realtime event triggers a session
	# reload on the client, which must see this message already in the DB.
	AISession.try_append_message(
		ctx.session_id,
		"assistant",
		question,
		message_type="clarification",
		task_type="agent",
		metadata={"status": "clarification", "options": options, "previews": previews},
	)
	frappe.db.commit()
	ctx.emit("clarify", question=question, options=options, previews=previews)


def _propose_plan(ctx, args: dict) -> None:
	headline = (args.get("headline") or "Here's my plan").strip()
	sections = [str(s).strip() for s in (args.get("sections") or []) if str(s).strip()]
	palette = (args.get("palette") or "").strip()
	AISession.try_append_message(
		ctx.session_id,
		"assistant",
		headline,
		message_type="clarification",
		task_type="agent",
		metadata={"status": "plan_summary", "headline": headline, "sections": sections, "palette": palette},
	)
	frappe.db.commit()
	ctx.emit(
		"clarify",
		question=headline,
		options=[],
		plan_summary=True,
		headline=headline,
		sections=sections,
		palette=palette,
	)


def _clean_previews(raw, n_options: int) -> list[dict] | None:
	"""Validate optional colour-swatch previews; must align 1:1 with options."""
	if not isinstance(raw, list) or len(raw) != n_options:
		return None
	previews = []
	for p in raw:
		if isinstance(p, dict) and isinstance(p.get("colors"), list):
			colors = [str(c).strip() for c in p["colors"] if c and str(c).strip()]
			previews.append({"colors": colors})
		else:
			return None
	return previews


ask_clarification = Tool(
	name="ask_clarification",
	side="terminal",
	description=(
		"Ask the user ONE focused question to gather information you need (e.g. brand name, "
		"positioning, audience, visual style). Ends your turn and waits for their reply. "
		"Provide 2–5 short options when there are sensible choices; omit options for "
		"open-ended answers like a name (the user can type their reply)."
	),
	parameters={
		"type": "object",
		"properties": {
			"question": {"type": "string", "description": "A single, focused question."},
			"options": {
				"type": "array",
				"items": {"type": "string"},
				"description": "Optional: 2–5 short plain-text answer choices. Omit for open-ended questions.",
			},
			"previews": {
				"type": "array",
				"description": (
					"ONLY for questions that ask the user to choose a COLOUR PALETTE: one entry "
					"per option, each {colors: ['#hex', ...]} showing that palette's swatches. "
					"Do NOT use for font, layout, tone, or any non-colour question."
				),
				"items": {
					"type": "object",
					"properties": {"colors": {"type": "array", "items": {"type": "string"}}},
				},
			},
		},
		"required": ["question"],
	},
	handler=_ask_clarification,
)

propose_plan = Tool(
	name="propose_plan",
	side="terminal",
	description=(
		"Before building a NEW page or doing a major redesign, present a short plan and "
		"wait for the user to approve or refine it. Ends your turn. Only call generate_page "
		"after the user approves."
	),
	parameters={
		"type": "object",
		"properties": {
			"headline": {"type": "string", "description": "One-line description of the page."},
			"sections": {
				"type": "array",
				"items": {"type": "string"},
				"description": "3–5 short section descriptions (under 12 words each).",
			},
			"palette": {"type": "string", "description": "Palette description with hex codes."},
		},
		"required": ["headline", "sections"],
	},
	handler=_propose_plan,
)

TOOLS = [ask_clarification, propose_plan]
