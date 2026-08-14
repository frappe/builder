"""OpenAI models through a ChatGPT subscription, spoken over the Codex backend.

The credential is a Codex CLI login: the JSON the CLI writes to ~/.codex/auth.json
is pasted into the provider's api_key field and refreshed here in place, so no
API key or per-token billing is involved. The backend only speaks the Responses
SSE protocol, which litellm cannot, so this module adapts each stream into the
chat-completions chunk shape the rest of builder.ai already reads: llm.py hands
any model whose provider routes as "codex" to complete() below and everything
downstream stays provider-blind.
"""

import base64
import json
import logging
import time
from types import SimpleNamespace

import frappe
import requests

CLIENT_ID = "app_EMoamEEZ73f0CkXaXp7hrann"
TOKEN_URL = "https://auth.openai.com/oauth/token"
API_BASE = "https://chatgpt.com/backend-api"
ORIGINATOR = "codex_cli_rs"
CLIENT_VERSION = "0.145.0"
CONNECT_TIMEOUT = 10
READ_TIMEOUT = 120  # max stall between bytes, mirrors llm.py
CATALOG_TIMEOUT = 5
REFRESH_SLACK_MS = 60_000

# The ChatGPT serving surface, not the public API. litellm's model map describes
# the API and gets these wrong; the spark models are text-only.
CONTEXT_WINDOWS = {
	"gpt-5.6-sol": 272_000,
	"gpt-5.6-terra": 272_000,
	"gpt-5.6-luna": 272_000,
	"gpt-5.6": 272_000,
	"gpt-5.5": 272_000,
	"gpt-5.4-mini": 272_000,
	"gpt-5.4-pro": 272_000,
	"gpt-5.4": 272_000,
	"gpt-5.3-codex-spark": 128_000,
	"gpt-5.3-codex": 400_000,
	"gpt-5.2": 400_000,
}


class CodexError(Exception):
	pass


# Named so llm.is_retryable recognises them; it matches exception class names.
class RateLimitError(Exception):
	pass


class InternalServerError(Exception):
	pass


def complete(
	model: str,
	messages: list,
	params: dict,
	*,
	provider: str,
	tools: list | None = None,
	stream: bool = False,
):
	"""Chat-completions-compatible entry for the codex route: an iterator of
	chunks when streaming, else the response text (tool calls need streaming).
	`params` (the TASK_PARAMS tier) is accepted for interface parity and
	deliberately unsent: the codex backend 400s on temperature AND on
	max_output_tokens, and budgets output itself."""
	payload = build_payload(model, messages, tools)
	log(f"Codex | model={model} stream={stream} tools={len(tools or [])} messages={len(messages)}")
	chunks = stream_chunks(provider, payload)
	if stream:
		return chunks
	return "".join(c.choices[0].delta.content or "" for c in chunks)


def verify_credential(raw: str) -> dict:
	"""The smallest real proof this login works: refresh the token, then hit the
	authenticated model catalog. Spends no completion tokens. The refreshed access
	token is discarded; OpenAI keeps the refresh token stable, so the pasted
	credential stays valid to store afterwards."""
	from frappe import _

	try:
		cred = refresh_credential(parse_credential(raw))
		headers = request_headers(cred["access"], cred["account_id"], accept="application/json")
		headers.pop("content-type")
		resp = requests.get(
			f"{API_BASE}/codex/models",
			params={"client_version": CLIENT_VERSION},
			headers=headers,
			timeout=CATALOG_TIMEOUT,
		)
		if resp.status_code >= 400:
			raise http_error(resp)
		return {"success": True, "severity": "ok", "message": _("Connected")}
	except CodexError as e:
		return {"success": False, "severity": "error", "message": str(e)}
	except Exception as e:
		from builder.ai.presets import readable_error

		message, severity = readable_error(str(e))
		return {"success": False, "severity": severity, "message": message}


def model_metadata(model_id: str) -> dict:
	"""Context window and vision for a codex model, from the table above."""
	for known, window in CONTEXT_WINDOWS.items():
		if model_id == known or model_id.startswith(f"{known}-20"):
			return {"max_tokens": window, "vision": "spark" not in model_id}
	return {}


# --- request + stream --------------------------------------------------------


def stream_chunks(provider: str, payload: dict):
	resp = open_stream(provider, payload)
	assembler = ChunkAssembler()
	with resp:
		for event in iter_sse(resp):
			yield from assembler.feed(event)
			if assembler.finished:
				return


def open_stream(provider: str, payload: dict) -> requests.Response:
	access, account = runtime_auth(provider)
	resp = post_stream(payload, access, account)
	if resp.status_code == 401:
		cred = refresh_credential(stored_credential(provider))
		save_credential(provider, cred)
		resp = post_stream(payload, cred["access"], cred["account_id"])
	if resp.status_code >= 400:
		raise http_error(resp)
	return resp


def post_stream(payload: dict, access: str, account: str) -> requests.Response:
	return requests.post(
		f"{API_BASE}/codex/responses",
		json=payload,
		headers=request_headers(access, account),
		stream=True,
		timeout=(CONNECT_TIMEOUT, READ_TIMEOUT),
	)


def request_headers(access: str, account: str, accept: str = "text/event-stream") -> dict:
	return {
		"Authorization": f"Bearer {access}",
		"chatgpt-account-id": account,
		"originator": ORIGINATOR,
		"OpenAI-Beta": "responses=experimental",
		"accept": accept,
		"content-type": "application/json",
	}


def http_error(resp: requests.Response) -> Exception:
	try:
		body = resp.text[:300]
	except Exception:
		body = ""
	message = f"Codex request failed ({resp.status_code}): {body}"
	if resp.status_code == 429:
		return RateLimitError(message)
	if resp.status_code >= 500:
		return InternalServerError(message)
	return CodexError(message)


def iter_sse(resp: requests.Response):
	data: list[str] = []
	for raw in resp.iter_lines():
		# decoded by hand: text/event-stream declares no charset, so requests'
		# decode_unicode would still yield bytes
		line = raw.decode("utf-8", "replace") if isinstance(raw, bytes) else (raw or "")
		line = line.strip()
		if not line:
			if data:
				yield parse_event("\n".join(data))
				data = []
			continue
		if line.startswith("data:"):
			value = line[len("data:") :].strip()
			if value == "[DONE]":
				break
			data.append(value)
	if data:
		yield parse_event("\n".join(data))


def parse_event(raw: str) -> dict:
	try:
		parsed = json.loads(raw)
	except ValueError:
		return {}
	return parsed if isinstance(parsed, dict) else {}


# --- SSE events -> chat-completion chunks ------------------------------------


class ChunkAssembler:
	"""Folds Responses SSE events into the chunk shape stream_tool_round and
	record_usage read. Tool-call arguments stream as deltas; the done event only
	tops up whatever the deltas had not sent, so nothing arrives twice."""

	def __init__(self):
		self.calls: dict[str, dict] = {}  # by item id and by call id
		self.order: list[dict] = []
		self.texted: set[str] = set()
		self.reasoning_parts: dict[str, tuple] = {}
		self.finished = False

	def feed(self, event: dict) -> list:
		kind = event.get("type")
		if kind in {"error", "response.failed"}:
			raise CodexError(error_detail(event))
		if kind == "response.output_item.added":
			return self.open_item(event.get("item") or {})
		if kind == "response.function_call_arguments.delta":
			return self.append_arguments(event)
		if kind in {"response.reasoning_summary_text.delta", "response.reasoning_text.delta"}:
			return self.append_reasoning(event)
		if kind == "response.output_text.delta":
			return self.append_text(event)
		if kind in {"response.output_item.done", "response.output_item.completed"}:
			return self.close_item(event.get("item") or {})
		if kind in {"response.completed", "response.done", "response.incomplete"}:
			return self.finish(event, truncated=kind == "response.incomplete")
		return []

	def open_item(self, item: dict) -> list:
		if item.get("type") != "function_call":
			return []
		call = self.register_call(item)
		delta = tool_call_delta(call["index"], call_id=call["id"], name=call["name"], arguments="")
		return [chunk(tool_calls=[delta])]

	def append_arguments(self, event: dict) -> list:
		call = self.find_call(event.get("item_id"), event.get("call_id"))
		delta = event.get("delta")
		if call is None or not isinstance(delta, str) or not delta:
			return []
		call["sent"] += len(delta)
		return [chunk(tool_calls=[tool_call_delta(call["index"], arguments=delta)])]

	def append_reasoning(self, event: dict) -> list:
		delta = event.get("delta")
		if not isinstance(delta, str) or not delta:
			return []
		item_id = event.get("item_id") or ""
		field = (
			"summary_index"
			if event.get("type") == "response.reasoning_summary_text.delta"
			else "content_index"
		)
		part = (field, event.get(field))
		previous = self.reasoning_parts.get(item_id)
		self.reasoning_parts[item_id] = part
		separator = "\n\n" if previous is not None and part != previous else ""
		return [chunk(reasoning=separator + delta)]

	def append_text(self, event: dict) -> list:
		delta = event.get("delta")
		if not isinstance(delta, str) or not delta:
			return []
		self.texted.add(event.get("item_id") or "")
		return [chunk(content=delta)]

	def close_item(self, item: dict) -> list:
		if item.get("type") == "function_call":
			return self.close_call(item)
		if item.get("type") == "message" and item.get("id") not in self.texted:
			# nothing streamed for this message, so the done text is all there is
			if text := message_text(item):
				return [chunk(content=text)]
		return []

	def close_call(self, item: dict) -> list:
		call = self.find_call(item.get("id"), item.get("call_id")) or self.register_call(item)
		remainder = (item.get("arguments") or "")[call["sent"] :]
		if not remainder:
			return []
		call["sent"] += len(remainder)
		delta = tool_call_delta(call["index"], call_id=call["id"], name=call["name"], arguments=remainder)
		return [chunk(tool_calls=[delta])]

	def finish(self, event: dict, *, truncated: bool) -> list:
		self.finished = True
		usage = (event.get("response") or {}).get("usage") or {}
		finish_reason = "length" if truncated else ("tool_calls" if self.order else "stop")
		return [chunk(finish_reason=finish_reason, usage=usage_of(usage))]

	def register_call(self, item: dict) -> dict:
		call = {
			"index": len(self.order),
			"id": item.get("call_id") or f"call_{len(self.order)}",
			"name": item.get("name") or "",
			"sent": 0,
		}
		self.order.append(call)
		for key in (item.get("id"), item.get("call_id")):
			if key:
				self.calls[key] = call
		return call

	def find_call(self, *keys) -> dict | None:
		for key in keys:
			if isinstance(key, str) and key in self.calls:
				return self.calls[key]
		# a lone call needs no id at all
		return self.order[0] if len(self.order) == 1 else None


def chunk(*, content=None, reasoning=None, tool_calls=None, finish_reason=None, usage=None):
	delta = SimpleNamespace(content=content, reasoning_content=reasoning, tool_calls=tool_calls)
	return SimpleNamespace(choices=[SimpleNamespace(delta=delta, finish_reason=finish_reason)], usage=usage)


def tool_call_delta(
	index: int, call_id: str | None = None, name: str | None = None, arguments: str | None = None
):
	return SimpleNamespace(index=index, id=call_id, function=SimpleNamespace(name=name, arguments=arguments))


def usage_of(usage: dict):
	prompt = usage.get("input_tokens") or 0
	completion = usage.get("output_tokens") or 0
	details = usage.get("input_tokens_details") or {}
	return SimpleNamespace(
		prompt_tokens=prompt,
		completion_tokens=completion,
		total_tokens=usage.get("total_tokens") or prompt + completion,
		prompt_tokens_details=SimpleNamespace(cached_tokens=details.get("cached_tokens") or 0),
	)


def message_text(item: dict) -> str:
	parts = item.get("content") or []
	return "".join(
		p.get("text") or "" for p in parts if isinstance(p, dict) and p.get("type") == "output_text"
	)


def error_detail(event: dict) -> str:
	error = event.get("error") or (event.get("response") or {}).get("error") or {}
	return error.get("message") or event.get("message") or "ChatGPT returned an error"


# --- chat transcript -> Responses payload ------------------------------------


def build_payload(model: str, messages: list, tools: list | None) -> dict:
	"""No tuning knobs on purpose: the backend rejects temperature and
	max_output_tokens outright (400 Unsupported parameter). The reasoning
	setting is required; without it the summary text never streams and the
	thinking step stays empty."""
	instructions, items = responses_input(messages)
	payload = {
		"model": model,
		"store": False,
		"stream": True,
		"instructions": instructions,
		"input": items,
		"reasoning": {"summary": "auto"},
		"tool_choice": "auto",
		"parallel_tool_calls": True,
	}
	if tools:
		payload["tools"] = responses_tools(tools)
	return payload


def responses_input(messages: list) -> tuple[str, list]:
	"""Split a chat transcript into Responses (instructions, input items).
	Leading system messages become instructions; anything the chat format carries
	that Responses does not (cache markers) is simply not copied."""
	instructions: list[str] = []
	items: list[dict] = []
	for m in messages:
		role = m.get("role")
		if role == "system" and not items and not instructions:
			instructions.append(content_text(m.get("content")))
		elif role in ("system", "user"):
			items.append({"role": "user", "content": user_content_parts(m.get("content"))})
		elif role == "assistant":
			items.extend(assistant_items(m, len(items)))
		elif role == "tool":
			items.append(
				{
					"type": "function_call_output",
					"call_id": m.get("tool_call_id") or "",
					"output": content_text(m.get("content")),
				}
			)
	return "\n\n".join(text for text in instructions if text), items


def assistant_items(message: dict, position: int) -> list:
	items = []
	if text := content_text(message.get("content")):
		items.append(
			{
				"type": "message",
				"role": "assistant",
				"status": "completed",
				"id": f"msg_{position}",
				"content": [{"type": "output_text", "text": text, "annotations": []}],
			}
		)
	# no item id on replayed calls: an id makes the server demand the reasoning
	# item that preceded it, which chat-format history cannot carry
	for tc in message.get("tool_calls") or []:
		fn = tc.get("function") or {}
		items.append(
			{
				"type": "function_call",
				"call_id": tc.get("id") or f"call_{position + len(items)}",
				"name": fn.get("name") or "",
				"arguments": fn.get("arguments") or "{}",
			}
		)
	return items


def user_content_parts(content) -> list:
	if not isinstance(content, list):
		return [{"type": "input_text", "text": content or ""}]
	parts = []
	for p in content:
		if not isinstance(p, dict):
			continue
		if p.get("type") == "image_url":
			parts.append({"type": "input_image", "image_url": (p.get("image_url") or {}).get("url") or ""})
		else:
			parts.append({"type": "input_text", "text": p.get("text") or ""})
	return parts


def content_text(content) -> str:
	if isinstance(content, list):
		return "".join(p.get("text") or "" for p in content if isinstance(p, dict))
	return content or ""


def responses_tools(tools: list) -> list:
	return [
		{
			"type": "function",
			"name": fn.get("name") or "",
			"description": fn.get("description") or "",
			"parameters": fn.get("parameters") or {},
			"strict": None,
		}
		for t in tools
		for fn in [t.get("function") or {}]
	]


# --- the OAuth credential ----------------------------------------------------


def runtime_auth(provider: str) -> tuple[str, str]:
	"""(access token, account id) for this provider, refreshed and persisted
	when stale."""
	cred = stored_credential(provider)
	if not cred.get("access") or cred.get("expires", 0) - REFRESH_SLACK_MS < time.time() * 1000:
		cred = refresh_credential(cred)
		save_credential(provider, cred)
	if not cred.get("account_id"):
		raise CodexError(
			"The ChatGPT credential is missing its account id. Sign in with ChatGPT again from AI settings."
		)
	return cred["access"], cred["account_id"]


def stored_credential(provider: str) -> dict:
	raw = frappe.get_cached_doc("Builder AI Provider", provider).resolved_key()
	if not raw:
		raise CodexError("No ChatGPT credential is saved. Sign in with ChatGPT from AI settings.")
	return parse_credential(raw)


def save_credential(provider: str, cred: dict) -> None:
	from frappe.utils.password import set_encrypted_password

	set_encrypted_password("Builder AI Provider", provider, json.dumps(cred), "api_key")


def parse_credential(raw: str) -> dict:
	"""Accept either shape: the CLI's auth.json or our own
	{access, refresh, expires, account_id}."""
	try:
		data = json.loads(raw or "")
	except ValueError:
		data = None
	if not isinstance(data, dict):
		raise CodexError(
			"That doesn't look like a ChatGPT credential. Sign in with ChatGPT, or paste the full contents of ~/.codex/auth.json."
		)
	if tokens := data.get("tokens"):
		access = tokens.get("access_token") or ""
		data = {
			"access": access,
			"refresh": tokens.get("refresh_token") or "",
			"expires": (jwt_claims(access).get("exp") or 0) * 1000,
			"account_id": tokens.get("account_id") or account_id_from_tokens(tokens.get("id_token"), access),
		}
	if not data.get("refresh"):
		raise CodexError("The credential has no refresh token. Sign in with ChatGPT again from AI settings.")
	return data


def refresh_credential(cred: dict) -> dict:
	# form-encoded on purpose: the token endpoint doesn't take JSON
	resp = requests.post(
		TOKEN_URL,
		data={"grant_type": "refresh_token", "client_id": CLIENT_ID, "refresh_token": cred["refresh"]},
		timeout=30,
	)
	if resp.status_code >= 400:
		raise CodexError("The ChatGPT sign-in has expired. Sign in with ChatGPT again from AI settings.")
	data = resp.json()
	access = data.get("access_token") or ""
	return {
		"access": access,
		"refresh": data.get("refresh_token") or cred["refresh"],
		"expires": int(time.time() * 1000) + int(data.get("expires_in") or 3600) * 1000,
		"account_id": cred.get("account_id") or account_id_from_tokens(data.get("id_token"), access),
	}


def account_id_from_tokens(id_token: str | None, access: str | None) -> str:
	"""The ChatGPT account id from whichever token carries it: a top-level claim,
	nested under the api.openai.com auth claim, or the first organization."""
	for token in (id_token, access):
		claims = jwt_claims(token or "")
		nested = claims.get("https://api.openai.com/auth")
		found = claims.get("chatgpt_account_id")
		if not found and isinstance(nested, dict):
			found = nested.get("chatgpt_account_id")
		if not found:
			found = first_org_id(claims)
		if found:
			return found
	return ""


def first_org_id(claims: dict) -> str:
	orgs = claims.get("organizations")
	if isinstance(orgs, list) and orgs and isinstance(orgs[0], dict):
		return orgs[0].get("id") or ""
	return ""


def jwt_claims(token: str) -> dict:
	try:
		payload = token.split(".")[1]
		return json.loads(base64.urlsafe_b64decode(payload + "=" * (-len(payload) % 4)))
	except Exception:
		return {}


def log(message: str) -> None:
	# lazy: frappe.logger opens a site log file, which import-time code must not
	logger = frappe.logger("builder.ai.codex")
	logger.setLevel(logging.INFO)
	logger.info(message)
