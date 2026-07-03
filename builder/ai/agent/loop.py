"""The single agentic loop for Builder AI.

`AgentRunner` holds the per-request state, builds the message list, and drives
one tool-calling loop until the model stops requesting server/terminal tools.
Tool *behaviour* lives in the registry; this file only orchestrates.

Realtime event contract (consumed by the frontend). Every event name is
suffixed with the CHANNEL — the page id for the in-editor chat, or the session
id when page-less (dashboard chat + sub-agents), e.g. `ai_chat_stream_<channel>`:

    ai_chat_progress       {message}
    ai_chat_stream         {chunk, kind?}   kind="page_yaml" → apply to canvas;
                                            absent/"summary" → append to chat text
    ai_chat_tool_batch     {operations: [{tool_name, args}]}
    ai_chat_tool_activity  {id, tool, summary, status: "running"|"done", image_url?}
                           (same id emitted twice — running then done; upsert by id)
    ai_chat_clarify        {question, options, previews?,
                            plan_summary?, headline?, sections?, palette?}
    ai_chat_complete       {message}
    ai_chat_error          {message}

All events also carry {page_id}. Clarify messages are persisted+committed
before the event fires, so a session reload on receipt is race-free.
"""

import json
import logging
import re
import time

import frappe

from builder.ai import llm, locks
from builder.ai.agent.registry import ToolRegistry, build_default_registry
from builder.ai.agent.tree import WorkingTree
from builder.ai.block_codec import BlockCodec
from builder.ai.models import ModelRegistry
from builder.ai.prompts import Prompts
from builder.ai.session import AISession
from builder.ai.snapshots import capture_page_state, save_revert_snapshot
from builder.utils import to_compact_yaml

logger = frappe.logger("builder.ai.agent.loop")
logger.setLevel(logging.INFO)

# One turn may span several rounds: server-tool reads, plus a model that applies a
# page-wide change in batches across rounds. High enough to finish a big multi-block
# fix (a "fix everything" can drip a few edits per round on weaker models), bounded so
# a runaway loop can't spin. When the cap IS hit the turn ends with a "continue" hint.
MAX_ROUNDS = 40
EVENT_PREFIX = "ai_chat"

# A streaming round is retried on transient failure (litellm can't fall back mid-stream).
# Backoff is STREAM_BACKOFF_BASE * 2**attempt → ~1s, 2s before the final give-up.
STREAM_MAX_ATTEMPTS = 3
STREAM_BACKOFF_BASE = 1.0

# Tools whose changes a pre-turn snapshot can revert. The snapshot captures blocks +
# page data + client scripts, so block edits AND script create/edit are all undone by
# one "Revert" — no separate "undo script" action. A turn touching none of these (clarify,
# plan, no-op) creates no snapshot and gets no Revert button.
SNAPSHOT_TOOLS = frozenset(
	{
		"add_block",
		"update_block",
		"update_blocks",
		"remove_block",
		"move_block",
		"generate_page",
		"set_page_script",
		"update_script",
	}
)


class CancelledError(Exception):
	"""Raised inside the stream loops when the user cancels the turn."""


def looks_like_page_yaml(text: str) -> bool:
	"""Heuristic: did the model emit page YAML as plain content?"""
	if not text:
		return False
	stripped = re.sub(r"^```(?:yaml)?\s*", "", text.strip())
	return stripped.startswith(("el:", "- el:", "id: root", "- id:"))


# Past-tense verbs a summary uses when it CLAIMS it changed the page. The no-op-claim
# guard uses this: if the model says it did one of these but called no tool, nothing was
# applied — a hallucinated success (weaker models narrate the action instead of doing it).
ACTION_CLAIM_RE = re.compile(
	r"\b(added|created|updated|changed|removed|deleted|applied|attached|inserted|"
	r"replaced|moved|translated|restyled|recolou?red|rebuilt|built|wired|enabled|"
	r"adjusted|swapped|renamed|resized|reordered|set up)\b",
	re.IGNORECASE,
)

NOOP_CORRECTION = (
	"You wrote a summary describing changes, but you called no tools — so NOTHING was "
	"applied to the page. If the request needs a change, call the appropriate tool(s) now "
	"(update_block, update_blocks, add_block, set_page_script, …) and actually do the work. "
	"If no change is genuinely needed, or you were only answering a question, reply plainly "
	"and do NOT claim you changed anything."
)


def claims_unbacked_action(summary_text: str) -> bool:
	"""True if the summary reads like a completed edit ('Added a confetti burst…')."""
	return bool(summary_text) and bool(ACTION_CLAIM_RE.search(summary_text))


# Weaker models sometimes emit a pseudo tool call as plain TEXT instead of calling
# the tool ("calc:default_api:write_page_data_script{…}", "```tool_code…"). That
# must never reach the chat as the turn's summary. Conservative signals only —
# `default_api` is Gemini's function namespace, never natural prose.
TOOL_SYNTAX_RE = re.compile(r"\bdefault_api\b|<tool_code|```tool_code")


def looks_like_tool_syntax(text: str) -> bool:
	return bool(text) and bool(TOOL_SYNTAX_RE.search(text))


# Above this many chars of compact-YAML page structure, switch the page context
# from the full tree to a compact outline (read_block pulls detail on demand).
# Tuned so a typical multi-section page still ships in full; only big pages skeletonise.
FULL_CONTEXT_LIMIT = 9000

# Tools that already surface as their own card in the chat (clarify question, plan,
# task group) — no activity line for them.
ACTIVITY_SILENT = frozenset({"ask_clarification", "propose_plan", "spawn_parallel_agents"})

# Server tools that only READ. Everything else that runs server-side (settings, theme,
# data scripts, page creation, generation…) mutates real state — the no-op-claim guards
# must count that as backing for an action claim, or a purely-server-tool turn (the
# dashboard's normal mode) gets its truthful summary replaced with "I didn't apply it".
READ_ONLY_SERVER_TOOLS = frozenset(
	{
		"read_page",
		"open_page",
		"query_blocks",
		"read_block",
		"get_document",
		"query_records",
		"list_doctypes",
		"get_doctype_schema",
		"get_page_scripts",
		"preview_page",
	}
)


def render_page_context(root: dict | None, selected_block_ids: tuple | list = ()) -> str:
	"""Render a page's block tree as model-readable context: the full compact YAML
	for a normal page, or an outline (+ full detail for selected blocks) past
	FULL_CONTEXT_LIMIT. Shared by the turn's page-context message and the page
	tools (open_page / create_page / read_page)."""
	if root is None:
		return ""
	full = to_compact_yaml(BlockCodec.compress(root, depth=0, task_tier="complex"))
	# Small pages: ship the full structure — cheapest path is no extra read_block
	# round-trips, and the model can match existing styles directly. Big pages: ship
	# a compact outline instead (styles/attrs omitted) and let the model pull detail
	# on demand with read_block. The threshold is on the full serialisation length,
	# which tracks token cost closely.
	if len(full) <= FULL_CONTEXT_LIMIT:
		return f"Current page structure (YAML — pass a block's 'ref' value as block_id to edit it):\n{full}"
	return render_skeleton_context(root, selected_block_ids)


def render_skeleton_context(root: dict, selected_block_ids: tuple | list = ()) -> str:
	"""Outline + full detail for any blocks the user has selected (so the common
	targeted-edit case needs no read_block round-trip)."""
	from builder.ai.agent.selectors import find_block, render_skeleton

	outline = render_skeleton(root)
	parts = [
		"This page is large, so you're given a compact OUTLINE (one line per block: "
		"indentation = nesting, then ref, element, optional name, and a short text "
		"preview). Styles and attributes are omitted. Pass a block's ref as block_id to "
		"edit it. To see a block's full styles/attributes/text before editing, call "
		"read_block(ref); to act on many blocks at once, call query_blocks then "
		"update_blocks.",
		outline,
	]
	for ref in selected_block_ids:
		block = find_block(root, ref)
		if block is None:
			continue
		detail = to_compact_yaml(BlockCodec.compress(block, depth=0, task_tier="complex"))
		parts.append(f"Full detail for selected block {ref}:\n{detail}")
	return "\n\n".join(parts)


def activity_summary(tool_name: str, args: dict, tree=None) -> str:
	"""A short human line for the chat's live activity feed ("Read page: Home")."""
	args = args or {}

	def page_title(page_id: str | None) -> str:
		return (page_id and frappe.db.get_value("Builder Page", page_id, "page_title")) or page_id or "…"

	def block_label(ref: str | None) -> str:
		block = tree.resolve(ref) if (tree and ref) else None
		if block:
			return block.get("blockName") or f"<{block.get('element') or 'div'}>"
		return ref or ""

	if tool_name in ("read_page", "open_page"):
		verb = "Read" if tool_name == "read_page" else "Opened"
		line = f"{verb} page: {page_title(args.get('page_id'))}"
		if args.get("block_id"):
			line += " — one block"
		return line
	if tool_name == "create_page":
		return f"Created page: {args.get('page_title') or ''}".strip()
	if tool_name == "copy_page_design":
		return f"Copied design from {page_title(args.get('source_page_id'))}"
	if tool_name == "generate_page":
		return "Building the page"
	if tool_name == "preview_page":
		return "Screenshot"
	if tool_name == "read_block":
		return f"Read block: {block_label(args.get('block_id'))}".rstrip(": ")
	if tool_name == "query_blocks":
		return "Searched blocks"
	if tool_name == "set_theme_variable":
		return f"Set --{args['name']}" if args.get("name") else "Set theme variable"
	if tool_name == "set_page_script":
		return f"Added script: {args.get('name') or ''}".rstrip(": ")
	if tool_name == "update_script":
		return f"Updated script: {args.get('script_name') or ''}".rstrip(": ")
	if tool_name == "create_component":
		return f"Created component: {args.get('name') or ''}".strip()
	if tool_name in ("get_document", "query_records", "get_doctype_schema"):
		return f"Read {args.get('doctype') or 'records'}"
	return tool_name.replace("_", " ").capitalize()


class AgentRunner:
	FULL_CONTEXT_LIMIT = FULL_CONTEXT_LIMIT  # class alias for existing callers/tests

	def __init__(
		self,
		prompt: str,
		page_context_json: str,
		model: str,
		api_key: str,
		*,
		user: str | None = None,
		page_id: str | None = None,
		session_id: str | None = None,
		selected_block_ids: list[str] | None = None,
		image_url: str | None = None,
		registry: ToolRegistry | None = None,
		system_prompt: str | None = None,
		pre_turn_state: dict | None = None,
		headless: bool = False,
	):
		self.prompt = prompt
		self.page_context_json = page_context_json
		self.model = model
		self.api_key = api_key
		self.user = user or frappe.session.user
		self.page_id = page_id
		self.session_id = session_id
		# Headless = no browser/canvas (dashboard chat + fan-out sub-agents). Client
		# block/script ops can't be applied; work goes through server tools + page
		# generation persisted server-side (page_writer). Events are session-scoped.
		self.headless = headless or not page_id
		# The realtime channel is fixed at construction: focus_page() may change
		# self.page_id mid-turn (dashboard agent opening a page), and the chat that
		# started the turn must keep receiving events on the channel it subscribed to.
		self.channel = page_id or session_id
		self.selected_block_ids = selected_block_ids or []
		self.image_url = image_url
		self.registry = registry or build_default_registry()
		self.system_prompt = system_prompt or Prompts.AGENT_SYSTEM
		# The working tree is built lazily in run() (or by focus_page for headless
		# turns that open/create a page mid-turn).
		self.tree: WorkingTree | None = None
		# Page locks acquired via focus_page this turn; released in run()'s finally.
		self.held_locks: list[str] = []
		# Images a server tool wants shown to the model (e.g. a preview_page screenshot).
		# Drained after each round as a follow-up user message — OpenAI-shape tool
		# results can't reliably carry image parts through OpenRouter.
		self.pending_images: list[dict] = []
		# Live activity feed: one entry per server-tool call, streamed to the chat as
		# ai_chat_tool_activity events and persisted on the final message metadata.
		self.activity: list[dict] = []
		self.current_activity: dict | None = None
		# preview_page calls this turn — hard-capped so a screenshot loop can't run up cost.
		self.preview_count = 0
		# Successful WRITE-side server-tool calls this turn (settings, scripts, data,
		# page creation…) — counts as real work for the no-op-claim guards.
		self.server_mutations = 0
		# Page state captured before this turn (in api.run). A snapshot doc is created
		# from it ONLY if the turn mutates the page; its name lands on the final
		# assistant message as the revert handle. None when the page was empty.
		self.pre_turn_state = pre_turn_state
		self.revert_snapshot: str | None = None
		# Per-turn debug trace (one entry per round) + why the turn ended. Persisted on
		# the assistant message so the agent debugger can explain what the model did and
		# why it stopped (e.g. "model_finished after 1 round, 2 tool calls").
		self.trace: list[dict] = []
		self.stop_reason = ""
		# Set once the no-op-claim guard has spent its single corrective round this turn.
		self.noop_corrected = False
		# Debug signals: how many tool-arg blobs needed json_repair, and the finish_reason
		# of each LLM call (="length" flags truncation — the usual cause of broken args).
		self.args_repaired = 0
		self.finish_reasons: list[str | None] = []
		# Client ops the WorkingTree rejected (bad ref, wrong parent, partial bulk miss).
		# Each is fed back to the model to self-correct; also logged and surfaced here so a
		# "why didn't my edit land" is traceable in the agent debugger, not just live logs.
		self.tool_failures: list[str] = []
		# How many streaming rounds had to be retried after a transient failure this turn.
		# Surfaced like args_repaired so a flaky provider shows up in the data, not as a
		# silent turn failure.
		self.stream_retries = 0
		# Tiered model selection: resolved in run() once we know the scenario.
		self.loop_model = self.model
		# Per-turn token tally, summed across every LLM call this turn (the loop's
		# tool-calling rounds + the generation stream). Surfaced in debug metadata and
		# logged so the selector/tiered-context changes can be measured against baseline.
		# `cached_tokens` is the cache-read slice of prompt_tokens (cheap, ~10% price);
		# `per_call` keeps each call's split so a turn's cost can be read round by round.
		self.usage = {
			"prompt_tokens": 0,
			"completion_tokens": 0,
			"total_tokens": 0,
			"cached_tokens": 0,
			"calls": 0,
			"per_call": [],
		}

	# --- cancellation -----------------------------------------------------

	def cancel_key(self) -> str | None:
		return f"builder_ai_cancel:{self.session_id}" if self.session_id else None

	def is_cancelled(self) -> bool:
		key = self.cancel_key()
		# use_local_cache=False is critical: the cancel is set by a DIFFERENT
		# web worker, and Frappe's per-request local cache would otherwise
		# pin the first (miss) result and never re-read Redis.
		return bool(frappe.cache.get_value(key, use_local_cache=False)) if key else False

	def clear_cancel_flag(self) -> None:
		if key := self.cancel_key():
			frappe.cache.delete_value(key)

	def interruptible_sleep(self, seconds: float) -> None:
		"""Sleep in small steps so a cancel during retry backoff is honored within ~0.25s
		instead of blocking the worker for the full delay."""
		waited = 0.0
		while waited < seconds:
			if self.is_cancelled():
				raise CancelledError
			step = min(0.25, seconds - waited)
			time.sleep(step)
			waited += step

	# --- realtime ---------------------------------------------------------

	def emit(self, suffix: str, **kwargs):
		# The channel is the page (in-editor chat) or, page-less, the session (dashboard
		# chat + sub-agent progress). Fixed at construction — see self.channel.
		event = f"{EVENT_PREFIX}_{suffix}"
		if self.channel:
			event = f"{event}_{self.channel}"
		frappe.publish_realtime(
			event, {"page_id": self.page_id, "session_id": self.session_id, **kwargs}, user=self.user
		)

	def ensure_revert_snapshot(self) -> None:
		"""Create the pre-turn snapshot the first time the turn changes the block tree.
		Consumes pre_turn_state so it runs at most once — and runs as soon as the first
		block batch is applied, so even a cancelled multi-round edit stays revertable."""
		if self.pre_turn_state is None:
			return
		state, self.pre_turn_state = self.pre_turn_state, None
		self.revert_snapshot = save_revert_snapshot(self.page_id, state)

	@staticmethod
	def cached_prompt_tokens(usage) -> int:
		"""The cache-read slice of prompt tokens, across provider shapes: OpenAI/litellm
		put it under prompt_tokens_details.cached_tokens; Anthropic exposes
		cache_read_input_tokens. 0 when the provider reports neither."""
		details = getattr(usage, "prompt_tokens_details", None)
		if details and (cached := getattr(details, "cached_tokens", None)):
			return cached
		return getattr(usage, "cache_read_input_tokens", 0) or 0

	def record_usage(self, chunk) -> None:
		"""Add a streamed chunk's usage to the per-turn tally. Only the final chunk of
		a stream (stream_options.include_usage) carries usage; the rest are None."""
		usage = getattr(chunk, "usage", None)
		if not usage:
			return
		prompt = getattr(usage, "prompt_tokens", 0) or 0
		completion = getattr(usage, "completion_tokens", 0) or 0
		total = getattr(usage, "total_tokens", 0) or 0
		cached = self.cached_prompt_tokens(usage)
		self.usage["prompt_tokens"] += prompt
		self.usage["completion_tokens"] += completion
		self.usage["total_tokens"] += total
		self.usage["cached_tokens"] += cached
		self.usage["calls"] += 1
		self.usage["per_call"].append({"prompt": prompt, "completion": completion, "cached": cached})

	def record_round(self, round_index: int, tool_operations: list[dict], text: str) -> None:
		"""Append one round to the debug trace: which tools the model called (with
		truncated args) and any text it wrote. This is what the agent debugger reads to
		explain a turn — e.g. why it applied only N blocks."""
		self.trace.append(
			{
				"round": round_index,
				"tools": [
					{
						"name": op["tool_name"],
						"args": BlockCodec.truncate_for_log(
							json.dumps(op.get("args", {}), ensure_ascii=False), 300
						),
					}
					for op in tool_operations
				],
				"text": BlockCodec.truncate_for_log(text or "", 300),
			}
		)

	# --- message construction --------------------------------------------

	def build_page_context(self) -> str:
		return render_page_context(self.page_root(), self.selected_block_ids)

	def build_messages(self) -> list[dict]:
		messages: list[dict] = [
			{
				"role": "system",
				"content": self.system_prompt,
				"cache_control": {"type": "ephemeral"},
			},
		]

		if page_context_message := self.build_page_context():
			# Cache the page structure too (system prompt is the other breakpoint): it's
			# the largest stable block and is resent on every round of a multi-round edit,
			# so caching it cuts both latency and input cost across the loop.
			messages.append(
				{
					"role": "user",
					"content": page_context_message,
					"cache_control": {"type": "ephemeral"},
				}
			)
			messages.append(
				{
					"role": "assistant",
					"content": "Understood. I have the current page structure. What would you like me to change?",
				}
			)

		# Prior conversation as proper role-tagged turns (not a flattened system
		# blob) — the model handles dialogue better and we save the "User:"/
		# "Assistant:" prefix tokens on every call.
		messages.extend(AISession.build_context_messages_from_id(self.session_id))

		user_text = self.prompt
		if self.selected_block_ids:
			user_text += f"\n\n(User has selected: {', '.join(self.selected_block_ids)})"
		if self.image_url:
			messages.append(
				{
					"role": "user",
					"content": [
						{"type": "text", "text": user_text},
						{"type": "image_url", "image_url": {"url": self.image_url}},
					],
				}
			)
		else:
			messages.append({"role": "user", "content": user_text})
		return messages

	# --- LLM call ---------------------------------------------------------

	def call_tool_llm(self, messages: list[dict]) -> tuple[list[dict], str, list[dict]]:
		"""Stream one tool-calling round, retrying the WHOLE round on a transient stream
		failure (network drop, 429, 5xx, mid-stream reset). Safe because a round applies
		nothing until it returns — ops are emitted and `messages` mutated by the caller only
		after this returns, so a failed attempt leaves no partial state; we just re-issue the
		identical completion (the cached prefix makes the retry cheap). litellm can't fall
		back mid-stream (fallbacks are off while streaming), so this is the retry layer."""
		for attempt in range(STREAM_MAX_ATTEMPTS):
			try:
				return self.stream_tool_round(messages)
			except CancelledError:
				raise
			except Exception as exc:
				if attempt == STREAM_MAX_ATTEMPTS - 1 or not llm.is_retryable(exc):
					raise
				self.stream_retries += 1
				backoff = STREAM_BACKOFF_BASE * (2**attempt)
				logger.warning(
					"Stream round failed (attempt %d/%d): %s — retrying in %.1fs",
					attempt + 1,
					STREAM_MAX_ATTEMPTS,
					exc,
					backoff,
				)
				self.interruptible_sleep(backoff)

	def stream_tool_round(self, messages: list[dict]) -> tuple[list[dict], str, list[dict]]:
		"""Stream one tool-calling completion. Returns (tool_operations,
		text_content, raw_tool_calls). Side-effect-free until it returns (see
		call_tool_llm) — accumulates into locals only, so it is safe to re-run.

		Tool-call arguments are accumulated by index across chunks.
		`raw_tool_calls` reconstruct the assistant turn for a follow-up round.
		Large artifacts (e.g. a full page) are NOT streamed here — the model
		calls an artifact tool with a short brief, and the loop hands generation
		to that tool's generator, which streams the artifact as content.
		"""
		stream = llm.complete_with_tools(
			self.loop_model,
			messages,
			self.registry.schemas(),
			llm.TASK_PARAMS["agent"],
			api_key=self.api_key,
			stream=True,
		)

		content_parts: list[str] = []
		# index -> {"id", "name", "args"}; preserves call order across chunks.
		acc: dict[int, dict] = {}
		finish_reason = None

		for chunk in stream:
			if self.is_cancelled():
				try:
					stream.close()
				except Exception:
					pass
				raise CancelledError
			self.record_usage(chunk)
			# The final include_usage chunk carries usage but no choices.
			if not chunk.choices:
				continue
			if fr := chunk.choices[0].finish_reason:
				finish_reason = fr
			delta = chunk.choices[0].delta
			if getattr(delta, "content", None):
				content_parts.append(delta.content)
			for tc in getattr(delta, "tool_calls", None) or []:
				idx = tc.index if tc.index is not None else 0
				entry = acc.setdefault(idx, {"id": None, "name": None, "args": ""})
				if tc.id:
					entry["id"] = tc.id
				fn = getattr(tc, "function", None)
				if fn and fn.name:
					entry["name"] = fn.name
				if fn and fn.arguments:
					entry["args"] += fn.arguments

		tool_operations: list[dict] = []
		raw_tool_calls: list[dict] = []
		for idx in sorted(acc):
			entry = acc[idx]
			if not entry["name"]:
				continue
			raw_arguments = entry["args"] or ""
			parsed, repaired = llm.loads_tolerant(raw_arguments)
			truncated_args = BlockCodec.truncate_for_log(raw_arguments, 2000)
			if parsed is None:
				# Even tolerant parsing failed — don't silently drop to {} with no trace
				# (that surfaces as an empty plan/edit). Log it loudly.
				args = {}
				logger.warning(
					"AI tool args UNPARSEABLE (tool=%s): %s",
					entry["name"],
					truncated_args,
				)
			else:
				args = parsed if isinstance(parsed, dict) else {}
				if repaired:
					self.args_repaired += 1
					logger.warning(
						"AI tool args recovered via json_repair (tool=%s): %s",
						entry["name"],
						truncated_args,
					)
			logger.info(
				"AI tool response: tool=%s, repaired=%s, raw_arguments=%s",
				entry["name"],
				repaired,
				truncated_args,
			)
			tool_operations.append({"tool_name": entry["name"], "args": args})
			raw_tool_calls.append(
				{
					"id": entry["id"],
					"type": "function",
					"function": {"name": entry["name"], "arguments": raw_arguments},
				}
			)

		content = "".join(content_parts)
		self.finish_reasons.append(finish_reason)
		# finish_reason="length" means the model hit max_tokens mid-output — the usual
		# cause of truncated/unparseable tool args. Surface it as the prime suspect.
		if finish_reason == "length":
			logger.warning("Agent LLM hit max_tokens (finish_reason=length) — tool args may be truncated")
		logger.info(
			"Agent LLM responded: tool_calls=%d, has_text=%s, finish_reason=%s",
			len(tool_operations),
			bool(content),
			finish_reason,
		)
		return tool_operations, content, raw_tool_calls

	def page_root(self) -> dict | None:
		"""The current page's root block dict, or None if empty/invalid. Headless, the
		mutating working tree IS the page — edits made this turn are visible to context
		rebuilds and the query tools, with refs staying valid. The editor path parses
		the browser-shipped page_context_json (state at the start of the turn)."""
		if self.headless and self.tree is not None:
			return self.tree.root
		try:
			data = json.loads(self.page_context_json)
		except (json.JSONDecodeError, TypeError):
			return None
		if isinstance(data, list):
			data = data[0] if data else None
		return data if isinstance(data, dict) else None

	def focus_page(self, page_id: str, *, lock: bool = True) -> str:
		"""Point the turn at a page: load its blocks from the DB into a mutating
		working tree (context, query tools, and block edits all read/write it), and
		capture the pre-edit state so the turn stays revertable. With lock=True the
		page lock is held for the rest of the turn so parallel AI tasks can't fight
		over one page (sub-agents pass lock=False — their task runner already holds it).
		Returns the rendered page context — the tool result for open_page/create_page."""
		from builder.ai import page_writer

		key = locks.page_key(page_id)
		if lock and key not in self.held_locks:
			if not locks.acquire(key, locks.PAGE_LOCK_TTL):
				return (
					f"FAILED: page {page_id} is being edited by another AI task right now — "
					"try again in a moment."
				)
			self.held_locks.append(key)
		root = page_writer.load_page_root(page_id)
		self.page_id = page_id
		self.tree = WorkingTree(root, mutating=True)
		# One revert handle per focused page: a focus switch starts a fresh snapshot,
		# and the LAST focused page's handle lands on the message metadata.
		self.pre_turn_state = capture_page_state(page_id)
		self.revert_snapshot = None
		if root is None:
			return f"Opened page {page_id} — it is empty. Build it with generate_page."
		return f"Opened page {page_id}.\n{render_page_context(root, self.selected_block_ids)}"

	# --- live activity feed ------------------------------------------------

	def begin_activity(self, tool_name: str, args: dict) -> dict | None:
		entry = None
		if tool_name not in ACTIVITY_SILENT:
			entry = {
				"id": len(self.activity),
				"tool": tool_name,
				"summary": activity_summary(tool_name, args, self.tree),
				"status": "running",
			}
			# Working-page tools carry the page id so the chat can offer an "Open"
			# link on the line (create_page fills it in from its handler).
			if tool_name in ("open_page", "generate_page", "preview_page", "copy_page_design"):
				entry["page"] = (args or {}).get("page_id") or self.page_id
			self.activity.append(entry)
			self.current_activity = entry
			self.emit("tool_activity", **entry)
		return entry

	def end_activity(self, entry: dict | None) -> None:
		if entry is None:
			return
		entry["status"] = "done"
		self.current_activity = None
		self.emit("tool_activity", **entry)

	@staticmethod
	def describe_operations(operations: list[dict]) -> str:
		"""A deterministic one-line summary of applied ops — used when the model
		didn't return its own summary text, so we avoid a second LLM round trip."""
		from collections import Counter

		counts = Counter(op.get("tool_name") for op in operations)

		def blk(n: int) -> str:
			return "block" if n == 1 else "blocks"

		# update_blocks edits many blocks in one op — count the blocks it touched,
		# not the single call, so the summary reads "updated 12 blocks" not "1".
		batched = 0
		for op in operations:
			if op.get("tool_name") != "update_blocks":
				continue
			args = op.get("args") or {}
			patches = args.get("patches")
			batched += len(patches) if isinstance(patches, list) else len(args.get("block_ids") or [])

		parts: list[str] = []
		if n := counts.get("add_block"):
			parts.append(f"added {n} {blk(n)}")
		if n := (counts.get("update_block", 0) + batched):
			parts.append(f"updated {n} {blk(n)}")
		if n := counts.get("remove_block"):
			parts.append(f"removed {n} {blk(n)}")
		if n := counts.get("move_block"):
			parts.append(f"moved {n} {blk(n)}")
		if counts.get("set_page_script"):
			parts.append("added a script")
		if counts.get("update_script"):
			parts.append("updated a script")

		if not parts:
			n = len(operations)
			return f"Applied {n} change{'s' if n != 1 else ''} to the page."
		sentence = parts[0] if len(parts) == 1 else f"{', '.join(parts[:-1])} and {parts[-1]}"
		return sentence[0].upper() + sentence[1:] + "."

	# --- orchestration ----------------------------------------------------

	def emit_cancelled(self) -> None:
		msg = "Cancelled."
		AISession.try_append_message(
			self.session_id, "assistant", msg, message_type="status", metadata={"status": "cancelled"}
		)
		frappe.db.commit()
		self.emit("complete", message=msg)

	def run(self):
		# Clear any stale cancel flag from a previous turn before starting.
		self.clear_cancel_flag()
		started = time.monotonic()
		# Editing an existing page runs the loop on the user's CHOSEN model — edit
		# taste matters as much as generation taste, and silently downgrading a
		# deliberately-picked heavy model is the surest way to degrade output.
		# Headless turns (dashboard orchestrator + sub-agents) always use the chosen
		# model too: reading a reference page's design and writing sub-agent briefs is
		# quality-sensitive work even before any page is open. Only the editor's
		# lightweight empty-page conversation (clarify/plan) drops to the cheap model.
		has_content = self.page_root() is not None
		self.loop_model = (
			self.model if (has_content or self.headless) else ModelRegistry.get_simple(self.model)
		)
		logger.info(
			f"AgentRunner.run: page_id={self.page_id}, model={self.model}, loop_model={self.loop_model}, "
			f"session_id={self.session_id}, user={self.user}"
		)
		label = ModelRegistry.get_label(self.loop_model)
		self.emit("progress", message=f"Thinking with {label}" if label else "Thinking…")

		if self.session_id and AISession.is_session_running(self.session_id):
			logger.warning(f"AgentRunner.run: session {self.session_id} already running, rejecting")
			self.emit(
				"error", message="Another AI request is still processing. Please wait for it to finish."
			)
			return

		if self.session_id:
			try:
				AISession(frappe.get_doc(AISession.DOCTYPE, self.session_id)).set_running()
			except Exception:
				pass

		# A sub-agent arrives with its page assigned but no context loaded — focus it
		# now (its task runner already holds the page lock) so build_messages ships the
		# page structure and the query/block tools work on it.
		if self.headless and self.page_id and self.tree is None:
			self.focus_page(self.page_id, lock=False)
		messages = self.build_messages()
		# Mirror of the page tree this turn. The editor validates client ops against it
		# (the browser applies the real edit); headless, the tree IS the page and ops
		# mutate it for real (see WorkingTree).
		if self.tree is None:
			self.tree = WorkingTree(self.page_root(), mutating=self.headless)
		client_operations: list[dict] = []
		summary_text = ""

		try:
			for _round in range(MAX_ROUNDS):
				tool_operations, summary_text, raw_tool_calls = self.call_tool_llm(messages)
				self.record_round(_round, tool_operations, summary_text)

				# Classify each call. Artifact tools (e.g. generate_page) take
				# precedence over their nominal side — they're handled by their
				# generator, not emitted as a plain client op.
				terminal_ops, artifact_ops, server_ops, client_ops = [], [], [], []
				for op in tool_operations:
					tool = self.registry.get(op["tool_name"])
					if tool and tool.artifact:
						artifact_ops.append(op)
					elif self.registry.side(op["tool_name"]) == "terminal":
						terminal_ops.append(op)
					elif self.registry.side(op["tool_name"]) == "server":
						server_ops.append(op)
					else:
						client_ops.append(op)
				# A terminal tool ends the turn and hands control back to the user.
				# If the model emits more than one, the first wins (the turn is over).
				if terminal_ops:
					self.handle_terminal(terminal_ops[0])
					return

				# EDITOR: an artifact tool (full-page generation) is the turn's work —
				# its generator streams the artifact live to the canvas on the heavy
				# model and returns the canonical client op(s). Generation ends the loop.
				# HEADLESS: generation is a STEP, not the end — it falls through to the
				# tool-result loop below (run_headless_generation), where the page is
				# persisted, the context refreshed, and the model can read back and
				# refine what it built before finishing.
				if artifact_ops and not self.headless:
					self.stop_reason = "generated"
					self.ensure_revert_snapshot()  # generate_page replaces the block tree
					for op in artifact_ops:
						tool = self.registry.get(op["tool_name"])
						if tool and tool.generator:
							ops = tool.generator(self, op["args"])
							client_operations.extend(ops)
							if ops:
								self.emit("tool_batch", operations=ops)
					break

				# Apply this round's edits immediately so the canvas updates live and the
				# user sees progress during a long multi-block change.
				if client_ops:
					if any(op["tool_name"] in SNAPSHOT_TOOLS for op in client_ops):
						self.ensure_revert_snapshot()
					client_operations.extend(client_ops)
					self.emit("tool_batch", operations=client_ops)

				# Live narration: surface what the model said / did THIS round so a long
				# multi-round turn shows real progress instead of a frozen "Applying…".
				# Only for rounds that CONTINUE — the final round's text is the turn summary.
				if tool_operations:
					note = (summary_text or "").strip()
					if looks_like_tool_syntax(note):
						note = ""
					if not note and client_ops:
						note = self.describe_operations(client_ops)
					if note:
						self.emit("progress", message=note)

				# Keep looping as long as the model is still calling tools. A page-wide
				# change (translate every block, restyle all buttons) spans several rounds,
				# emitting a batch each round; the model ENDS the turn by replying with a
				# final summary and NO tool calls. (Previously the loop broke after the
				# first client-only round, so bulk edits silently did just the first few.)
				if not tool_operations:
					# No-op-claim guard: the model wrote a summary that CLAIMS an edit but
					# called no tool, and nothing has been applied this whole turn — a
					# hallucinated success (weaker models narrate instead of acting). Spend
					# exactly one corrective round telling it to actually call the tools.
					if (
						not client_operations
						and not self.server_mutations
						and not self.noop_corrected
						and claims_unbacked_action(summary_text)
					):
						self.noop_corrected = True
						self.stop_reason = "noop_retry"
						logger.warning(
							"No-op claim from model (no tools called): %s",
							BlockCodec.truncate_for_log(summary_text, 300),
						)
						messages.append({"role": "assistant", "content": summary_text})
						messages.append({"role": "user", "content": NOOP_CORRECTION})
						continue
					self.stop_reason = "model_finished"
					break

				messages.append(
					{"role": "assistant", "content": summary_text or None, "tool_calls": raw_tool_calls}
				)
				for tc_dict, op in zip(raw_tool_calls, tool_operations, strict=True):
					tool = self.registry.get(op["tool_name"])
					if tool and tool.artifact and tool.generator:
						# Only reachable headless — the editor broke out of the loop above.
						content, ops = self.run_headless_generation(tool, op)
						client_operations.extend(ops)
					elif tool and tool.side == "server" and tool.handler:
						entry = self.begin_activity(op["tool_name"], op["args"])
						content = tool.handler(self, op["args"])
						self.end_activity(entry)
						if op["tool_name"] not in READ_ONLY_SERVER_TOOLS and not str(content).startswith(
							"FAILED"
						):
							self.server_mutations += 1
					elif self.headless and tool and tool.handler:
						# A client-side tool with a server twin (page scripts): no browser
						# here, so the handler applies it directly.
						entry = self.begin_activity(op["tool_name"], op["args"])
						content = tool.handler(self, op["args"])
						self.end_activity(entry)
						if not str(content).startswith("FAILED"):
							self.server_mutations += 1
					else:
						content = self.tree.apply(op["tool_name"], op["args"])
						# "FAILED" (hard miss) or "NOT FOUND" (partial bulk miss) — a correction
						# the model is now being asked to make. Record + log so it's not invisible.
						if "FAILED" in content or "NOT FOUND" in content:
							self.tool_failures.append(f"{op['tool_name']}: {content}")
							logger.warning("Client op rejected — %s: %s", op["tool_name"], content)
					messages.append({"role": "tool", "tool_call_id": tc_dict["id"], "content": content})

				# Headless block edits mutated the working tree for real — persist after
				# every applied round so a cancel/crash keeps the work done so far (the
				# same live-apply semantics the editor canvas gives).
				if self.headless and self.page_id and client_ops and self.tree.root:
					from builder.ai import page_writer

					page_writer.save_draft_blocks(self.page_id, self.tree.root)

				# Images a tool captured this round (preview_page screenshots) ride a
				# follow-up user message — appended only after every role:"tool" result,
				# as the OpenAI message shape requires.
				for img in self.pending_images:
					messages.append(
						{
							"role": "user",
							"content": [
								{"type": "text", "text": img["caption"]},
								{"type": "image_url", "image_url": {"url": img["data_url"]}},
							],
						}
					)
				self.pending_images.clear()
			else:
				# Loop ran the full MAX_ROUNDS without the model finishing — a very large
				# bulk edit or a stuck loop. The work done so far still applies.
				self.stop_reason = "max_rounds"

		except CancelledError:
			self.emit_cancelled()
			return
		except Exception as e:
			logger.error(f"Agent LLM call failed: {e!s}", exc_info=True)
			frappe.log_error(f"Agent LLM call failed: {e}", "AgentRunner.run")
			# Show a generic message to the user — raw provider/exception strings can
			# leak internals (keys, model ids, stack detail). Full error is logged above.
			user_msg = "Something went wrong while building your changes. Please try again."
			AISession.try_append_message(
				self.session_id, "assistant", user_msg, message_type="status", metadata={"status": "error"}
			)
			frappe.db.commit()  # commit before emit so the client's reload sees it
			self.emit("error", message=user_msg)
			return
		finally:
			self.clear_cancel_flag()
			for key in self.held_locks:
				locks.release(key)
			self.held_locks = []
			if self.session_id:
				try:
					AISession(frappe.get_doc(AISession.DOCTYPE, self.session_id)).clear_running()
				except Exception:
					pass

		# Defensive: a weaker model may emit page YAML as content instead of
		# calling generate_page. Treat that as a synthetic generate_page op.
		if not client_operations and looks_like_page_yaml(summary_text):
			logger.info("Recovering YAML-as-content into a synthetic generate_page op")
			yaml_text = BlockCodec.strip_fences(summary_text)
			op = {"tool_name": "generate_page", "args": {"yaml": yaml_text}}
			client_operations.append(op)
			if self.headless:
				# No canvas to stream to — persist the page server-side, as the
				# artifact generator does on the happy path.
				if self.page_id:
					from builder.ai import page_writer

					page_writer.persist_page(self.page_id, yaml_text)
			else:
				self.ensure_revert_snapshot()
				self.emit("stream", chunk=yaml_text, kind="page_yaml")
				self.emit("tool_batch", operations=[op])
			summary_text = ""

		# Leaked tool-call syntax is never a summary — suppress it. With applied work
		# the deterministic fallbacks below take over; with none, say what happened.
		if looks_like_tool_syntax(summary_text):
			logger.warning(
				"Suppressed tool-syntax leak in summary: %s", BlockCodec.truncate_for_log(summary_text, 300)
			)
			summary_text = (
				""
				if client_operations
				else "My last step came out garbled and was not applied — ask me to try that again."
			)

		if not client_operations and not summary_text:
			# A soft miss, not a failure: the model may have done real tool work (reads)
			# and just failed to write its reply. Warn — and persist, so the turn doesn't
			# vanish on reload.
			logger.warning("Agent returned empty response (no text; activity=%d)", len(self.activity))
			if self.server_mutations:
				note = "Done — the steps above were applied (I skipped the write-up)."
			elif self.activity:
				note = (
					"I gathered that information but didn't write up a reply — ask me again and I'll answer."
				)
			else:
				note = "I came back empty on that one — try rephrasing your request."
			metadata = {"status": "warning"}
			if self.activity:
				metadata["activity"] = self.activity
			AISession.try_append_message(
				self.session_id, "assistant", note, message_type="status", metadata=metadata
			)
			frappe.db.commit()
			self.emit("error", message=note, warning=True)
			return

		# Backstop: the model still claims an edit it never made (no ops applied, no
		# server-side writes, even after the corrective round). Don't present a
		# hallucinated success — say so.
		if not client_operations and not self.server_mutations and claims_unbacked_action(summary_text):
			logger.warning(
				"Unbacked action claim persisted (no ops applied): %s",
				BlockCodec.truncate_for_log(summary_text, 300),
			)
			summary_text = (
				"I described that change but didn't actually apply it — so nothing on the page "
				"changed. Could you rephrase, or tell me more specifically what to change?"
			)
			self.stop_reason = self.stop_reason or "noop_unbacked"

		# Block/script edits and generation ops were already emitted incrementally inside
		# the loop (live canvas progress); nothing more to emit here.
		generated = any(op["tool_name"] == "generate_page" for op in client_operations)
		if summary_text:
			# The model wrote a summary alongside its tool calls — richest, and
			# free (no extra round trip). Prefer it whenever present.
			self.emit("stream", chunk=summary_text)
		elif generated:
			# Skip a summary call after generation (the YAML arg would bloat its
			# context); send a fixed nudge instead.
			summary_text = (
				"Created the page. Ask me to refine it — adjust styles, add sections, or change the layout."
			)
			self.emit("stream", chunk=summary_text)
		else:
			# Block/script edits with no model text: synthesise the summary from
			# the ops rather than making a second LLM call. The canvas already
			# updated from the tool_batch above; this just ends the turn sooner.
			summary_text = self.describe_operations(client_operations)
			self.emit("stream", chunk=summary_text)

		# Hit the per-turn round cap → the work is INCOMPLETE. Say so, so a big edit
		# doesn't look finished; the user can reply "continue" to resume from here.
		if self.stop_reason == "max_rounds":
			hint = '\n\n⚠️ I hit my edit-step limit for one turn before finishing — reply "continue" and I\'ll pick up where I left off.'
			summary_text += hint
			self.emit("stream", chunk=hint)

		# The revert snapshot was created lazily during the loop, the first time a block
		# change was applied (see ensure_revert_snapshot). Script-only / no-op / clarify
		# turns never trigger it, so they carry no revert handle.
		elapsed_ms = round((time.monotonic() - started) * 1000)
		logger.info(
			"AI turn done | page=%s rounds=%d llm_calls=%d prompt_tokens=%d "
			"cached_tokens=%d completion_tokens=%d total_tokens=%d tool_failures=%d "
			"stream_retries=%d elapsed_ms=%d stop=%s",
			self.page_id,
			len(self.trace),
			self.usage["calls"],
			self.usage["prompt_tokens"],
			self.usage["cached_tokens"],
			self.usage["completion_tokens"],
			self.usage["total_tokens"],
			len(self.tool_failures),
			self.stream_retries,
			elapsed_ms,
			self.stop_reason or "model_finished",
		)
		final_metadata = {
			"status": "complete",
			"model": self.model,
			"operations": len(client_operations),
			# Trace for the agent debugger: why the turn ended + what the model did each
			# round. Explains cases like "only 2 blocks updated" at a glance.
			"debug": {
				"stopReason": self.stop_reason or "model_finished",
				"loopModel": self.loop_model,
				"rounds": len(self.trace),
				"noopCorrected": self.noop_corrected,
				"argsRepaired": self.args_repaired,
				"finishReasons": self.finish_reasons,
				"toolFailures": self.tool_failures,
				"streamRetries": self.stream_retries,
				# Per-turn cost signal for the selector/tiered-context experiment.
				"tokens": self.usage,
				"elapsedMs": elapsed_ms,
				"trace": self.trace,
			},
		}
		if self.revert_snapshot:
			final_metadata["revertSnapshot"] = self.revert_snapshot
		if self.activity:
			# The chat's activity feed (tool lines + screenshots) — rendered live from
			# tool_activity events, rehydrated from here on a session reload.
			final_metadata["activity"] = self.activity
		AISession.try_append_message(
			self.session_id,
			"assistant",
			summary_text or f"Applying {len(client_operations)} change(s).",
			message_type="chat",
			task_type="agent",
			metadata=final_metadata,
		)
		frappe.db.commit()  # commit before emit so the client's reload sees the final turn
		self.emit("complete", message=summary_text or "Done")

	def handle_terminal(self, op: dict):
		"""Run a terminal tool's handler (which emits the appropriate event and
		persists the message). Terminal tools register a handler."""
		tool = self.registry.get(op["tool_name"])
		if tool and tool.handler:
			tool.handler(self, op["args"])

	def run_headless_generation(self, tool, op: dict) -> tuple[str, list[dict]]:
		"""Run generate_page as one STEP of a headless turn. The generator persists the
		page server-side (page_writer.persist_page); reload it into the working tree so
		the model can read back — and surgically refine — what it just built."""
		from builder.ai import page_writer

		if not self.page_id:
			return ("FAILED: no page is open — call create_page or open_page first, then generate.", [])
		entry = self.begin_activity(op["tool_name"], op["args"])
		self.ensure_revert_snapshot()  # generation replaces the block tree
		try:
			ops = tool.generator(self, op["args"])
		except ValueError as e:
			self.end_activity(entry)
			return (f"FAILED: {e}. Retry generate_page with a fuller brief.", [])
		self.end_activity(entry)
		if not ops:
			return ("FAILED: generation produced nothing. Retry generate_page with a fuller brief.", [])
		root = page_writer.load_page_root(self.page_id)
		self.tree = WorkingTree(root, mutating=True)
		context = render_page_context(root)
		return (
			"Page generated and saved. Verify it (preview_page / read_block), make surgical "
			f"fixes with the block tools if needed, then finish with a short summary.\n{context}",
			ops,
		)


def run_agent_job(prompt: str, page_context_json: str, model: str, api_key: str, **kwargs):
	# A page-less turn is the dashboard orchestrator: no canvas, so it uses the
	# orchestrator registry (server tools + parallel fan-out) and its own system prompt.
	# The registry is built HERE (in the worker) rather than pickled through enqueue.
	if not kwargs.get("page_id") and not kwargs.get("registry"):
		from builder.ai.agent.registry import build_orchestrator_registry

		kwargs["registry"] = build_orchestrator_registry()
		# The editor's URL prefix is site-configurable — resolve it here so the
		# links the agent writes actually work on this site.
		builder_path = frappe.conf.builder_path or "builder"
		kwargs.setdefault(
			"system_prompt", Prompts.ORCHESTRATOR_SYSTEM.replace("{BUILDER_PATH}", builder_path)
		)
		kwargs["headless"] = True
	AgentRunner(prompt, page_context_json, model, api_key, **kwargs).run()
