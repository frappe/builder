import json
import re

import frappe
import yaml
from frappe import _


def classify_task(prompt: str, is_modify: bool = False, task_type: str | None = None) -> str:
	"""Classify task → simple (specific modify) | complex (general modify/full page)."""
	if is_modify and task_type in ["rewrite_text", "replace_image"]:
		return "simple"
	return "complex"


# ─── Model Selection & Cost Intelligence ──────────────────────────

MODEL_TIERS = {
	"openai": {"simple": "gpt-5.4-mini", "complex": "gpt-5.4"},
	"anthropic": {"simple": "claude-haiku-4-5", "complex": "claude-sonnet-4-6"},
	"google": {"simple": "gemini-3-flash", "complex": "gemini-3.1-pro"},
	"x-ai": {"simple": "grok-4.1-fast", "complex": "grok-4.1"},
}

MODEL_COST_INDEX = {
	"gpt-5.4-nano": 1,
	"gpt-5.4-mini": 2,
	"gpt-5.3-codex": 4,
	"gpt-5.4": 6,
	"claude-haiku-4-5": 1,
	"claude-sonnet-4-6": 4,
	# "claude-opus-4-6": 7,
	"gemini-3-flash": 2,
	"gemini-2.5-pro": 4,
	"gemini-3.1-pro": 6,
	"grok-4.1-fast": 1,
	"grok-4.1": 4,
	"grok-4.20": 6,
}

TASK_PARAMS = {
	"simple": {"max_tokens": 24000, "temperature": 0.5},
	"complex": {"max_tokens": 20000, "temperature": 0.7},
}

TIER_ORDER = ["simple", "complex"]


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
	provider = get_provider_from_model(configured_model)
	tier_map = MODEL_TIERS.get(provider)
	if not tier_map:
		return None

	configured_cost = MODEL_COST_INDEX.get(configured_model, 5)

	current_tier = None
	for tier in TIER_ORDER:
		if tier_map.get(tier) == current_model:
			current_tier = tier

	if current_tier is None or current_tier not in TIER_ORDER:
		return None

	for next_tier in TIER_ORDER[TIER_ORDER.index(current_tier) + 1 :]:
		next_model = tier_map.get(next_tier)
		if not next_model or next_model == current_model:
			continue
		if MODEL_COST_INDEX.get(next_model, 5) <= configured_cost:
			return next_model

	return None


# ─── Tiered System Prompts ────────────────────────────────────────

MODIFY_PROMPT = (
	"You modify web sections in Frappe Builder's block system.\n"
	"Return ONLY valid YAML array. No markdown, no explanations.\n\n"
	"# Schema\n"
	"el: str\n"
	"id: str # MUST preserve existing\n"
	"name?: str\n"
	"style?: dict # CSS-in-JS camelCase\n"
	"c?: [el]\n"
	"attrs?: dict\n"
	"text?: str\n"
	"m_style?: dict\n\n"
	"Rules: Preserve ALL existing 'id' values. Only change what requested. Return COMPLETE structure. "
	"Use %, rem for responsive widths. Top-level sections MUST be 100% width.\n"
	"Wrap text in semantic elements — never place text directly in div/section."
)

REWRITE_TEXT_PROMPT = (
	"You are a professional copywriter. Rewrite the text content in the provided block structure to be more engaging and professional.\n"
	"Return ONLY a valid YAML array. Preserve everything. Only update the 'text' property.\n"
	"No markdown, no explanations."
)

REPLACE_IMAGE_PROMPT = (
	"You are a visual design assistant. Suggest a highly relevant, high-quality image description or URL for the provided block.\n"
	"Return ONLY a valid YAML array. Preserve everything. Update 'attrs' property like 'src' and 'alt'.\n"
	"No markdown, no explanations."
)


def get_system_prompt_for_tier(task_tier: str, is_modify: bool, task_type: str | None = None) -> str:
	if is_modify:
		if task_type == "rewrite_text":
			return REWRITE_TEXT_PROMPT
		if task_type == "replace_image":
			return REPLACE_IMAGE_PROMPT
		return MODIFY_PROMPT
	return get_system_prompt()


# ─── Context Optimization ─────────────────────────────────────────

STYLE_KEYS_SIMPLE = frozenset(
	{
		"color",
		"backgroundColor",
		"background",
		"fontSize",
		"fontWeight",
		"fontStyle",
		"textDecoration",
		"opacity",
		"visibility",
		"padding",
		"paddingTop",
		"paddingRight",
		"paddingBottom",
		"paddingLeft",
		"margin",
		"marginTop",
		"marginRight",
		"marginBottom",
		"marginLeft",
		"border",
		"borderRadius",
		"borderColor",
		"borderWidth",
		"display",
		"width",
		"height",
		"maxWidth",
		"objectFit",
		"position",
		"zIndex",
		"boxShadow",
	}
)


def compress_block_to_dsl(block: dict, depth: int = 0, task_tier: str = "complex") -> dict:
	if not isinstance(block, dict):
		return block
	dsl = {}
	if block.get("element"):
		dsl["el"] = block["element"]
	if block.get("blockId"):
		dsl["id"] = block["blockId"]
	if block.get("blockName"):
		dsl["name"] = block["blockName"]

	if block.get("baseStyles") and isinstance(block.get("baseStyles"), dict):
		if task_tier == "simple":
			filtered = {k: v for k, v in block["baseStyles"].items() if k in STYLE_KEYS_SIMPLE}
		else:
			filtered = block["baseStyles"]
		if filtered:
			dsl["style"] = filtered

	if block.get("attributes") and isinstance(block.get("attributes"), dict):
		dsl["attrs"] = block["attributes"]
	if block.get("classes"):
		dsl["classes"] = block["classes"]

	if block.get("innerHTML"):
		dsl["text"] = block["innerHTML"]

	if task_tier == "complex" or depth <= 1:
		if block.get("mobileStyles") and isinstance(block.get("mobileStyles"), dict):
			dsl["m_style"] = block["mobileStyles"]
		if block.get("tabletStyles") and isinstance(block.get("tabletStyles"), dict):
			dsl["t_style"] = block["tabletStyles"]

	children = block.get("children", [])
	if children and isinstance(children, list):
		compressed_children = [
			compress_block_to_dsl(c, depth + 1, task_tier) for c in children if isinstance(c, dict)
		]
		if compressed_children:
			dsl["c"] = compressed_children

	return dsl


def strip_block_context(block_context: str, task_tier: str) -> str:
	"""Convert block JSON to compact YAML using a terse DSL to reduce input tokens."""
	try:
		data = json.loads(block_context)
	except (json.JSONDecodeError, TypeError):
		return block_context

	if isinstance(data, dict):
		data = [data]

	stripped = [compress_block_to_dsl(b, 0, task_tier) for b in data if isinstance(b, dict)]
	return yaml.dump(stripped, sort_keys=False, default_flow_style=False)


def expand_dsl_to_block(dsl_block: dict) -> dict:
	"""Expand compact DSL dictionary back to Frappe Builder block schema."""
	if not isinstance(dsl_block, dict):
		return dsl_block
	block = {
		"element": dsl_block.get("el", "div"),
		"blockName": dsl_block.get("name", ""),
		"baseStyles": dsl_block.get("style", {}),
		"attributes": dsl_block.get("attrs", {}),
	}
	if "id" in dsl_block:
		block["blockId"] = dsl_block["id"]
	if "text" in dsl_block:
		block["innerHTML"] = dsl_block["text"]
	if "m_style" in dsl_block:
		block["mobileStyles"] = dsl_block["m_style"]
	if "t_style" in dsl_block:
		block["tabletStyles"] = dsl_block["t_style"]
	if "classes" in dsl_block:
		block["classes"] = dsl_block["classes"]

	children = dsl_block.get("c", [])
	if children and isinstance(children, list):
		block["children"] = [expand_dsl_to_block(c) for c in children if isinstance(c, dict)]
	else:
		block["children"] = []

	return block


def build_user_message(prompt: str, task_tier: str, is_modify: bool, block_context: str | None = None) -> str:
	"""Build a token-efficient user message."""
	if is_modify and block_context:
		return f"Block:\n{block_context}\n\nChange: {prompt}"
	return f"Create a section for: {prompt}"


# ─── LLM Helpers ──────────────────────────────────────────────────


def _call_llm(model: str, messages: list, params: dict, *, stream: bool = True, api_key: str | None = None):
	"""Unified litellm call. Returns iterator (stream) or string (non-stream)."""
	import litellm

	if model.startswith("gemini-"):
		model = f"gemini/{model}"

	litellm.drop_params = True

	# For Anthropic: inject cache_control into the system message content block
	# so litellm forwards it correctly to Anthropic's caching layer.
	# For all other providers: pass messages unchanged.
	if "claude-" in model:
		for m in messages:
			if m["role"] == "system" and isinstance(m.get("content"), str):
				m["content"] = [{"type": "text", "text": m["content"]}]
				m["cache_control"] = {"type": "ephemeral"}

	kwargs = {
		"model": model,
		"messages": messages,
		"temperature": params["temperature"],
		"max_tokens": params["max_tokens"],
		"stream": stream,
		"api_key": api_key,
	}

	resp = litellm.completion(**kwargs)
	return resp if stream else (resp.choices[0].message.content or "")


def _parse_blocks(content: str) -> list[dict]:
	"""Parse LLM YAML output into block list and expand DSL. Raises on invalid output."""
	content = content.strip()
	if content.startswith("```"):
		content = re.sub(r"^```(?:yaml)?\s*\n?", "", content)
		content = re.sub(r"\n?```\s*$", "", content)
	content = content.strip()

	try:
		parsed = yaml.safe_load(content)
	except Exception as e:
		raise ValueError(f"YAML parsing failed: {e}")

	if isinstance(parsed, dict):
		blocks = [parsed]
	elif isinstance(parsed, list):
		blocks = [b for b in parsed if isinstance(b, dict)]
	else:
		raise ValueError("Not a valid block object")
	if not blocks:
		raise ValueError("No valid blocks in response")

	return [expand_dsl_to_block(b) for b in blocks]


def get_available_models():
	return [
		{
			"provider": "openai",
			"models": [
				{"name": "gpt-5.4", "label": "GPT-5.4 (Flagship)", "max_tokens": 1000000},
				{"name": "gpt-5.3-codex", "label": "GPT-5.3 Codex (Best Coding)", "max_tokens": 1000000},
				{"name": "gpt-5.4-mini", "label": "GPT-5.4 Mini (Fast)", "max_tokens": 1000000},
				{"name": "gpt-5.4-nano", "label": "GPT-5.4 Nano (Cheapest)", "max_tokens": 1000000},
			],
		},
		{
			"provider": "anthropic",
			"models": [
				# {"name": "claude-opus-4-6", "label": "Claude Opus 4.6 (Most Capable)", "max_tokens": 200000},
				{"name": "claude-sonnet-4-6", "label": "Claude Sonnet 4.6 (Balanced)", "max_tokens": 200000},
				{"name": "claude-haiku-4-5", "label": "Claude Haiku 4.5 (Fastest)", "max_tokens": 200000},
			],
		},
		{
			"provider": "google",
			"models": [
				{"name": "gemini-3.1-pro", "label": "Gemini 3.1 Pro (Flagship)", "max_tokens": 1048576},
				{"name": "gemini-2.5-pro", "label": "Gemini 2.5 Pro", "max_tokens": 1048576},
				{"name": "gemini-3-flash", "label": "Gemini 3 Flash (Fast)", "max_tokens": 1048576},
			],
		},
		{
			"provider": "x-ai",
			"models": [
				{"name": "grok-4.20", "label": "Grok 4.20 (Most Capable)", "max_tokens": 131072},
				{"name": "grok-4.1", "label": "Grok 4.1", "max_tokens": 131072},
				{"name": "grok-4.1-fast", "label": "Grok 4.1 Fast (Cheapest)", "max_tokens": 2000000},
			],
		},
	]


def get_system_prompt():
	"""Full system prompt for complex page generation."""
	return """You are an expert web designer specializing in creating modern, responsive web pages using the Frappe Builder block system.

Return ONLY a valid YAML array of blocks. No markdown, no explanations.

# Block Schema (Compact DSL):
- el: semantic HTML tag (section, div, nav, header, footer, h1-h3, p, span, button, a, img)
- name: descriptive name
- style: CSS-in-JS camelCase object (display, flexDirection, padding, margin, gap, backgroundColor, color, fontSize, fontWeight, width, minHeight, background, boxShadow, borderRadius, gridTemplateColumns, fontFamily)
- m_style: mobile overrides (fontSize, padding, flexDirection, etc.)
- t_style: tablet overrides
- attrs: HTML attrs (src, alt, href, target)
- text: text content
- c: nested blocks array
- classes: CSS class names

# Rules:
- Top-level sections MUST always have 'width: 100%'. Use flex/grid layouts.
- Modern harmonious color palettes
- Google Fonts via fontFamily in style (use ONLY the font name, e.g. "Bebas Neue" — do NOT add CSS fallback families)
- Responsive: %, rem, auto-fit units; add m_style overrides
- Semantic HTML with alt texts for images
- Consistent padding/margins
- Wrap text in semantic text elements (p, h1-h3, span, a) — never place text directly in div/section.

# CRITICAL: Return ONLY valid YAML array."""


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

		task_tier = classify_task(prompt, is_modify=False)
		optimal_model = get_optimal_model(model, task_tier)
		params = TASK_PARAMS[task_tier]
		should_stream = task_tier != "simple"
		tier_label = {"simple": "fast", "complex": "full"}[task_tier]

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
			{"role": "system", "content": system_prompt, "cache_control": {"type": "ephemeral"}},
			{"role": "user", "content": user_message},
		]

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

		try:
			blocks = _parse_blocks(content)
		except ValueError:
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

	except ValueError as e:
		frappe.log_error(f"Parse error: {e!s}\nContent: {content}", "AI Page Generation")
		frappe.publish_realtime(
			"ai_generation_error",
			{"page_id": page_id, "message": "Failed to parse AI response. The model returned invalid YAML."},
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




def modify_section_blocks(
	prompt: str,
	block_context: str,
	model: str,
	api_key: str | None = None,
	user: str | None = None,
	page_id: str | None = None,
	task_type: str | None = None,
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

		task_tier = classify_task(prompt, is_modify=True, task_type=task_type)
		optimal_model = get_optimal_model(model, task_tier)
		params = TASK_PARAMS[task_tier]
		should_stream = task_tier != "simple"
		stripped_context = strip_block_context(block_context, task_tier)
		tier_label = {"simple": "fast", "complex": "full"}[task_tier]

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

		system_prompt = get_system_prompt_for_tier(task_tier, is_modify=True, task_type=task_type)
		user_message = build_user_message(prompt, task_tier, is_modify=True, block_context=stripped_context)

		messages = [
			{"role": "system", "content": system_prompt, "cache_control": {"type": "ephemeral"}},
			{"role": "user", "content": user_message},
		]

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

		try:
			blocks = _parse_blocks(content)
		except ValueError:
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

	except ValueError as e:
		frappe.log_error(f"Parse error: {e!s}\nContent: {content}", "AI Section Modify")
		frappe.publish_realtime(
			"ai_modify_error",
			{"page_id": page_id, "message": "Failed to parse AI response. The model returned invalid YAML."},
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
def modify_section_from_prompt(
	prompt: str, block_context: str, page_id: str | None = None, task_type: str | None = None
):
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
		task_type=task_type,
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
