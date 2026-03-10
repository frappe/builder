"""
AI Page Generator
Generates Builder pages from natural language prompts using various LLM providers
"""

import json
from typing import Any

import frappe
from frappe import _


def get_available_models():
	"""Return list of available AI models"""
	return [
		{
			"provider": "openai",
			"models": [
				{"name": "chatgpt-4o-latest", "label": "GPT-4o Latest", "max_tokens": 128000},
				{"name": "gpt-4o", "label": "GPT-4o", "max_tokens": 128000},
				{"name": "gpt-4o-mini", "label": "GPT-4o Mini", "max_tokens": 128000},
				{"name": "o1", "label": "O1 (Reasoning)", "max_tokens": 100000},
				{"name": "o1-mini", "label": "O1 Mini (Reasoning)", "max_tokens": 65000},
				{"name": "gpt-4-turbo", "label": "GPT-4 Turbo", "max_tokens": 128000},
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

1. **Root Block**: Always wrap everything in a root body element:
```json
{
  "element": "body",
  "blockId": "root",
  "children": [...],
  "baseStyles": {}
}
```

2. **Common Elements**: Use semantic HTML elements:
   - Container: "div" with display: flex/grid
   - Text: "h1", "h2", "h3", "p", "span"
   - Buttons: "button" or "a"
   - Images: "img" with src attribute
   - Sections: "section", "header", "footer", "nav"
   - Font: Choose from Google Fonts and specify in styles

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
5. **Responsive**: Ensure mobile-first responsive design
6. **Accessibility**: Include proper semantic HTML and alt texts

# Common Layouts:

**Hero Section**:
```json
{
  "element": "section",
  "baseStyles": {
    "display": "flex",
    "flexDirection": "column",
    "alignItems": "center",
    "justifyContent": "center",
    "minHeight": "80vh",
    "padding": "4rem 2rem",
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
  "baseStyles": {
    "display": "flex",
    "justifyContent": "space-between",
    "alignItems": "center",
    "padding": "1rem 2rem",
    "backgroundColor": "#ffffff",
    "boxShadow": "0 2px 4px rgba(0,0,0,0.1)"
  },
  "children": [...]
}
```

# CRITICAL: Output Format

Return ONLY a JSON array with no markdown code blocks, no explanations, no additional text. Start directly with `[` and end with `]`.

Example output:
[{"element":"body","blockId":"root","children":[{"element":"section","baseStyles":{"display":"flex"},"children":[...]}],"baseStyles":{}}]

Remember:
- Generate complete, production-ready pages
- Use modern design principles
- Ensure responsive design
- Return ONLY valid JSON
- No markdown, no explanations, just JSON"""


def generate_page_blocks(prompt: str, model: str, api_key: str | None = None) -> list[dict[str, Any]]:
	"""
	Generate page blocks from a prompt using the specified AI model with streaming.

	Streams response chunks to the frontend via realtime events so users
	can see the generation happening in real time.

	Args:
		prompt: User's description of the page they want
		model: Model identifier (e.g., 'gpt-4o', 'claude-sonnet-4-6')
		api_key: Optional API key (if not configured in site config)

	Returns:
		List of block dictionaries
	"""
	content = ""
	try:
		try:
			import litellm
		except ImportError:
			frappe.throw(
				_("litellm library is not installed. Please install it using: pip install litellm"),
				title=_("Missing Dependency"),
			)

		if not api_key:
			api_key = get_api_key_for_model(model)

		if not api_key:
			frappe.throw(
				_(
					"API key not configured for model: {0}. Please configure it in site config or provide it in the request."
				).format(model),
				title=_("API Key Missing"),
			)

		set_api_key_for_provider(model, api_key)

		frappe.publish_realtime(
			"ai_generation_progress",
			{"status": "preparing", "message": "Preparing AI request..."},
			user=frappe.session.user,
		)

		messages = [
			{"role": "system", "content": get_system_prompt()},
			{"role": "user", "content": f"Create a section for: {prompt}"},
		]

		frappe.publish_realtime(
			"ai_generation_progress",
			{"status": "generating", "message": f"Generating page with {model}..."},
			user=frappe.session.user,
		)

		# Stream the response so the frontend can show progressive output
		response = litellm.completion(
			model=model,
			messages=messages,
			temperature=0.7,
			max_tokens=8000,
			stream=True,
		)

		content = ""
		for chunk in response:
			delta = chunk.choices[0].delta.content
			if delta:
				content += delta
				frappe.publish_realtime(
					"ai_generation_stream",
					{"chunk": delta, "accumulated": content},
					user=frappe.session.user,
				)

		content = content.strip()

		frappe.publish_realtime(
			"ai_generation_progress",
			{"status": "parsing", "message": "Parsing generated content..."},
			user=frappe.session.user,
		)

		# Remove markdown code blocks if present
		if content.startswith("```"):
			content = content.split("\n", 1)[1] if "\n" in content else content[3:]
			if content.endswith("```"):
				content = content[:-3].strip()

		section = json.loads(content)

		# Normalize: if the model returned an array, take the first element
		if isinstance(section, list):
			section = section[0] if section else {}

		if not isinstance(section, dict):
			frappe.throw(
				_("AI response is not a valid block object"),
				title=_("Invalid Response"),
			)

		# Wrap the generated section in a proper Builder root block
		blocks = [
			{
				"element": "div",
				"originalElement": "body",
				"blockId": "root",
				"children": [section],
				"baseStyles": {
					"display": "flex",
					"flexWrap": "wrap",
					"flexShrink": "0",
					"flexDirection": "column",
					"alignItems": "center",
				},
				"attributes": {},
				"mobileStyles": {},
				"tabletStyles": {},
			}
		]

		frappe.publish_realtime(
			"ai_generation_progress",
			{"status": "complete", "message": "Page generated successfully!"},
			user=frappe.session.user,
		)

		return blocks

	except json.JSONDecodeError as e:
		frappe.log_error(f"JSON parsing error: {e!s}\nContent: {content}", "AI Page Generation Error")
		frappe.throw(
			_("Failed to parse AI response as JSON. The model may have returned invalid output."),
			title=_("Generation Error"),
		)

	except Exception as e:
		frappe.log_error(f"AI generation error: {e!s}", "AI Page Generation Error")
		frappe.throw(
			_("Failed to generate page: {0}").format(str(e)),
			title=_("Generation Error"),
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
def generate_page_from_prompt(prompt: str, model: str | None = None, api_key: str | None = None):
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

	blocks = generate_page_blocks(prompt, model, api_key)

	return {
		"success": True,
		"blocks": blocks,
		"message": _("Page generated successfully"),
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
