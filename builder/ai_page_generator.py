import json
import re

import frappe
import litellm
import yaml
from frappe import _

from builder.utils import to_compact_yaml

TASK_PARAMS = {
	"simple": {"max_tokens": 1000, "temperature": 0.5},
	"complex": {"max_tokens": 16000, "temperature": 0.7},
}

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


# System Prompts

MODIFY_PROMPT = (
	"You modify web sections in Frappe Builder's block system.\n"
	"Return ONLY valid YAML array. No markdown, no explanations.\n\n"
	"# Schema\n"
	"el: str\n"
	"id: str # MUST preserve existing\n"
	"name?: str\n"
	"style?: dict # CSS-in-JS camelCase. Support interactive states like hover:backgroundColor, active:color.\n"
	"c?: [el]\n"
	"attrs?: dict\n"
	"text?: str\n"
	"m_style?: dict\n\n"
	"Rules: Preserve ALL existing 'id' values. Only change what requested. Return COMPLETE structure. "
	"Use %, rem for responsive widths. Top-level sections MUST be 100% width.\n"
	"Wrap text in semantic elements — never place text directly in div/section.\n"
	"Formatting: use flow style for all style dicts e.g. style: {color: '#fff', 'hover:backgroundColor': '#eee'}. "
	"All images must be external URLs with proper alt text if replacing."
	"Omit any key whose value is empty, null, or {}."
)

REWRITE_TEXT_PROMPT = (
	"You are a professional copywriter. Rewrite the provided text content to be more engaging and professional.\n"
	"Return ONLY the rewritten text. No markdown, no explanations, no quotes."
)

REPLACE_IMAGE_PROMPT = (
	"You are an image finder. Suggest a highly relevant, high-quality publicly available image URL "
	"(different from what is provided).\n"
	"Return ONLY the image URL. No markdown, no explanations, no quotes."
)

GENERATE_PROMPT = """You are an expert web designer specializing in creating modern, responsive web pages using the Frappe Builder block system.

Return ONLY a valid YAML object. No markdown, no explanations.

# Structure:
Return a single root block that represents the page (el: div, id: root). This block contains all sections in its 'c' (children) property.

# Schema for the Page Container Object:
- el: div
- id: root
- name: body
- style: CSS-in-JS camelCase object for page-wide styles (e.g. { backgroundColor: '#f8f9fa', fontFamily: 'Inter', display: 'flex', flexDirection: 'column', alignItems: 'center' })
- c: array of content blocks (sections, header, footer, etc.)

# Content Block Schema:
- el: semantic HTML tag (section, nav, header, footer, h1-h3, p, span, button, a, img)
- name: descriptive name
- style: CSS-in-JS camelCase object. Include interactive states (e.g., 'hover:backgroundColor', 'active:transform', 'hover:color') for buttons and links.
- m_style: mobile overrides
- t_style: tablet overrides
- attrs: HTML attrs (src, alt, href, target)
- text: text content
- c: nested blocks array
- classes: CSS class names

# Rules:
- The top-level Page block must have 'display: flex', 'flexDirection: column', and 'alignItems: center' to layout sections properly.
- All top-level sections inside 'c' MUST have 'width: 100%'.
- Modern harmonious color palettes. Good spacing. Professional concise copy.
- Interactive: Use hover states for buttons/links to make the page feel alive.
- Google Fonts via fontFamily (use ONLY the font name and not the fallback).
- Semantic HTML with alt texts."""

MODIFY_PROMPT_MAP = {
	"rewrite_text": REWRITE_TEXT_PROMPT,
	"replace_image": REPLACE_IMAGE_PROMPT,
}


def get_system_prompt(is_modify: bool, task_type: str | None = None) -> str:
	if is_modify:
		return MODIFY_PROMPT_MAP.get(task_type or "", MODIFY_PROMPT)
	return GENERATE_PROMPT


def classify_task(is_modify: bool, task_type: str | None = None) -> str:
	if is_modify and task_type in {"rewrite_text", "replace_image"}:
		return "simple"
	return "complex"


def compress_block_to_yaml(block: dict, depth: int = 0, task_tier: str = "complex") -> dict:
	if not isinstance(block, dict):
		return block

	out = {}
	if block.get("element"):
		out["el"] = block["element"]
	if block.get("blockId"):
		out["id"] = block["blockId"]
	if block.get("blockName"):
		out["name"] = block["blockName"]

	base_styles = block.get("baseStyles") or {}
	if isinstance(base_styles, dict):
		filtered = (
			{k: v for k, v in base_styles.items() if k in STYLE_KEYS_SIMPLE}
			if task_tier == "simple"
			else base_styles
		)
		if filtered:
			out["style"] = filtered

	attrs = block.get("attributes") or {}
	if isinstance(attrs, dict) and attrs:
		out["attrs"] = attrs

	if block.get("classes"):
		out["classes"] = block["classes"]
	if block.get("innerHTML"):
		out["text"] = block["innerHTML"]

	mob = block.get("mobileStyles") or {}
	if isinstance(mob, dict) and mob:
		out["m_style"] = mob

	tab = block.get("tabletStyles") or {}
	if isinstance(tab, dict) and tab and (task_tier == "complex" or depth <= 1):
		out["t_style"] = tab

	children = [
		compress_block_to_yaml(c, depth + 1, task_tier)
		for c in block.get("children", [])
		if isinstance(c, dict)
	]
	if children:
		out["c"] = children

	return out


def extract_block_id(block_context: str) -> str | None:
	"""Extract blockId from raw JSON context without full re-parse later."""
	try:
		data = json.loads(block_context)
		if isinstance(data, list):
			data = data[0] if data else {}
		return data.get("blockId") if isinstance(data, dict) else None
	except Exception:
		return None


def strip_block_context(block_context: str, task_tier: str, task_type: str | None = None) -> str:
	"""Convert block JSON to compact YAML to reduce input tokens."""
	try:
		data = json.loads(block_context)
	except (json.JSONDecodeError, TypeError):
		return block_context

	if isinstance(data, list):
		data = data[0] if data else {}
	if not isinstance(data, dict):
		return block_context

	if task_type == "rewrite_text":
		return data.get("innerHTML") or data.get("innerText") or ""
	if task_type == "replace_image":
		attrs = data.get("attributes", {})
		return to_compact_yaml({"src": attrs.get("src", ""), "alt": attrs.get("alt", "")})
	return to_compact_yaml([compress_block_to_yaml(data, 0, task_tier)])


def expand_yaml_to_block(node: dict) -> dict:
	"""Expand compact YAML node back to Frappe Builder block schema."""
	if not isinstance(node, dict):
		return node

	block = {
		"element": node.get("el", "div"),
		"blockName": node.get("name", ""),
		"baseStyles": node.get("style", {}),
		"attributes": node.get("attrs", {}),
		"children": [expand_yaml_to_block(c) for c in node.get("c", []) if isinstance(c, dict)],
	}
	for yaml_key, block_key in [
		("id", "blockId"),
		("text", "innerHTML"),
		("m_style", "mobileStyles"),
		("t_style", "tabletStyles"),
		("classes", "classes"),
	]:
		if yaml_key in node:
			block[block_key] = node[yaml_key]

	return block


def build_user_message(
	prompt: str, is_modify: bool, block_context: str | None = None, task_type: str | None = None
) -> str:
	if is_modify and block_context:
		if task_type == "rewrite_text":
			return f'Text content to rewrite: "{block_context}"\n\nInstruction: {prompt}'
		if task_type == "replace_image":
			return f"Current image attributes:\n{block_context}\n\nInstruction: {prompt}"
		return f"Block:\n{block_context}\n\nChange: {prompt}"
	return f"Create a page for: {prompt}"


def call_llm(model: str, messages: list, params: dict, *, stream: bool, api_key: str | None = None):
	"""Call litellm. Returns chunk iterator (stream=True) or string (stream=False)."""
	if model.startswith("gemini-"):
		model = f"gemini/{model}"

	litellm.drop_params = True

	if "claude-" in model:
		for m in messages:
			if m["role"] == "system" and isinstance(m.get("content"), str):
				m["content"] = [{"type": "text", "text": m["content"]}]
	resp = litellm.completion(model=model, messages=messages, stream=stream, api_key=api_key, **params)
	return resp if stream else (resp.choices[0].message.content or "")


def strip_fences(text: str) -> str:
	text = re.sub(r"^```(?:yaml|json)?\s*\n?", "", text.strip())
	return re.sub(r"\n?```\s*$", "", text).strip()


def parse_blocks(content: str) -> dict:
	"""Parse LLM YAML output into a single block object."""
	parsed = yaml.safe_load(strip_fences(content))
	if isinstance(parsed, dict):
		block = parsed
	elif isinstance(parsed, list):
		block = parsed[0] if parsed else {}
	else:
		raise ValueError("Not a valid block object")

	if not block:
		raise ValueError("No valid blocks in response")

	if isinstance(block, dict) and not block.get("id"):
		block["id"] = "root"

	return expand_yaml_to_block(block)


def run_llm_job(
	prompt: str,
	model: str,
	api_key: str,
	event_prefix: str,
	is_modify: bool,
	user: str | None = None,
	page_id: str | None = None,
	block_context: str | None = None,
	task_type: str | None = None,
):
	user = user or frappe.session.user

	def emit(suffix, **kwargs):
		event = f"{event_prefix}_{suffix}"
		if page_id:
			event = f"{event}_{page_id}"
		payload = {
			"page_id": page_id,
			"task_type": task_type,
			**kwargs,
		}
		frappe.publish_realtime(event, payload, user=user)

	task_tier = classify_task(is_modify=is_modify, task_type=task_type)
	params = TASK_PARAMS[task_tier]

	if task_tier == "simple":
		model = get_simple_model(model)

	should_stream = True
	action = "Modifying" if is_modify else "Generating"
	tier_label = "fast" if task_tier == "simple" else "full"

	emit(
		"progress",
		status="generating",
		message=f"{action} ({tier_label}) with {model}...",
		task_tier=task_tier,
		model_used=model,
	)

	# Fix: extract original_id once here; pass it down instead of re-parsing later
	original_id = extract_block_id(block_context) if is_modify and block_context else None

	stripped_context = (
		strip_block_context(block_context, task_tier, task_type=task_type) if is_modify else None
	)

	messages = [
		{
			"role": "system",
			"content": get_system_prompt(is_modify, task_type),
			"cache_control": {"type": "ephemeral"},
		},
		{
			"role": "user",
			"content": build_user_message(
				prompt, is_modify, block_context=stripped_context, task_type=task_type
			),
		},
	]

	content = ""
	try:
		if should_stream:
			for chunk in call_llm(model, messages, params, stream=True, api_key=api_key):
				if delta := chunk.choices[0].delta.content:
					content += delta
					emit("stream", chunk=delta, block_id=original_id)
		else:
			content = call_llm(model, messages, params, stream=False, api_key=api_key)

	except ValueError as e:
		frappe.log_error(f"Parse error: {e}\nContent: {content}", f"{event_prefix} parse")
		emit("error", message="Failed to parse AI response. The model returned invalid YAML.")
		return

	except Exception as e:
		frappe.log_error(f"LLM job error: {e}", event_prefix)
		emit("error", message=str(e))
		return

	emit("complete", block_id=original_id, model_used=model, task_tier=task_tier)


def generate_page_blocks(
	prompt: str, model: str, api_key: str, user: str | None = None, page_id: str | None = None
):
	run_llm_job(prompt, model, api_key, "ai_generation", is_modify=False, user=user, page_id=page_id)


def modify_section_blocks(
	prompt: str,
	block_context: str,
	model: str,
	api_key: str,
	user: str | None = None,
	page_id: str | None = None,
	task_type: str | None = None,
):
	run_llm_job(
		prompt,
		model,
		api_key,
		"ai_modify",
		is_modify=True,
		user=user,
		page_id=page_id,
		block_context=block_context,
		task_type=task_type,
	)


def enqueue_ai_job(fn, **kwargs):
	if not frappe.has_permission("Builder Page", ptype="write"):
		frappe.throw(_("You do not have permission to modify pages"))
	settings = frappe.get_single("Builder Settings")
	model = settings.get("ai_model")
	if not model:
		frappe.throw(_("Please configure an AI model in Settings → AI"))
	frappe.enqueue(
		fn,
		model=model,
		api_key=settings.get_password("ai_api_key", raise_exception=False),
		user=frappe.session.user,
		is_async=True,
		**kwargs,
	)
	frappe.local.response.http_status_code = 202
	return {"status": "accepted"}


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
				{"name": "claude-sonnet-4-6", "label": "Claude Sonnet 4.6 (Balanced)", "max_tokens": 200000},
				{"name": "claude-haiku-4-5", "label": "Claude Haiku 4.5 (Fastest)", "max_tokens": 200000},
			],
		},
		{
			"provider": "google",
			"models": [
				{
					"name": "gemini-3.1-pro-preview",
					"label": "Gemini 3.1 Pro (Flagship)",
					"max_tokens": 1048576,
				},
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


PROVIDER_SIMPLE_MODEL: dict[str, str] = {
	"anthropic": "claude-haiku-4-5",
	"google": "gemini-3-flash-preview",
	"openai": "gpt-5.4-nano",
	"xai": "grok-4.1-fast",
}


def detect_provider(model: str) -> str | None:
	lower = model.lower()
	if "claude-" in lower:
		return "anthropic"
	if "gemini-" in lower:
		return "google"
	if "gpt-" in lower or re.match(r"o\d", lower):
		return "openai"
	if "grok-" in lower:
		return "xai"
	return None


def get_simple_model(model: str) -> str:
	provider = detect_provider(model)
	if provider is None:
		return model
	return PROVIDER_SIMPLE_MODEL[provider]


@frappe.whitelist()
def get_ai_models():
	return get_available_models()


@frappe.whitelist()
def generate_page_from_prompt(prompt: str, page_id: str | None = None):
	return enqueue_ai_job(generate_page_blocks, prompt=prompt, page_id=page_id)


@frappe.whitelist()
def modify_section_from_prompt(
	prompt: str, block_context: str, page_id: str | None = None, task_type: str | None = None
):
	try:
		json.loads(block_context)
	except json.JSONDecodeError:
		frappe.throw(_("Invalid block context JSON"))
	return enqueue_ai_job(
		modify_section_blocks,
		prompt=prompt,
		block_context=block_context,
		page_id=page_id,
		task_type=task_type,
	)


@frappe.whitelist()
def test_api_key(model: str, api_key: str):
	try:
		litellm.drop_params = True
		litellm.completion(
			model=f"gemini/{model}" if model.startswith("gemini-") else model,
			messages=[{"role": "user", "content": "Say 'OK' if you can read this"}],
			max_tokens=10,
			api_key=api_key,
		)
		return {"success": True, "message": _("API key is valid")}
	except Exception as e:
		return {"success": False, "message": str(e)}
