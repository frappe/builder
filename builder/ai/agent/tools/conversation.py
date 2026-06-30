"""Conversation tools — the agent's way of pausing the loop to talk to the user.

Both are *terminal*: calling one ends the turn and hands control back to the
user. They replace the old approach of smuggling clarification/plan JSON inside
the model's text and regex-parsing it out, plus the `✓ APPROVED` magic string.
Approval is now just the user's next ordinary message.
"""

import frappe

from builder.ai.agent.registry import Tool
from builder.ai.session import AISession


def ask_clarification(ctx, args: dict) -> None:
	question = (args.get("question") or "Could you clarify?").strip()
	options = [str(o).strip() for o in (args.get("options") or []) if str(o).strip()]
	previews = clean_previews(args.get("previews"), len(options))
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


def normalize_sections(raw) -> list[str]:
	"""Accept sections as a newline-delimited string (the robust contract for weaker
	models — one quoted JSON array per item is where their tool-call JSON breaks) OR a
	list (Claude does arrays fine). Strip bullets/leading dashes and stray quotes."""
	if isinstance(raw, str):
		items = raw.splitlines()
	elif isinstance(raw, list):
		items = [str(s) for s in raw]
	else:
		items = []
	out = []
	for item in items:
		s = item.strip().lstrip("-•*").strip().strip("'\"").strip()
		if s:
			out.append(s)
	return out


def propose_plan(ctx, args: dict) -> None:
	headline = (args.get("headline") or "Here's my plan").strip()
	sections = normalize_sections(args.get("sections"))
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


def clean_previews(raw, n_options: int) -> list[dict] | None:
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
					"For questions offering a DESIGN DIRECTION or a COLOUR PALETTE: one entry per "
					"option, each {colors: ['#hex', ...]} = that option's palette swatches (for a "
					"direction, use that direction's palette). One entry per option, in the same "
					"order. Omit for purely textual answers like the brand name."
				),
				"items": {
					"type": "object",
					"properties": {"colors": {"type": "array", "items": {"type": "string"}}},
				},
			},
		},
		"required": ["question"],
	},
	handler=ask_clarification,
)

propose_plan = Tool(
	name="propose_plan",
	side="terminal",
	description=(
		"Before building a NEW page or doing a major redesign, present a short plan and "
		"wait for the user to approve or refine it. The plan must EXPRESS the chosen design "
		"direction — its sections, copy, and layout should read unmistakably as that "
		"aesthetic, not a generic structure. Ends your turn. Never call this twice in a row: "
		"if a plan is already pending and the user approved it, call generate_page instead. "
		"Only re-propose when the user asked for changes."
	),
	parameters={
		"type": "object",
		"properties": {
			"headline": {
				"type": "string",
				"description": "One concrete line stating what the page is and who it's for — not a slogan.",
			},
			"sections": {
				"type": "string",
				"description": (
					"3–5 sections as ONE string, with each section on its OWN LINE (separate them with "
					"a newline). Do NOT send a JSON array. Make each line DECISION-USEFUL: the real "
					"headline/key copy it will use (in 'single quotes'), what's concretely in it (named "
					"items, not 'categories'), and the layout (e.g. 'full-bleed split, photo right'). "
					"Use single quotes for any quoted copy. Write real nouns and copy, never "
					"mood-adjective filler — do NOT use 'striking', 'clean', 'elegant', 'minimalist', "
					"'sleek', 'modern', or 'premium'. Example (two lines):\n"
					"Hero — deep-green full-bleed panel, headline 'Bring the forest home', sapling photo right, 'Shop the collection' button\n"
					"Story — two-column split, founder portrait left, 120-word origin note right"
				),
			},
			"palette": {"type": "string", "description": "Palette description with hex codes."},
		},
		"required": ["headline", "sections"],
	},
	handler=propose_plan,
)

TOOLS = [ask_clarification, propose_plan]
