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
		"svg",
		"choices",
		"input",
		"upload",
		"actions",
		"divider",
		"note",
	}
)
MAX_ELEMENTS = 30
# Roomy enough for a few small inline-SVG layout sketches; the tool description
# tells the model to keep sketches tiny.
MAX_UI_JSON = 24000


def run_present_ui(ctx, args: dict) -> None:
	text = (args.get("text") or "").strip()
	ui = sanitize_ui(args.get("ui"))
	content = render_ui_text(text, ui)
	metadata = {"status": "ui", "text": text, "ui": ui}
	if ctx.activity:
		metadata["activity"] = ctx.activity  # research done before asking survives a reload
	# Persist + commit BEFORE emitting: the realtime event triggers a session
	# reload on the client, which must see this message already in the DB.
	AISession.try_append_message(
		ctx.session_id,
		"assistant",
		content,
		message_type="clarification",
		task_type="agent",
		metadata=metadata,
	)
	frappe.db.commit()
	ctx.emit("clarify", question=text, ui=ui)


def sanitize_ui(raw) -> list[dict]:
	"""Keep only dict elements with a known kind, capped in count and size —
	the renderer skips anything else anyway; this keeps garbage out of the DB."""
	if not isinstance(raw, list):
		return []
	elements = [e for e in raw if isinstance(e, dict) and e.get("kind") in ELEMENT_KINDS]
	elements = elements[:MAX_ELEMENTS]
	for el in elements:
		if el.get("kind") == "choices":
			el["options"] = [sanitize_option(o) for o in el.get("options") or [] if isinstance(o, dict)]
	while elements and len(json.dumps(elements)) > MAX_UI_JSON:
		elements.pop()
	return elements


def sanitize_option(option: dict) -> dict:
	"""Normalize decorations to the shapes the renderer expects, dropping what
	can't be salvaged (models emit font as a dict, a 'Heading + Body' string, or
	even a bare number — be liberal in what we accept)."""
	if "font" in option:
		font = coerce_font(option.pop("font"))
		if font:
			option["font"] = font
	# A font option without a label (models lean on the specimen) would submit
	# an empty tap-reply — name it after its pairing.
	if not option.get("label") and isinstance(option.get("font"), dict):
		option["label"] = " + ".join(
			v for v in (option["font"].get("heading"), option["font"].get("body")) if v
		)
	if option.get("colors") is not None and not isinstance(option["colors"], list):
		option.pop("colors")
	if option.get("svg") is not None and not isinstance(option["svg"], str):
		option.pop("svg")
	if option.get("image") is not None and not isinstance(option["image"], str):
		option.pop("image")
	return option


def coerce_font(font) -> dict | None:
	"""Accept {heading, body} or a 'Heading + Body' string; None for anything else."""
	if isinstance(font, dict):
		pair = {k: font[k] for k in ("heading", "body") if isinstance(font.get(k), str) and font[k].strip()}
		return pair or None
	if isinstance(font, str):
		parts = [p.strip() for p in re.split(r"\s*[+/|]\s*", font) if p.strip()]
		if not parts:
			return None
		pair = {"heading": parts[0]}
		if len(parts) > 1:
			pair["body"] = parts[1]
		return pair
	return None


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
	if kind == "svg":
		return [f"[sketch: {el.get('caption')}]"] if el.get("caption") else ["[sketch]"]
	if kind == "choices":
		return [option_text(o) for o in el.get("options") or []]
	if kind == "input":
		return [f"[input: {el.get('label') or el.get('placeholder') or 'text field'}]"]
	if kind == "upload":
		return [f"[upload: {el.get('label') or 'image'}]"]
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
	font = option.get("font")
	if isinstance(font, dict) and (font.get("heading") or font.get("body")):
		line += f" [fonts: {font.get('heading') or '—'} + {font.get('body') or '—'}]"
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
		"(read_page / theme variables / source) and derive the answer instead. Never "
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
					"UI elements, rendered in order. Kinds:\n"
					"{kind:'heading', text} — bold card heading\n"
					"{kind:'text', text} — paragraph (line breaks preserved)\n"
					"{kind:'list', items:[str]} — bulleted list (e.g. plan sections)\n"
					"{kind:'swatches', colors:['#hex'], label?} — colour palette row\n"
					"{kind:'image', src, caption?} — an image (site file or https URL)\n"
					"{kind:'svg', svg, caption?} — small inline-SVG figure (sanitized; no scripts)\n"
					"{kind:'choices', label?, multi?, options:[{label, description?, colors:['#hex']?, "
					"svg:'<svg…>'?, font:'Fraunces + DM Sans'?, image:'https://…'?}]} — tappable option cards; "
					"single-select submits immediately, multi collects. An option's `svg` is a "
					"MINIMAL layout sketch: abstract wireframe of flat rects/lines in that option's "
					"palette on its background colour, viewBox='0 0 120 80', no words, <15 shapes — it "
					"must make the layout difference between options visible at a glance. An option's "
					"`font` is a STRING: the exact Google Font names of that option's heading and body "
					"faces joined by ' + ' — the card renders a live type specimen in the real fonts, "
					"so the user sees the typography they're picking. An option's `image` is a "
					"photo thumbnail URL (use the `thumb` from search_images) — for letting the "
					"user pick a hero/section photo; the chosen option's image URL comes back in "
					"their reply\n"
					"{kind:'input', label?, placeholder?} — one-line text field\n"
					"{kind:'upload', label?} — image-upload field (logo, their own photo); the "
					"uploaded file's URL arrives in their reply. Pair with an actions button, and "
					"usually alongside a choices card of found images as the 'or upload your own' "
					"escape hatch\n"
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
