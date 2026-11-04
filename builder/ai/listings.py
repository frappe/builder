"""What a provider will serve this account right now, asked of the provider itself.

Each listing returns {model id: what the provider says about it}. Most providers
only name their models, so the value is empty and models.dev describes them; the
ChatGPT catalog describes its own, and those facts win, because the ChatGPT
serving surface differs from the public API (a smaller context window, for one).

A listing doubles as the key check when connecting: it spends no tokens, and a
rejected key fails it the same way a rejected completion would.
"""

import requests

FETCH_TIMEOUT = 15


def list_models(preset: dict, credential: str | None) -> dict[str, dict]:
	"""Model ids this credential can call, by the preset's listing style. Raises on a rejected key."""
	style = preset.get("listing")
	if style == "codex":
		from builder.ai import codex

		return codex.list_models(credential or "")
	lister = LISTERS.get(style)
	if not lister:
		raise ValueError(f"No model listing for {preset.get('name') or style}")
	return lister(credential or "")


def list_openai(key: str) -> dict[str, dict]:
	data = get_json("https://api.openai.com/v1/models", {"Authorization": f"Bearer {key}"})
	return {m["id"]: {} for m in data.get("data") or [] if m.get("id")}


def list_anthropic(key: str) -> dict[str, dict]:
	headers = {"x-api-key": key, "anthropic-version": "2023-06-01"}
	data = get_json("https://api.anthropic.com/v1/models?limit=1000", headers)
	return {m["id"]: {} for m in data.get("data") or [] if m.get("id")}


def list_gemini(key: str) -> dict[str, dict]:
	url = "https://generativelanguage.googleapis.com/v1beta/models?pageSize=1000"
	data = get_json(url, {"x-goog-api-key": key})
	return {
		m["name"].removeprefix("models/"): {}
		for m in data.get("models") or []
		if m.get("name") and "generateContent" in (m.get("supportedGenerationMethods") or [])
	}


def list_openrouter(key: str) -> dict[str, dict]:
	# The catalog is public, so it proves nothing about the key: /key does.
	if key:
		get_json("https://openrouter.ai/api/v1/key", {"Authorization": f"Bearer {key}"})
	data = get_json("https://openrouter.ai/api/v1/models", {})
	return {m["id"]: {} for m in data.get("data") or [] if m.get("id")}


LISTERS = {
	"openai": list_openai,
	"anthropic": list_anthropic,
	"gemini": list_gemini,
	"openrouter": list_openrouter,
}


class ListingError(Exception):
	pass


def get_json(url: str, headers: dict) -> dict:
	response = requests.get(url, headers=headers, timeout=FETCH_TIMEOUT)
	if response.status_code >= 400:
		# the body says why (Gemini's "API key not valid" comes back as a bare 400)
		raise ListingError(f"{response.status_code}: {response.text[:300]}")
	return response.json() or {}
