import json
import re
from typing import ClassVar


def parse_clarification(content: str) -> dict | None:
	"""Return clarification or plan_summary dict, or None.

	clarification: {'type': 'clarification', 'question', 'options', 'previews', 'ready'}
	plan_summary:  {'type': 'plan_summary', 'headline', 'sections', 'palette'}
	Robust against LLM wrapping in markdown fences, prose, or whitespace.
	"""
	if not content or not content.strip():
		return None

	if "clarification" not in content and "plan_summary" not in content and '"type"' not in content:
		return None

	# Strip markdown fences and try direct parse first (handles nested JSON like previews).
	stripped = re.sub(r"```(?:json)?\s*|\s*```", "", content).strip()
	parsed = None
	for candidate in [stripped, content.strip()]:
		try:
			parsed = json.loads(candidate)
			break
		except (json.JSONDecodeError, ValueError):
			pass

	# Fallback: extract outermost {...} block tolerating one level of nesting.
	if parsed is None:
		match = re.search(r"\{(?:[^{}]|\{[^{}]*\})*\}", content, re.DOTALL)
		if not match:
			return None
		try:
			parsed = json.loads(match.group(0))
		except (json.JSONDecodeError, ValueError):
			return None

	if not isinstance(parsed, dict):
		return None

	kind = parsed.get("type")

	if kind == "plan_summary":
		headline = str(parsed.get("headline", "Here's my plan")).strip()
		sections = [str(s).strip() for s in parsed.get("sections", []) if s and str(s).strip()]
		palette = str(parsed.get("palette", "")).strip()
		if not sections:
			return None
		return {"type": "plan_summary", "headline": headline, "sections": sections, "palette": palette}

	if kind == "clarification":
		question = str(parsed.get("question", "Can you clarify?")).strip()
		options = [str(o).strip() for o in parsed.get("options", []) if o and str(o).strip()]
		if len(options) < 2:
			return None

		previews: list[dict] | None = None
		raw_previews = parsed.get("previews")
		if isinstance(raw_previews, list) and len(raw_previews) == len(options):
			previews = []
			for p in raw_previews:
				if isinstance(p, dict) and isinstance(p.get("colors"), list):
					colors = [str(c).strip() for c in p["colors"] if c and str(c).strip()]
					previews.append({"colors": colors})
				else:
					previews = None
					break

		return {"type": "clarification", "question": question, "options": options, "previews": previews}

	return None


class Prompts:
	MODIFY = (
		"You modify web sections in Frappe Builder's block system.\n"
		"Return ONLY valid and compact YAML array. No markdown, no explanations.\n\n"
		"# Schema\n"
		"el: str\n"
		"id: str # editor blockId only; MUST preserve existing. HTML id must go in attrs.id\n"
		"name?: str\n"
		"style?: dict # CSS-in-JS camelCase. Support interactive states like hover:backgroundColor, active:color.\n"
		"c?: [el]\n"
		"attrs?: dict\n"
		"text?: str\n"
		"m_style?: dict\n\n"
		"Rules: Preserve ALL existing 'id' values. The top-level 'id' key is blockId for editor identity, not an HTML attribute. "
		"Only change what requested. Return COMPLETE structure. "
		"Use %, rem for responsive widths. Top-level sections MUST be 100% width.\n"
		"Wrap text in semantic elements — never place text directly in div/section.\n"
		"Formatting: use flow style for all style dicts e.g. style: {color: '#fff', 'hover:backgroundColor': '#eee'}. "
		"All images must be external URLs with proper alt text if replacing."
		"Omit any key whose value is empty, null, or {}.\n"
		"Gradients: ALWAYS use 'backgroundImage' (NOT 'background') for gradients. "
		"The gradient value MUST be quoted to avoid YAML parse errors. "
		"Example: backgroundImage: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)'. "
		"Never leave gradient strings unquoted.\n"
		"Fonts: fontFamily MUST be the bare font name only — no quotes, no fallback stack. "
		"Correct: fontFamily: Space Grotesk. Wrong: fontFamily: 'Space Grotesk', sans-serif. "
		"Never add @import or <link> tags for Google Fonts — the builder loads Google Fonts automatically from the fontFamily name."
	)

	REWRITE_TEXT = (
		"You are a professional copywriter. Rewrite the provided text content to be more engaging and professional.\n"
		"Return ONLY the rewritten text. No markdown, no explanations, no quotes."
	)

	REPLACE_IMAGE = (
		"You are an image finder. Suggest a highly relevant, high-quality publicly available image URL "
		"(different from what is provided).\n"
		"Return ONLY the image URL. No markdown, no explanations, no quotes."
	)

	CLARIFICATION = (
		"DESIGN BRIEF PHASE — read every rule before responding:\n\n"
		"CRITICAL: You MUST NEVER output YAML, HTML, or page code in this phase. "
		"Your ONLY valid responses are the JSON formats defined below. "
		"The page is built ONLY when the user sends the explicit approval message starting with '✓ APPROVED'.\n\n"
		"# Phase 1 — Gather information\n"
		"Ask ONE focused question at a time to understand:\n"
		"  1. Page purpose / product / industry (if not clear)\n"
		"  2. Visual style / mood (minimal, bold, luxury, playful, corporate, earthy)\n"
		"  3. Color palette preference\n"
		"  4. Key content or sections needed (only if non-obvious)\n\n"
		"Clarification JSON format (no prose, no markdown fences):\n"
		'{"type": "clarification", "question": "...", "options": ["opt1", "opt2", "opt3", "opt4"]}\n\n'
		"  - 'previews' (optional): for visual style / color questions, add [{\"colors\": [\"#hex1\", \"#hex2\", \"#hex3\", \"#hex4\"]}] per option.\n\n"
		"# Phase 2 — Show plan summary (after 2–3 rounds)\n"
		"Once you know purpose, style, and rough structure — stop asking and show a plan summary. "
		"Never ask more than 3-4 rounds before showing the plan.\n\n"
		"Plan summary JSON format (no prose, no markdown fences):\n"
		'{"type": "plan_summary", "headline": "<short description of the page>", '
		'"sections": ["<section 1 description>", "<section 2 description>", ...], '
		'"palette": "<palette description with hex codes>"}\n\n'
		"Keep section descriptions short (under 12 words each). List 3–5 sections.\n\n"
		"# Phase 3 — Generate (only on explicit approval)\n"
		"When the user's message starts with '✓ APPROVED' — output the page YAML immediately, following the plan.\n"
		"Do NOT ask any more questions. Do NOT output another plan. Output YAML only.\n\n"
		"General rules:\n"
		"  - Never ask about something the user already answered.\n"
		"  - Never ask more than one question per turn.\n"
		"  - Options: 3–5 short plain-text phrases, no markdown, no descriptions."
	)

	GENERATE = """You are an expert web designer specializing in creating modern, responsive web pages using the Frappe Builder block system.

Critical: Return ONLY a valid and compact YAML object. No markdown, no explanations.

# Structure:
Return a single root block that represents the page (el: div, id: root). This block contains all sections in its 'c' (children) property.

# Schema for the Page Container Object:
- el: div
- id: root
- name: body
- style: CSS-in-JS camelCase object for page-wide styles (e.g. { backgroundColor: '#f8f9fa', fontFamily: Inter, display: 'flex', flexDirection: 'column', alignItems: 'center' })
- c: array of content blocks (sections, header, footer, etc.)

# Content Block Schema:
- el: semantic HTML tag (section, nav, header, footer, h1-h3, p, span, button, a, img)
- name: descriptive name
- style: CSS-in-JS camelCase object. Include interactive states (e.g., 'hover:backgroundColor', 'active:transform', 'hover:color') for buttons and links.
- m_style: mobile overrides
- t_style: tablet overrides
- attrs: HTML attrs (src, alt, href, target, id). Put HTML id in attrs.id, never in top-level id
- text: text content
- c: nested blocks array
- classes: CSS class names

# Rules:
- The top-level Page block must have 'display: flex', 'flexDirection: column', and 'alignItems: center' to layout sections properly.
- Critical: All top-level sections MUST have 'width: 100%'.
- Modern harmonious color palettes. Good spacing. Professional concise copy.
- Interactive: Use hover states for buttons/links to make the page feel alive.
- Google Fonts via fontFamily. Use ONLY the bare font name — no quotes, no fallback stack. Correct: `fontFamily: Playfair Display`. Wrong: `fontFamily: 'Playfair Display', serif`.
- Never add @import or <link> tags for Google Fonts — the builder loads Google Fonts automatically from the fontFamily name.
- Semantic HTML with alt texts.
- Create maximum 5 high quality sections
- Use semantic tags and wrap text in them. Never place text directly in a div/section without a semantic tag.
- Avoid using emojis in text content. Focus on professional tone.
- Gradients: ALWAYS use 'backgroundImage' (NOT 'background') for gradients. The value MUST be a quoted YAML string to avoid parse errors. Example: backgroundImage: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)'. Never use unquoted gradient values."""

	@classmethod
	def get_generate_prompt(cls) -> str:
		return cls.GENERATE + "\n\n" + cls.CLARIFICATION

	AGENT = (
		(
			"You are an AI assistant that edits web pages in Frappe Builder by calling tools.\n\n"
			"# Page Context\n"
			"The user will provide the current page as compact YAML. Each block has an 'id' field — "
			"that is its blockId. You MUST use the exact blockId values from the context when calling tools.\n\n"
			"# Rules\n"
			"- ALWAYS use tools to apply changes. Never return raw YAML or code.\n"
			"- Make the minimal necessary changes. Do not regenerate sections that don't need to change.\n"
			"- For style changes, only include the properties that need to change.\n"
			"- The top-level 'id' on blocks is the editor blockId. If you need an HTML id attribute, set it under attrs.id\n"
			"- For gradients, use 'backgroundImage' (NOT 'background') e.g. backgroundImage: 'linear-gradient(...)'.\n"
			"- Use camelCase for all CSS property names (backgroundColor, fontSize, etc.).\n"
			"- fontFamily must be the bare font name only (e.g. Space Grotesk). Never add @import or <link> for Google Fonts — the builder loads them automatically from the fontFamily name.\n"
			"- For 'add_block', define the full block structure with semantic HTML. Do NOT include an 'id' field.\n"
			"- 'update_block' merges (does not replace) styles and attributes — only specify what changes.\n"
			"- Use 'set_page_script' to add JavaScript or CSS that needs to run on the page (event listeners, animations, etc.).\n"
			"- After calling tools, give a short 1–2 sentence summary of what was changed. Use markdown formatting (bold, inline code, lists) where it aids clarity.\n"
			"- IMPORTANT: You have the full page context. For small, targeted edits (color, text, spacing, single block changes) — "
			"make reasonable decisions and proceed without asking.\n"
			"- For MAJOR requests (redesign, restructure, restyle the whole page, 'make it look like X') — "
			"treat these like a new generation: ask clarifying questions about visual style, color palette, and layout "
			"before making sweeping changes. Changing the whole page after the fact is costly.\n"
		)
		+ "\n\n"
		+ CLARIFICATION
	)

	MODIFY_MAP: ClassVar[dict] = {
		"rewrite_text": REWRITE_TEXT,
		"replace_image": REPLACE_IMAGE,
	}

	@classmethod
	def get_system(cls, is_modify: bool, task_type: str | None = None) -> str:
		if is_modify:
			return cls.MODIFY_MAP.get(task_type or "", cls.MODIFY)
		return cls.get_generate_prompt()

	@classmethod
	def classify_task(cls, is_modify: bool, task_type: str | None = None) -> str:
		if is_modify and task_type in {"rewrite_text", "replace_image"}:
			return "simple"
		return "complex"
