"""
AI Page Generator
Generates Builder pages from natural language prompts using various LLM providers
"""

import json

import frappe
from frappe import _


def get_available_models():
	"""Return list of available AI models"""
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
				{"name": "claude-opus-4-6", "label": "Claude Opus 4.6 (Most Capable)", "max_tokens": 200000},
				{"name": "claude-haiku-4-5", "label": "Claude Haiku 4.5 (Fastest)", "max_tokens": 200000},
			],
		},
		{
			"provider": "google",
			"models": [
				{"name": "gemini-1.5-flash", "label": "Gemini 1.5 Flash", "max_tokens": 1048576},
				{"name": "gemini-1.5-pro", "label": "Gemini 1.5 Pro", "max_tokens": 2097152},
				{
					"name": "gemini-2.0-flash-exp",
					"label": "Gemini 2.0 Flash (Experimental)",
					"max_tokens": 1048576,
				},
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
	"""Return the system prompt for page generation"""
	return """You are an expert web designer and developer specializing in creating beautiful, modern, and responsive web pages using the Frappe Builder block system.

Your task is to generate a complete page structure based on user prompts. You must return ONLY a valid JSON array of blocks, with no additional text, markdown formatting, or explanations.

# Block Structure Rules:

2. **Common Elements**: Use semantic HTML elements:
   - Container: "div" with display: flex/grid
   - Text: "h1", "h2", "h3", "p", "span"
   - Buttons: "button" or "a"
   - Images: "img" with src attribute
   - Sections: "section", "header", "footer", "nav"
   - Font: Choose creative/relevant fonts from Google Fonts and specify in baseStyles (e.g., "fontFamily": "Roboto")

3. **Styling (baseStyles)**: Use CSS-in-JS object format:
```json
{
  "baseStyles": {
    "display": "flex",
    "flexDirection": "column",
    "padding": "2rem",
    "backgroundColor": "#ffffff",
    "fontSize": "16px",
    "fontWeight": "600"
  }
}
```

4. **Responsive Styles**: Add mobile/tablet overrides:
```json
{
  "mobileStyles": {
    "fontSize": "14px",
    "padding": "1rem"
  },
  "tabletStyles": {
    "fontSize": "15px"
  }
}
```

5. **Attributes**: Add HTML attributes:
```json
{
  "attributes": {
    "src": "/path/to/image.jpg",
    "alt": "Image description",
    "href": "https://example.com",
    "target": "_blank"
  }
}
```

6. **Text Content**: Use innerText or innerHTML:
```json
{
  "element": "h1",
  "blockName": "hero-title",
  "innerText": "Welcome to Our Site"
}
```

7. **Classes**: Add CSS classes if needed:
```json
{
  "classes": ["hero-section", "text-center"]
}
```

# Design Best Practices:

1. **Modern Design**: Use contemporary design patterns (flexbox, grid layouts)
2. **Color Schemes**: Use harmonious color palettes
3. **Typography**: Use appropriate font sizes and weights
4. **Spacing**: Apply consistent padding and margins
5. **Responsive**: Ensure mobile-first responsive design, set relative units (%, rem) for widths.
6. **Accessibility**: Include proper semantic HTML and alt texts

# Common Layouts:

**Hero Section**:
```json
{
  "element": "section",
  "blockName": "hero-section",
  "baseStyles": {
    "display": "flex",
    "flexDirection": "column",
    "alignItems": "center",
    "justifyContent": "center",
    "minHeight": "80vh",
    "padding": "4rem 2rem",
    "width": "100%",
    "background": "linear-gradient(135deg, #667eea 0%, #764ba2 100%)",
    "color": "#ffffff"
  },
  "children": [...]
}
```

**Card Grid**:
```json
{
  "element": "div",
  "blockName": "product-grid",
  "baseStyles": {
    "display": "grid",
    "gridTemplateColumns": "repeat(auto-fit, minmax(300px, 1fr))",
    "gap": "2rem",
    "padding": "2rem"
  },
  "children": [...]
}
```

**Navigation Bar**:
```json
{
  "element": "nav",
  "blockName": "main-nav",
  "baseStyles": {
    "display": "flex",
    "justifyContent": "space-between",
    "alignItems": "center",
    "padding": "1rem 2rem",
    "width": "100%",
    "backgroundColor": "#ffffff",
    "boxShadow": "0 2px 4px rgba(0,0,0,0.1)"
  },
  "children": [...]
}
```

# CRITICAL: Output Format

Return ONLY a JSON array with no markdown code blocks, no explanations, no additional text. Start directly with `[` and end with `]`.

Example output:
[{"element":"section","baseStyles":{"display":"flex"},"children":[...],attributes:{},blockName:"hero-section"}, {"element":"div","baseStyles":{"display":"grid"},"children":[...]}, ...]

Remember:
- Generate complete, production-ready pages
- Use modern design principles
- Ensure responsive design
- Return ONLY valid JSON
- No markdown, no explanations, just JSON
- Make sure widths are set to 100% for responsiveness"""


def generate_page_blocks(
	prompt: str,
	model: str,
	api_key: str | None = None,
	user: str | None = None,
	page_id: str | None = None,
):
	"""
	Generate page blocks from a prompt using the specified AI model with streaming.

	Runs as a background job. Streams chunks and publishes final blocks via realtime.

	Args:
		prompt: User's description of the page they want
		model: Model identifier (e.g., 'gpt-5.4', 'claude-sonnet-4-6')
		api_key: Optional API key (if not configured in site config)
		user: The user to publish realtime events to
		page_id: Builder Page ID to scope realtime events to
	"""
	user = user or frappe.session.user
	content = ""
	try:
		try:
			import litellm
		except ImportError:
			frappe.publish_realtime(
				"ai_generation_error",
				{"page_id": page_id, "message": "litellm library is not installed. Please install it using: pip install litellm"},
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
					"message": f"API key not configured for model: {model}. Please configure it in Settings \u2192 AI.",
				},
				user=user,
			)
			return

		set_api_key_for_provider(model, api_key)

		frappe.publish_realtime(
			"ai_generation_progress",
			{"page_id": page_id, "status": "preparing", "message": "Preparing AI request..."},
			user=user,
		)

		messages = [
			{"role": "system", "content": get_system_prompt()},
			{"role": "user", "content": f"Create a section for: {prompt}"},
		]

		frappe.publish_realtime(
			"ai_generation_progress",
			{"page_id": page_id, "status": "generating", "message": f"Generating page with {model}..."},
			user=user,
		)

		# Stream the response so the frontend can show progressive output
		# GPT-5+ models only support temperature=1; use drop_params to
		# let litellm silently strip unsupported kwargs for any model.
		litellm.drop_params = True
		response = litellm.completion(
			model=model,
			messages=messages,
			temperature=0.7,
			max_tokens=12000,
			stream=True,
		)

		content = ""
		for chunk in response:
			delta = chunk.choices[0].delta.content
			if delta:
				content += delta
				frappe.publish_realtime(
					"ai_generation_stream",
					{"page_id": page_id, "chunk": delta, "accumulated": content},
					user=user,
				)

		content = content.strip()

		frappe.publish_realtime(
			"ai_generation_progress",
			{"page_id": page_id, "status": "parsing", "message": "Parsing generated content..."},
			user=user,
		)

		# Remove markdown code blocks if present
		if content.startswith("```"):
			content = content.split("\n", 1)[1] if "\n" in content else content[3:]
			if content.endswith("```"):
				content = content[:-3].strip()

		parsed = json.loads(content)

		# Normalize: ensure we have a list of section blocks
		if isinstance(parsed, dict):
			blocks = [parsed]
		elif isinstance(parsed, list):
			blocks = [b for b in parsed if isinstance(b, dict)]
		else:
			frappe.publish_realtime(
				"ai_generation_error",
				{"page_id": page_id, "message": "AI response is not a valid block object"},
				user=user,
			)
			return

		if not blocks:
			frappe.publish_realtime(
				"ai_generation_error",
				{"page_id": page_id, "message": "AI response contained no valid blocks"},
				user=user,
			)
			return

		frappe.publish_realtime(
			"ai_generation_complete",
			{"page_id": page_id, "blocks": blocks},
			user=user,
		)

	except json.JSONDecodeError as e:
		frappe.log_error(f"JSON parsing error: {e!s}\nContent: {content}", "AI Page Generation Error")
		frappe.publish_realtime(
			"ai_generation_error",
			{"page_id": page_id, "message": "Failed to parse AI response as JSON. The model may have returned invalid output."},
			user=user,
		)

	except Exception as e:
		frappe.log_error(f"AI generation error: {e!s}", "AI Page Generation Error")
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
	"""Determine provider from model name"""
	if model.startswith(("gpt-", "chatgpt-", "o1", "o3")):
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
		"google": "GOOGLE_API_KEY",
		"x-ai": "XAI_API_KEY",
	}

	env_key = key_mapping.get(provider)
	if env_key:
		os.environ[env_key] = api_key


@frappe.whitelist()
def get_ai_models():
	"""API endpoint to get available AI models"""
	return get_available_models()


@frappe.whitelist()
def generate_page_from_prompt(prompt: str, page_id: str | None = None, model: str | None = None, api_key: str | None = None):
	"""
	API endpoint to generate page blocks from a prompt.
	Reads model and API key from Builder Settings if not provided.
	"""
	if not frappe.has_permission("Builder Page", ptype="write"):
		frappe.throw(_("You do not have permission to generate pages"))

	if not prompt or not prompt.strip():
		frappe.throw(_("Please provide a prompt describing the page you want to create"))

	# Read from Builder Settings if not provided
	if not model:
		settings = frappe.get_single("Builder Settings")
		model = settings.get("ai_model")
		if not api_key:
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
		queue="default",
		is_async=True,
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

		set_api_key_for_provider(model, api_key)

		# Make a simple test call
		litellm.completion(
			model=model,
			messages=[{"role": "user", "content": "Say 'OK' if you can read this"}],
			max_tokens=10,
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
