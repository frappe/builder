"""Model-aware input/output reservations and an honest per-attempt usage ledger."""

import copy
import json
import time

import frappe

from builder.ai.models import ModelRegistry

DEFAULT_RUN_TOKEN_BUDGET = 1_000_000


class RepairLimitError(ValueError):
	pass


class ContextBudgetError(ValueError):
	pass


class TurnBudgetError(ContextBudgetError):
	pass


class ModelCapabilityError(ContextBudgetError):
	pass


def estimate_tokens(messages, tools=None):
	text, images = [], 0
	for message in messages:
		item = {key: value for key, value in message.items() if not key.startswith("_bob_")}
		if isinstance(item.get("content"), list):
			parts = []
			for part in item["content"]:
				if part.get("type") == "image_url":
					images += 1
				else:
					parts.append(part)
			item["content"] = parts
		text.append(item)
	encoded = json.dumps({"messages": text, "tools": tools or []}, ensure_ascii=False)
	try:
		import tiktoken

		count = len(tiktoken.get_encoding("o200k_base").encode(encoded))
	except Exception:
		count = len(encoded.encode("utf-8"))
	return count + images * 4096 + len(messages) * 12


def fit_request(request, window, output_limit=None):
	request.messages = copy.deepcopy(request.messages)
	request.params = dict(request.params)
	reserve = min(int(request.params.get("max_tokens") or 4096), int(output_limit or window // 4))
	available = int(window * 0.9) - reserve - 1024
	if available < 1024:
		raise ContextBudgetError("This model's context is too small for the requested work")
	removed = 0
	while estimate_tokens(request.messages, request.tools) > available:
		# Remove a complete historical unit, never leave orphan tool results.
		candidates = [i for i, msg in enumerate(request.messages[:-2]) if i and not msg.get("_bob_keep")]
		if not candidates:
			raise ContextBudgetError(
				"The current page and request exceed this model's context. Select a smaller section or a larger-context model."
			)
		index = candidates[0]
		item = request.messages.pop(index)
		removed += 1
		if item.get("tool_calls"):
			ids = {call["id"] for call in item["tool_calls"]}
			request.messages = [msg for msg in request.messages if msg.get("tool_call_id") not in ids]
	for message in request.messages:
		message.pop("_bob_keep", None)
	request.params["max_tokens"] = reserve
	return {
		"estimated_input_tokens": estimate_tokens(request.messages, request.tools),
		"output_reserve": reserve,
		"context_window": window,
		"removed_messages": removed,
		"token_estimator": "o200k_base with image/framing allowance; byte fallback",
	}


def begin_attempt(ctx, request, purpose):
	contract = ModelRegistry.capabilities(request.model)
	if request.tools and not contract["tools"]:
		raise ModelCapabilityError(
			"This model is configured without tool support. Choose a tool-capable model."
		)
	if request.stream and not contract["streaming"]:
		raise ModelCapabilityError(
			"This model is configured without streaming support. Choose a streaming-capable model."
		)
	budget = fit_request(request, contract["context"], contract["output"])
	reserved = budget["estimated_input_tokens"] + budget["output_reserve"]
	maximum = int(frappe.conf.get("bob_run_token_budget") or DEFAULT_RUN_TOKEN_BUDGET)
	ctx.usage["token_budget"] = maximum
	used = ctx.usage.get("reserved_tokens", 0)
	if used + reserved > maximum:
		raise TurnBudgetError(
			"This turn reached its token budget. Review the saved work and continue in another turn."
		)
	ctx.usage["reserved_tokens"] = used + reserved
	entry = {
		"model": request.model,
		"purpose": purpose,
		"status": "started",
		"started": time.time(),
		"usage": None,
		"estimated_cost_usd": None,
		**budget,
	}
	ctx.usage.setdefault("ledger", []).append(entry)
	ctx.current_attempt = entry
	return entry


def finish_attempt(entry, status):
	entry.update(
		status=status,
		elapsed_ms=round((time.time() - entry["started"]) * 1000),
		missing_usage=entry["usage"] is None,
	)


def usage_cost(model, prompt, completion):
	# Unknown or subscription pricing stays unknown, never silently reported as free.
	prices = (frappe.conf.get("bob_model_prices") or {}).get(model)
	if not prices:
		return None
	return round(
		(prompt * float(prices["input_per_million"]) + completion * float(prices["output_per_million"]))
		/ 1_000_000,
		6,
	)
