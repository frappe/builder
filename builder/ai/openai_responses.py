"""Direct OpenAI Responses transport for GPT-6 models used by Bob's tool loop."""

from types import SimpleNamespace

import requests

from builder.ai import codex
from builder.ai.models import ModelRegistry

API_URL = "https://api.openai.com/v1/responses"


class OpenAIResponsesError(Exception):
	def __init__(self, message: str, status_code: int):
		super().__init__(message)
		self.status_code = status_code


class AuthenticationError(OpenAIResponsesError):
	pass


class PermissionDeniedError(OpenAIResponsesError):
	pass


class NotFoundError(OpenAIResponsesError):
	pass


class RateLimitError(OpenAIResponsesError):
	pass


class InternalServerError(OpenAIResponsesError):
	pass


def route(model: str) -> str | None:
	info = ModelRegistry.find(model) or {}
	prefix = info.get("route_prefix") or ""
	model_id = model.removeprefix(f"{prefix}/")
	if info.get("litellm_provider") == "openai" and not info.get("api_base") and model_id.startswith("gpt-6"):
		return model_id
	return None


def build_payload(model: str, messages: list, tools: list | None, params: dict) -> dict:
	payload = codex.build_payload(model, messages, tools, params.get("reasoning_effort"))
	payload["max_output_tokens"] = params.get("max_tokens", 16000)
	if tier := params.get("service_tier"):
		payload["service_tier"] = tier
	if not tools:
		payload.pop("tool_choice")
		payload.pop("parallel_tool_calls")
	for tool in payload.get("tools", []):
		tool["strict"] = False
	for item in payload["input"]:
		if item.get("type") == "message" and item.get("role") == "assistant":
			content = codex.content_text(item.get("content"))
			item.clear()
			item.update({"role": "assistant", "content": content})
	return payload


def headers(api_key: str) -> dict:
	return {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}


def http_error(response) -> OpenAIResponsesError:
	status = response.status_code
	message = f"OpenAI request failed ({status}): {response.text[:300]}"
	known = {401: AuthenticationError, 403: PermissionDeniedError, 404: NotFoundError, 429: RateLimitError}
	cls = known.get(status, InternalServerError if status >= 500 else OpenAIResponsesError)
	return cls(message, status)


def stream_chunks(api_key: str, payload: dict):
	with requests.post(
		API_URL, json=payload, headers=headers(api_key), stream=True, timeout=(10, 120)
	) as response:
		if response.status_code >= 400:
			raise http_error(response)
		assembler = codex.ChunkAssembler()
		for event in codex.iter_sse(response):
			yield from assembler.feed(event)
			if assembler.finished:
				return


def complete(model: str, messages: list, params: dict, api_key: str, tools: list | None, stream: bool):
	chunks = stream_chunks(api_key, build_payload(model, messages, tools, params))
	if stream:
		return chunks
	if tools is not None:
		return collect_response(chunks)
	return "".join(chunk.choices[0].delta.content or "" for chunk in chunks)


def collect_response(chunks):
	content, calls, usage = [], {}, None
	for chunk in chunks:
		delta = chunk.choices[0].delta
		if delta.content:
			content.append(delta.content)
		for part in delta.tool_calls or []:
			call = calls.setdefault(part.index, {"id": "", "name": "", "arguments": ""})
			call["id"] = part.id or call["id"]
			call["name"] = part.function.name or call["name"]
			call["arguments"] += part.function.arguments or ""
		usage = chunk.usage or usage
	tool_calls = [
		SimpleNamespace(
			id=call["id"], function=SimpleNamespace(name=call["name"], arguments=call["arguments"])
		)
		for _, call in sorted(calls.items())
	]
	message = SimpleNamespace(content="".join(content), tool_calls=tool_calls)
	return SimpleNamespace(choices=[SimpleNamespace(message=message)], usage=usage)
