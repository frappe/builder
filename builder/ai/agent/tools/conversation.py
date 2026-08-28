"""Conversational UI primitive — the agent's way of pausing the loop to talk.

One terminal tool, `present_ui`: instead of hardcoded cards (a clarify card, a
plan card, …) the agent composes whatever the moment needs from a small set of
UI atoms — text, heading, list, swatches, image, choices, input, actions — and
the frontend has ONE generic renderer for them. The user's interaction comes
back as their next ordinary chat message, so approval/refinement is just
conversation, no magic strings.

The persisted message content is a plain-text rendering of the whole card:
that's what the model sees on replay, so it always knows exactly what it
offered (options, plan sections, buttons) without any per-card special-casing.
"""

import json
import re

import frappe

from builder.ai.agent.registry import Tool
from builder.ai.session import AISession

ELEMENT_KINDS = frozenset(
	{
		"text",
		"heading",
		"list",
		"swatches",
		"image",
		"choices",
		"input",
		"upload",
		"color_input",
		"actions",
		"divider",
		"note",
	}
)
MAX_ELEMENTS = 30
# A card is text, options and colours now, so this is a sanity bound rather than a
# real constraint — big enough that no honest multi-step card ever hits it.
MAX_UI_JSON = 24000


def run_present_ui(ctx, args: dict) -> str | None:
	text = (args.get("text") or "").strip()
	ui = sanitize_ui(args.get("ui"))
	# A choices group with zero usable options renders nothing tappable — the
	# turn would end on a dead card (seen live: 'more options' answered with an
	# empty options array). Bounce it back instead of stranding the user.
	if any(el.get("kind") == "choices" and not el.get("options") for el in ui):
		return (
			"FAILED: a choices group has no usable options — nothing renders and the user "
			"cannot answer. Every option must be an object like {label, description?, font?, "
			"svg?, colors?}. Call present_ui again with real options."
		)
	# Same dead end, reached the other way: everything sanitized away (unknown
	# kinds, or an oversized card trimmed to nothing). present_ui ends the turn,
	# so a card with no controls strands the user just as badly.
	if not ui:
		return (
			"FAILED: the card has no elements, so it renders as a question the user cannot "
			"answer. `ui` must be an ARRAY of element objects, e.g. "
			"[{'kind': 'choices', 'options': [...]}]. Call present_ui again with real elements."
		)
	content = render_ui_text(text, ui)
	metadata = {"status": "ui", "text": text, "ui": ui}
	if timeline := ctx.timeline():
		metadata["steps"] = timeline  # research done before asking survives a reload
	# after_commit: the event triggers a session reload on the client, which must
	# see this message already in the DB.
	AISession.try_append_message(
		ctx.session_id,
		"assistant",
		content,
		message_type="clarification",
		task_type="agent",
		metadata=metadata,
	)
	ctx.emit("clarify", question=text, ui=ui, after_commit=True)


def sanitize_ui(raw) -> list[dict]:
	"""Keep only dict elements with a known kind, capped in count and size —
	the renderer skips anything else anyway; this keeps garbage out of the DB."""
	# A single-element card often arrives as the bare element instead of a
	# one-item array (seen live: a fully-formed font-pairing choices group that
	# was dropped whole, leaving a question with nothing to tap).
	if isinstance(raw, dict):
		raw = [raw]
	if not isinstance(raw, list):
		return []
	elements = [e for e in raw if isinstance(e, dict) and e.get("kind") in ELEMENT_KINDS]
	elements = elements[:MAX_ELEMENTS]
	for el in elements:
		if el.get("kind") == "choices":
			sanitized = (sanitize_option(o) for o in el.get("options") or [])
			el["options"] = [o for o in sanitized if o]
		elif el.get("kind") == "color_input":
			el["colors"] = sanitize_color_slots(el.get("colors"))
	while elements and len(json.dumps(elements)) > MAX_UI_JSON:
		elements.pop()
	return elements


def sanitize_color_slots(colors) -> list[dict]:
	"""A color_input's role slots: [{label, hint?, value?}]. Keep dicts with a string
	label (tolerate bare-string slot names); `value` is a curated preset hex the card
	shows as the starting point — only a plain hex survives (anything else could reach
	an inline style). Cap the count so a card can't sprawl."""
	out = []
	for slot in colors or []:
		if isinstance(slot, str) and slot.strip():
			out.append({"label": slot.strip()[:60]})
		elif isinstance(slot, dict) and slot.get("label"):
			clean = {"label": str(slot["label"])[:60]}
			if slot.get("hint"):
				clean["hint"] = str(slot["hint"])[:120]
			value = str(slot.get("value") or "").strip()
			if re.fullmatch(r"#[0-9a-fA-F]{3,8}", value):
				clean["value"] = value
			out.append(clean)
	return out[:6]


def sanitize_option(option) -> dict | None:
	"""Normalize decorations to the shapes the renderer expects, dropping what
	can't be salvaged. A bare-string option becomes a plain labelled chip —
	dropping it would strand the card."""
	if isinstance(option, str) and option.strip():
		return {"label": option.strip()[:120]}
	if not isinstance(option, dict):
		return None
	if option.get("colors") is not None and not isinstance(option["colors"], list):
		option.pop("colors")
	if option.get("image") is not None and not isinstance(option["image"], str):
		option.pop("image")
	return option


def render_ui_text(text: str, ui: list[dict]) -> str:
	"""Plain-text rendering of the card — the message content the model sees on
	replay, and the fallback display for clients without the generic renderer."""
	lines = [text] if text else []
	for el in ui:
		lines.extend(render_element_text(el))
	return "\n".join(lines).strip() or "…"


def render_element_text(el: dict) -> list[str]:
	kind = el.get("kind")
	# A note is model-only: it lands in the persisted message (replay context)
	# but the renderer never shows it to the user.
	if kind in ("heading", "text", "note"):
		return [str(el.get("text") or "")]
	if kind == "list":
		return [f"- {i}" for i in el.get("items") or []]
	if kind == "swatches":
		colors = ", ".join(str(c) for c in el.get("colors") or [])
		return [f"[palette: {colors}]"] if colors else []
	if kind == "image":
		return [f"[image: {el.get('src') or ''}]"]
	if kind == "choices":
		return [option_text(o) for o in el.get("options") or []]
	if kind == "input":
		return [f"[input: {el.get('label') or el.get('placeholder') or 'text field'}]"]
	if kind == "upload":
		return [f"[upload: {el.get('label') or 'image'}]"]
	if kind == "color_input":
		slots = [s.get("label") for s in el.get("colors") or [] if isinstance(s, dict) and s.get("label")]
		roles = ", ".join(slots) if slots else (el.get("label") or "brand colours")
		return [f"[colour picker — {roles}]"]
	if kind == "actions":
		labels = " / ".join(str(b.get("label") or "") for b in el.get("buttons") or [])
		return [f"[buttons: {labels}]"] if labels else []
	return []


def option_text(option) -> str:
	if not isinstance(option, dict):
		return f"* {option}"
	label = option.get("label") or option.get("value") or ""
	desc = option.get("description") or ""
	line = f"* {label} — {desc}" if desc else f"* {label}"
	if option.get("image"):
		line += f" [image: {option['image']}]"
	return line


present_ui = Tool(
	name="present_ui",
	side="terminal",
	handler=run_present_ui,
	description=(
		"Show the user an interactive card composed from UI atoms, then END your turn and "
		"wait. This is your ONLY conversational UI — compose whatever the moment needs: a "
		"single question with tappable options, a plan for approval, a confirmation, a "
		"small form. Their interaction (option tapped, button clicked, text typed) arrives "
		"as their next ordinary message; free-typed text is an equally valid reply. "
		"Elements render in order. Interaction model: a lone single-select 'choices' "
		"submits on tap; 'input' fields and multi-select choices are collected and sent by "
		"an 'actions' button (always add one when using them). Keep cards focused — one "
		"decision per card. Only ask when you are genuinely blocked — never when the request "
		"references an existing page, image, or brand you can read: study the reference "
		"(theme variables / source) and derive the answer instead. Never "
		"re-present a plan the user already approved — build."
	),
	parameters={
		"type": "object",
		"properties": {
			"text": {
				"type": "string",
				"description": "The message above the card — the question being asked or what you're proposing. Short.",
			},
			"ui": {
				"type": "array",
				"description": (
					"UI elements, rendered in order. A card with more than ONE question renders "
					"as a MULTI-STEP form — one question per step — so give EVERY question atom "
					"(choices/input/color_input/upload) its own short `label`: it is that step's "
					"question, and it is what names the answer in the user's reply. The one "
					"exception is the FIRST question, which `text` already asks. Otherwise keep "
					"the card COMPACT: `text` renders above it, so never repeat the question as "
					"a heading. Kinds:\n"
					"{kind:'heading', text} — bold card heading (for plan titles etc., NEVER a "
					"restatement of `text`)\n"
					"{kind:'text', text} — paragraph (line breaks preserved)\n"
					"{kind:'list', items:[str]} — bulleted list (e.g. plan sections)\n"
					"{kind:'swatches', colors:['#hex'], label?} — colour palette row\n"
					"{kind:'image', src, caption?} — an image (site file or https URL)\n"
					"{kind:'choices', label?, multi?, options:[{label, description?, colors:['#hex']?, "
					"image:'https://…'?}]} — tappable option cards; single-select submits immediately, "
					"multi collects. An option's `colors` renders as a small palette strip. An "
					"option's `image` is a photo thumbnail URL (use the `thumb` from search_images) — "
					"for letting the user pick a hero/section photo; the chosen option's image URL "
					"comes back in their reply\n"
					"{kind:'input', label?, placeholder?} — one-line text field\n"
					"{kind:'upload', label?} — image-upload field (logo, their own photo); the "
					"uploaded file's URL arrives in their reply. Pair with an actions button, and "
					"usually alongside a choices card of found images as the 'or upload your own' "
					"escape hatch\n"
					"{kind:'color_input', label?, colors:[{label, hint?}]} — LABELLED colour slots the "
					"user fills with a picker, ONE per role so it's clear which colour goes WHERE. Give "
					"each slot a role label (e.g. 'Brand / Primary', 'Background', 'Accent', 'Text / Ink' "
					"— adapt to the brand) and an optional one-line hint; every slot is optional. The "
					"reply names each chosen colour by its role ('Brand: #C4552D, Background: #F4EFE8'). "
					"Pair with an actions button. Use early in a design flow — the colours the user "
					"assigns are LAW: use each one in the role they named, for that role, everywhere\n"
					"{kind:'note', text} — model-only context: persisted as part of your message "
					"(you'll see it on replay) but NEVER shown to the user. Put detailed working "
					"notes here (e.g. the full build brief behind a plan) so the visible card "
					"stays scannable\n"
					"{kind:'actions', buttons:[{label, variant:'primary'|'secondary'?}]} — "
					"submit buttons (e.g. 'Build it'); the clicked label + all collected "
					"values become the user's reply\n"
					"{kind:'divider'}"
				),
				"items": {"type": "object"},
			},
		},
		"required": ["text"],
	},
)

TOOLS = [present_ui]
