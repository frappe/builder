import json
import re

import frappe
from frappe import _

# ─── Task Classification ───────────────────────────────────────────

TRIVIAL_PATTERNS = [
	r"\b(change|update|rename|rephrase|reword|fix|correct|replace)\b.*\b(text|title|heading|label|typo|word|name|copy|content|string)\b",
	r"\b(change|update|set|make)\b.*\b(colou?r|font|size|bold|italic|underline|weight)\b",
	r"\b(change|update|set)\b.*\b(background|bg)\s*(colou?r)?\b",
	r"\bmake\s+(it\s+)?(bigger|smaller|larger|bolder|lighter|darker|brighter)\b",
]

SIMPLE_PATTERNS = [
	r"\b(add|insert|include|put)\b.*\b(button|link|icon|image|img|divider|spacer|badge|tag)\b",
	r"\b(change|update|set|adjust|modify|tweak)\b.*\b(padding|margin|spacing|gap|border|shadow|radius|opacity|alignment|align|width|height)\b",
	r"\b(center|left.?align|right.?align|justify)\b",
	r"\b(hide|show|remove|delete|toggle)\b.*\b(block|element|section|button|text|image|div)\b",
	r"\b(move|swap|reorder|rearrange)\b",
	r"\b(round|rounded|square|circle|pill)\b.*\b(corner|border|shape)\b",
]

COMPLEX_PATTERNS = [
	r"\b(create|build|generate|make|design)\b.*\b(page|landing|website|full|complete)\b",
	r"\b(from\s+scratch|entire|whole|complete|multi.?section)\b",
]


def classify_task(prompt: str, is_modify: bool = False) -> str:
	"""Classify prompt complexity → trivial | simple | moderate | complex."""
	lower = prompt.lower().strip()

	if not is_modify:
		for p in COMPLEX_PATTERNS:
			if re.search(p, lower):
				return "complex"
		return "moderate"

	for p in TRIVIAL_PATTERNS:
		if re.search(p, lower):
			return "trivial"
	for p in SIMPLE_PATTERNS:
		if re.search(p, lower):
			return "simple"
	for p in COMPLEX_PATTERNS:
		if re.search(p, lower):
			return "complex"
	return "moderate"


# ─── Model Selection & Cost Intelligence ──────────────────────────

MODEL_TIERS = {
	"openai": {"trivial": "gpt-5-nano", "simple": "gpt-4.1-mini", "moderate": "gpt-4.1", "complex": "gpt-5"},
	"anthropic": {
		"trivial": "claude-haiku-4-5",
		"simple": "claude-haiku-4-5",
		"moderate": "claude-sonnet-4-6",
		"complex": "claude-sonnet-4-6",
	},
	"google": {
		"trivial": "gemini-2.5-flash-lite",
		"simple": "gemini-2.5-flash",
		"moderate": "gemini-2.5-flash",
		"complex": "gemini-2.5-pro",
	},
	"x-ai": {
		"trivial": "grok-beta",
		"simple": "grok-beta",
		"moderate": "grok-2-1212",
		"complex": "grok-2-1212",
	},
}

MODEL_COST_INDEX = {
	"gpt-5-nano": 1,
	"gpt-5-mini": 2,
	"gpt-4.1-mini": 2,
	"o4-mini": 3,
	"gpt-4.1": 4,
	"gpt-5": 5,
	"o3": 6,
	"gpt-5.4": 7,
	"claude-haiku-4-5": 1,
	"claude-sonnet-4-6": 4,
	# "claude-opus-4-6": 7,
	"gemini-2.5-flash-lite": 1,
	"gemini-2.5-flash": 2,
	"gemini-2.5-pro": 5,
	"grok-beta": 2,
	"grok-2-1212": 4,
	"grok-2-vision-1212": 4,
}

TASK_PARAMS = {
	"trivial": {"max_tokens": 2000, "temperature": 0.3},
	"simple": {"max_tokens": 4000, "temperature": 0.5},
	"moderate": {"max_tokens": 18000, "temperature": 0.7},
	"complex": {"max_tokens": 20000, "temperature": 0.7},
}

TIER_ORDER = ["trivial", "simple", "moderate", "complex"]


def get_optimal_model(configured_model: str, task_tier: str) -> str:
	"""Pick the cheapest adequate model, capped at the user's configured model."""
	provider = get_provider_from_model(configured_model)
	tier_map = MODEL_TIERS.get(provider)
	if not tier_map:
		return configured_model
	optimal = tier_map.get(task_tier, configured_model)
	configured_cost = MODEL_COST_INDEX.get(configured_model, 5)
	optimal_cost = MODEL_COST_INDEX.get(optimal, 5)
	if optimal_cost > configured_cost:
		return configured_model
	return optimal


def get_escalated_model(current_model: str, configured_model: str) -> str | None:
	"""Next-tier fallback model, capped at configured model's cost."""
	provider = get_provider_from_model(current_model)
	tier_map = MODEL_TIERS.get(provider)
	if not tier_map:
		return None
	reverse_map = {v: k for k, v in tier_map.items()}
	current_tier = reverse_map.get(current_model)
	if not current_tier or current_tier not in TIER_ORDER:
		return None
	idx = TIER_ORDER.index(current_tier)
	if idx >= len(TIER_ORDER) - 1:
		return None
	next_model = tier_map.get(TIER_ORDER[idx + 1])
	if not next_model or next_model == current_model:
		return None
	configured_cost = MODEL_COST_INDEX.get(configured_model, 5)
	if MODEL_COST_INDEX.get(next_model, 5) > configured_cost:
		return configured_model if configured_model != current_model else None
	return next_model


# ─── Tiered System Prompts ────────────────────────────────────────

MINIMAL_MODIFY_PROMPT = (
	"You modify web sections in Frappe Builder's block system.\n"
	"Return ONLY valid JSON array. No markdown, no text. Start with [ end with ].\n\n"
	'Block: {"element":"tag","blockName":"n","blockId":"id","baseStyles":{...},'
	'"children":[...],"attributes":{...},"innerText":"t","mobileStyles":{...},"tabletStyles":{...}}\n\n'
	"Preserve all blockId values. Only change what was asked. Use camelCase CSS.\n"
	"Wrap text in semantic elements (p, h1-h3, span, a) — never place text directly in div/section."
)

FOCUSED_MODIFY_PROMPT = (
	"You modify web sections in Frappe Builder's block system.\n"
	"Return ONLY valid JSON array. No markdown, no explanations. Start with [ end with ].\n\n"
	"Block props: element, blockName, blockId, baseStyles (CSS-in-JS camelCase), "
	"mobileStyles, tabletStyles, attributes, innerText/innerHTML, children, classes.\n"
	'Style example: {"display":"flex","flexDirection":"column","padding":"2rem","backgroundColor":"#fff"}\n\n'
	"Rules: Preserve blockId values. Only change what requested. Return COMPLETE block structure. "
	"Use %, rem for responsive widths.\n"
	"Wrap text in semantic elements (p, h1-h3, span, a) — never place text directly in div/section."
)

COMPACT_GENERATION_PROMPT = (
	"You generate web sections using Frappe Builder's block system.\n"
	"Return ONLY valid JSON array. No markdown, no text. Start with [ end with ].\n\n"
	'Block: {"element":"section","blockName":"hero","baseStyles":{"display":"flex",'
	'"flexDirection":"column","padding":"2rem"},"children":[...],"attributes":{},'
	'"mobileStyles":{},"tabletStyles":{}}\n\n'
	"Elements: section, div, nav, header, footer, h1-h3, p, span, button, a, img\n"
	"Styles: CSS-in-JS camelCase \u2014 display, flexDirection, padding, margin, gap, "
	"backgroundColor, color, fontSize, fontWeight, width, minHeight, background, "
	"boxShadow, borderRadius, gridTemplateColumns\n"
	"Attributes: src, alt, href, target | Text: innerText or innerHTML\n\n"
	"Design: flex/grid layouts, 100% widths, modern colors, Google Fonts via fontFamily "
	'(use ONLY the font name e.g. "Bebas Neue" — never add fallback families like cursive or sans-serif), '
	"responsive mobileStyles overrides.\n"
	"Wrap text in semantic elements (p, h1-h3, span, a) — never place text directly in div/section."
)


def get_system_prompt_for_tier(task_tier: str, is_modify: bool) -> str:
	"""Select the most token-efficient prompt for the task tier."""
	if is_modify:
		if task_tier == "trivial":
			return MINIMAL_MODIFY_PROMPT
		if task_tier == "simple":
			return FOCUSED_MODIFY_PROMPT
		return get_modify_system_prompt()
	if task_tier in ("trivial", "simple"):
		return COMPACT_GENERATION_PROMPT
	return get_system_prompt()


# ─── Context Optimization ─────────────────────────────────────────


def strip_block_context(block_context: str, task_tier: str) -> str:
	"""Remove empty/default properties from block JSON to reduce input tokens."""
	try:
		data = json.loads(block_context)
	except (json.JSONDecodeError, TypeError):
		return block_context

	if isinstance(data, dict):
		data = [data]

	def _strip(block, depth=0):
		if not isinstance(block, dict):
			return block
		out = {}
		for k, v in block.items():
			if v is None:
				continue
			if isinstance(v, dict) and not v:
				continue
			if isinstance(v, list) and not v and k != "children":
				continue
			if isinstance(v, str) and not v and k not in ("innerText", "innerHTML"):
				continue
			if k == "children" and isinstance(v, list):
				children = [_strip(c, depth + 1) for c in v if isinstance(c, dict)]
				if children:
					out[k] = children
			else:
				out[k] = v
		if task_tier == "trivial" and depth > 1:
			out.pop("mobileStyles", None)
			out.pop("tabletStyles", None)
			out.pop("classes", None)
		return out

	stripped = [_strip(b) for b in data if isinstance(b, dict)]
	return json.dumps(stripped, separators=(",", ":"))


def build_user_message(prompt: str, task_tier: str, is_modify: bool, block_context: str | None = None) -> str:
	"""Build a token-efficient user message."""
	if is_modify and block_context:
		if task_tier in ("trivial", "simple"):
			return f"Block:\n{block_context}\n\nChange: {prompt}"
		return f"Current section:\n{block_context}\n\nModify: {prompt}"
	if task_tier in ("trivial", "simple"):
		return f"Create: {prompt}"
	return f"Create a section for: {prompt}"


# ─── LLM Helpers ──────────────────────────────────────────────────


def _call_llm(model: str, messages: list, params: dict, *, stream: bool = True, api_key: str | None = None):
	"""Unified litellm call. Returns iterator (stream) or string (non-stream)."""
	import litellm

	# Google AI Studio keys require the 'gemini/' provider prefix;
	# without it litellm routes to Vertex AI and demands ADC credentials.
	if model.startswith("gemini-"):
		model = f"gemini/{model}"

	litellm.drop_params = True
	kwargs = dict(
		model=model,
		messages=messages,
		temperature=params["temperature"],
		max_tokens=params["max_tokens"],
	)
	if api_key:
		kwargs["api_key"] = api_key
	if stream:
		return litellm.completion(**kwargs, stream=True)
	resp = litellm.completion(**kwargs, stream=False)
	return resp.choices[0].message.content or ""


def _parse_blocks(content: str) -> list[dict]:
	"""Parse LLM output into block list. Raises on invalid output."""
	content = content.strip()
	if content.startswith("```"):
		content = content.split("\n", 1)[1] if "\n" in content else content[3:]
		if content.endswith("```"):
			content = content[:-3].strip()
	parsed = json.loads(content)
	if isinstance(parsed, dict):
		blocks = [parsed]
	elif isinstance(parsed, list):
		blocks = [b for b in parsed if isinstance(b, dict)]
	else:
		raise ValueError("Not a valid block object")
	if not blocks:
		raise ValueError("No valid blocks in response")
	return blocks


def get_available_models():
	return [
		{
			"provider": "openai",
			"models": [
				{"name": "gpt-5.4", "label": "GPT-5.4 (Flagship)", "max_tokens": 1050000},
				{"name": "gpt-5", "label": "GPT-5 (Reasoning)", "max_tokens": 400000},
				{"name": "gpt-5-mini", "label": "GPT-5 Mini (Fast)", "max_tokens": 400000},
				{"name": "gpt-5-nano", "label": "GPT-5 Nano (Cheapest)", "max_tokens": 400000},
				{"name": "gpt-4.1", "label": "GPT-4.1", "max_tokens": 1047576},
				{"name": "gpt-4.1-mini", "label": "GPT-4.1 Mini", "max_tokens": 1047576},
				{"name": "o3", "label": "o3 (Reasoning)", "max_tokens": 200000},
				{"name": "o4-mini", "label": "o4-mini (Fast Reasoning)", "max_tokens": 200000},
			],
		},
		{
			"provider": "anthropic",
			"models": [
				{"name": "claude-sonnet-4-6", "label": "Claude Sonnet 4.6 (Latest)", "max_tokens": 200000},
				# {"name": "claude-opus-4-6", "label": "Claude Opus 4.6 (Most Capable)", "max_tokens": 200000},
				{"name": "claude-haiku-4-5", "label": "Claude Haiku 4.5 (Fastest)", "max_tokens": 200000},
			],
		},
		{
			"provider": "google",
			"models": [
				{"name": "gemini-2.5-pro", "label": "Gemini 2.5 Pro", "max_tokens": 1048576},
				{"name": "gemini-2.5-flash", "label": "Gemini 2.5 Flash", "max_tokens": 1048576},
				{"name": "gemini-2.5-flash-lite", "label": "Gemini 2.5 Flash-Lite", "max_tokens": 1048576},
			],
		},
		{
			"provider": "x-ai",
			"models": [
				{"name": "grok-beta", "label": "Grok Beta", "max_tokens": 131072},
				{"name": "grok-2-1212", "label": "Grok 2", "max_tokens": 131072},
				{"name": "grok-2-vision-1212", "label": "Grok 2 Vision", "max_tokens": 32768},
			],
		},
	]


def get_system_prompt():
	"""Full system prompt for complex page generation (moderate/complex tiers)."""
	return """You are an expert web designer specializing in creating modern, responsive web pages using the Frappe Builder block system.

Return ONLY a valid JSON array of blocks. No markdown, no explanations. Start with [ end with ].

# Block Structure:
- element: semantic HTML tag (section, div, nav, header, footer, h1-h3, p, span, button, a, img)
- blockName: descriptive name
- baseStyles: CSS-in-JS camelCase object (display, flexDirection, padding, margin, gap, backgroundColor, color, fontSize, fontWeight, width, minHeight, background, boxShadow, borderRadius, gridTemplateColumns, fontFamily)
- mobileStyles: mobile overrides (fontSize, padding, flexDirection, etc.)
- tabletStyles: tablet overrides
- attributes: HTML attrs (src, alt, href, target)
- innerText or innerHTML: text content
- children: nested blocks array
- classes: CSS class names

# Style Format:
{"display":"flex","flexDirection":"column","padding":"2rem","backgroundColor":"#ffffff"}

# Rules:
- Use flex/grid layouts with 100% widths
- Modern harmonious color palettes
- Google Fonts via fontFamily in baseStyles (use ONLY the font name, e.g. "Bebas Neue" — do NOT add CSS fallback families like cursive, sans-serif, etc.)
- Responsive: %, rem, auto-fit units; add mobileStyles overrides
- Semantic HTML with alt texts for images
- Consistent padding/margins
- Wrap text (innerText/innerHTML) in semantic text elements (p, h1-h3, span, a) — never place text directly in div/section.

# CRITICAL: Return ONLY valid JSON array. No markdown code blocks, no text outside the array."""


def generate_page_blocks(
	prompt: str,
	model: str,
	api_key: str | None = None,
	user: str | None = None,
	page_id: str | None = None,
):
	"""Smart page generation with auto model selection and fallback escalation."""
	user = user or frappe.session.user
	content = ""
	try:
		try:
			import litellm
		except ImportError:
			frappe.publish_realtime(
				"ai_generation_error",
				{"page_id": page_id, "message": "litellm is not installed. Run: pip install litellm"},
				user=user,
			)
			return

		if not api_key:
			api_key = get_api_key_for_model(model)

		if not api_key:
			frappe.publish_realtime(
				"ai_generation_error",
				{
					"page_id": page_id,
					"message": f"API key not configured for {model}. Configure in Settings \u2192 AI.",
				},
				user=user,
			)
			return

		# ── Smart routing ──
		task_tier = classify_task(prompt, is_modify=False)
		optimal_model = get_optimal_model(model, task_tier)
		params = TASK_PARAMS[task_tier]
		should_stream = task_tier in ("moderate", "complex")

		tier_label = {"trivial": "quick", "simple": "fast", "moderate": "standard", "complex": "full"}[
			task_tier
		]
		frappe.publish_realtime(
			"ai_generation_progress",
			{
				"page_id": page_id,
				"status": "generating",
				"message": f"Generating ({tier_label}) with {optimal_model}...",
				"task_tier": task_tier,
				"model_used": optimal_model,
			},
			user=user,
		)

		system_prompt = get_system_prompt_for_tier(task_tier, is_modify=False)
		user_message = build_user_message(prompt, task_tier, is_modify=False)
		messages = [
			{"role": "system", "content": system_prompt},
			{"role": "user", "content": user_message},
		]

		# ── LLM call (stream for complex, single-shot for simple) ──
		if should_stream:
			response = _call_llm(optimal_model, messages, params, stream=True, api_key=api_key)
			for chunk in response:
				delta = chunk.choices[0].delta.content
				if delta:
					content += delta
					frappe.publish_realtime(
						"ai_generation_stream",
						{"page_id": page_id, "chunk": delta},
						user=user,
					)
		else:
			content = _call_llm(optimal_model, messages, params, stream=False, api_key=api_key)

		# ── Parse with automatic escalation on failure ──
		try:
			blocks = _parse_blocks(content)
		except (json.JSONDecodeError, ValueError):
			escalated = get_escalated_model(optimal_model, model)
			if escalated and escalated != optimal_model:
				frappe.publish_realtime(
					"ai_generation_progress",
					{"page_id": page_id, "message": f"Refining with {escalated}..."},
					user=user,
				)
				next_idx = min(TIER_ORDER.index(task_tier) + 1, len(TIER_ORDER) - 1)
				next_tier = TIER_ORDER[next_idx]
				messages[0]["content"] = get_system_prompt_for_tier(next_tier, is_modify=False)
				content = _call_llm(
					escalated, messages, TASK_PARAMS[next_tier], stream=False, api_key=api_key
				)
				blocks = _parse_blocks(content)
			else:
				raise

		frappe.publish_realtime(
			"ai_generation_complete",
			{"page_id": page_id, "blocks": blocks, "model_used": optimal_model, "task_tier": task_tier},
			user=user,
		)

	except json.JSONDecodeError as e:
		frappe.log_error(f"JSON parse error: {e!s}\nContent: {content}", "AI Page Generation")
		frappe.publish_realtime(
			"ai_generation_error",
			{"page_id": page_id, "message": "Failed to parse AI response. The model returned invalid JSON."},
			user=user,
		)

	except Exception as e:
		frappe.log_error(f"AI generation error: {e!s}", "AI Page Generation")
		frappe.publish_realtime(
			"ai_generation_error",
			{"page_id": page_id, "message": f"Failed to generate page: {e!s}"},
			user=user,
		)


def get_api_key_for_model(model: str) -> str | None:
	"""Get API key from site config based on model provider"""
	provider = get_provider_from_model(model)

	key_mapping = {
		"openai": "openai_api_key",
		"anthropic": "anthropic_api_key",
		"google": "google_api_key",
		"x-ai": "xai_api_key",
	}

	config_key = key_mapping.get(provider)
	if config_key:
		return frappe.conf.get(config_key)

	return None


def get_provider_from_model(model: str) -> str:
	"""Determine provider from model name."""
	if model.startswith(("gpt-", "chatgpt-", "o1", "o3", "o4")):
		return "openai"
	elif model.startswith("claude-"):
		return "anthropic"
	elif model.startswith("gemini-"):
		return "google"
	elif model.startswith("grok-"):
		return "x-ai"
	else:
		return "openai"  # default


def set_api_key_for_provider(model: str, api_key: str):
	"""Set API key in environment for litellm"""
	import os

	provider = get_provider_from_model(model)

	key_mapping = {
		"openai": "OPENAI_API_KEY",
		"anthropic": "ANTHROPIC_API_KEY",
		"google": "GEMINI_API_KEY",
		"x-ai": "XAI_API_KEY",
	}

	env_key = key_mapping.get(provider)
	if env_key:
		os.environ[env_key] = api_key


def get_modify_system_prompt():
	"""Full system prompt for complex section modification (moderate/complex tiers)."""
	return """You are an expert web designer specializing in modifying web page sections using the Frappe Builder block system.

Modify the existing block structure based on user instructions. Return ONLY a valid JSON array of the modified blocks. No markdown, no explanations.

# Block Structure:
- element, blockName, blockId, baseStyles (CSS-in-JS camelCase), mobileStyles, tabletStyles
- attributes (src, alt, href, target), innerText/innerHTML, children, classes

# Modification Rules:
1. Preserve ALL existing blockId values to prevent DOM churn
2. Only modify what the user explicitly asks for
3. Keep existing structure intact where not asked to change
4. Return the COMPLETE modified block structure (not a diff)
5. Use responsive units (%, rem, auto-fit) for widths
6. Style format: {"display":"flex","flexDirection":"column","padding":"2rem"}
7. Wrap text (innerText/innerHTML) in semantic text elements (p, h1-h3, span, a) — never place text directly in div/section

# CRITICAL: Return ONLY valid JSON array. Start with [ end with ]."""


def modify_section_blocks(
	prompt: str,
	block_context: str,
	model: str,
	api_key: str | None = None,
	user: str | None = None,
	page_id: str | None = None,
):
	"""Smart section modification with context stripping and auto model selection."""
	user = user or frappe.session.user
	content = ""
	try:
		try:
			import litellm
		except ImportError:
			frappe.publish_realtime(
				"ai_modify_error",
				{"page_id": page_id, "message": "litellm is not installed. Run: pip install litellm"},
				user=user,
			)
			return

		if not api_key:
			api_key = get_api_key_for_model(model)

		if not api_key:
			frappe.publish_realtime(
				"ai_modify_error",
				{
					"page_id": page_id,
					"message": f"API key not configured for {model}. Configure in Settings \u2192 AI.",
				},
				user=user,
			)
			return

		# ── Smart routing ──
		task_tier = classify_task(prompt, is_modify=True)
		optimal_model = get_optimal_model(model, task_tier)
		params = TASK_PARAMS[task_tier]
		should_stream = task_tier in ("moderate", "complex")

		# Strip context to save tokens
		stripped_context = strip_block_context(block_context, task_tier)

		tier_label = {"trivial": "quick", "simple": "fast", "moderate": "standard", "complex": "full"}[
			task_tier
		]
		frappe.publish_realtime(
			"ai_modify_progress",
			{
				"page_id": page_id,
				"status": "generating",
				"message": f"Modifying ({tier_label}) with {optimal_model}...",
				"task_tier": task_tier,
				"model_used": optimal_model,
			},
			user=user,
		)

		system_prompt = get_system_prompt_for_tier(task_tier, is_modify=True)
		user_message = build_user_message(prompt, task_tier, is_modify=True, block_context=stripped_context)
		messages = [
			{"role": "system", "content": system_prompt},
			{"role": "user", "content": user_message},
		]

		# ── LLM call (stream for complex, single-shot for simple) ──
		if should_stream:
			response = _call_llm(optimal_model, messages, params, stream=True, api_key=api_key)
			for chunk in response:
				delta = chunk.choices[0].delta.content
				if delta:
					content += delta
					frappe.publish_realtime(
						"ai_modify_stream",
						{"page_id": page_id, "chunk": delta},
						user=user,
					)
		else:
			content = _call_llm(optimal_model, messages, params, stream=False, api_key=api_key)

		# ── Parse with automatic escalation on failure ──
		try:
			blocks = _parse_blocks(content)
		except (json.JSONDecodeError, ValueError):
			escalated = get_escalated_model(optimal_model, model)
			if escalated and escalated != optimal_model:
				frappe.publish_realtime(
					"ai_modify_progress",
					{"page_id": page_id, "message": f"Refining with {escalated}..."},
					user=user,
				)
				next_idx = min(TIER_ORDER.index(task_tier) + 1, len(TIER_ORDER) - 1)
				next_tier = TIER_ORDER[next_idx]
				messages[0]["content"] = get_system_prompt_for_tier(next_tier, is_modify=True)
				content = _call_llm(
					escalated, messages, TASK_PARAMS[next_tier], stream=False, api_key=api_key
				)
				blocks = _parse_blocks(content)
			else:
				raise

		frappe.publish_realtime(
			"ai_modify_complete",
			{"page_id": page_id, "blocks": blocks, "model_used": optimal_model, "task_tier": task_tier},
			user=user,
		)

	except json.JSONDecodeError as e:
		frappe.log_error(f"JSON parse error: {e!s}\nContent: {content}", "AI Section Modify")
		frappe.publish_realtime(
			"ai_modify_error",
			{"page_id": page_id, "message": "Failed to parse AI response. The model returned invalid JSON."},
			user=user,
		)

	except Exception as e:
		frappe.log_error(f"AI modify error: {e!s}", "AI Section Modify")
		frappe.publish_realtime(
			"ai_modify_error",
			{"page_id": page_id, "message": f"Failed to modify section: {e!s}"},
			user=user,
		)


@frappe.whitelist()
def get_ai_models():
	return get_available_models()


@frappe.whitelist()
def modify_section_from_prompt(prompt: str, block_context: str, page_id: str | None = None):
	if not frappe.has_permission("Builder Page", ptype="write"):
		frappe.throw(_("You do not have permission to modify pages"))

	try:
		json.loads(block_context)
	except json.JSONDecodeError:
		frappe.throw(_("Invalid block context JSON"))

	settings = frappe.get_single("Builder Settings")
	model = settings.get("ai_model")
	api_key = settings.get_password("ai_api_key", raise_exception=False)

	if not model:
		frappe.throw(_("Please configure an AI model in Settings → AI"))

	user = frappe.session.user

	frappe.enqueue(
		modify_section_blocks,
		prompt=prompt,
		block_context=block_context,
		model=model,
		api_key=api_key,
		user=user,
		page_id=page_id,
		queue="default",
		is_async=True,
	)

	return {
		"status": "started",
		"message": _("Section modification started"),
	}


@frappe.whitelist()
def generate_page_from_prompt(prompt: str, page_id: str | None = None):
	if not frappe.has_permission("Builder Page", ptype="write"):
		frappe.throw(_("You do not have permission to generate pages"))

	settings = frappe.get_single("Builder Settings")
	model = settings.get("ai_model")
	api_key = settings.get_password("ai_api_key", raise_exception=False)

	if not model:
		frappe.throw(_("Please configure an AI model in Settings → AI"))

	user = frappe.session.user

	frappe.enqueue(
		generate_page_blocks,
		prompt=prompt,
		model=model,
		api_key=api_key,
		user=user,
		page_id=page_id,
	)

	return {
		"status": "started",
		"message": _("Page generation started"),
	}


@frappe.whitelist()
def test_api_key(model: str, api_key: str):
	"""Test if an API key is valid"""
	try:
		import litellm

		# Make a simple test call
		test_model = f"gemini/{model}" if model.startswith("gemini-") else model
		litellm.drop_params = True
		litellm.completion(
			model=test_model,
			messages=[{"role": "user", "content": "Say 'OK' if you can read this"}],
			max_tokens=10,
			api_key=api_key,
		)

		return {
			"success": True,
			"message": _("API key is valid"),
		}

	except Exception as e:
		return {
			"success": False,
			"message": str(e),
		}
