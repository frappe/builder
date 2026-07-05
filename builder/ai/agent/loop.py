"""The single agentic loop for Builder AI.

`AgentRunner` holds the per-request state, builds the message list, and drives
one tool-calling loop until the model stops requesting tools. Tool *behaviour*
lives in the registry; this file only orchestrates.

The server is authoritative for every turn: the page is loaded from the DB into
a mutating `WorkingTree`, ops are applied there first and persisted after each
round, and the accepted ops are mirrored to the editor canvas (which is a live
VIEW, not a second source of truth). Ops the tree rejects are never emitted, so
canvas and server can't diverge.

Realtime event contract (consumed by the frontend). Every event name is
suffixed with the CHANNEL — the page id for the in-editor chat, or the session
id when page-less (dashboard chat + sub-agents), e.g. `ai_chat_stream_<channel>`:

    ai_chat_progress       {message}
    ai_chat_stream         {chunk, kind?}   kind="page_yaml" → live canvas preview;
                                            absent/"summary" → append to chat text
    ai_chat_tool_batch     {operations: [{tool_name, args}]}
                           (generate_page args carry the expanded {blocks, data_script};
                           add_block args carry block_json — the canvas applies those
                           verbatim so both sides share block ids)
    ai_chat_tool_activity  {id, tool, summary, status: "running"|"done", image_url?}
                           (same id emitted twice — running then done; upsert by id)
    ai_chat_clarify        {question, ui: [element]}   generic card the agent
                           composed (present_ui); renderer skips unknown element
                           kinds. Confirm-gated actions add {pending_action}.
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
		"set_page_blocks",
		"generate_page",
		"set_page_script",
		"update_script",
	}
)

# Script tools ALWAYS apply through their server handlers, editor sessions included.
# Applying them in the browser (frappe.client.insert from toolDispatch) lost scripts
# silently — two parallel attaches in one round raced and .catch(() => null) ate the
# failure; a page then published with its reveal CSS but not the JS that fires it.
# The server apply is atomic and verified; the canvas just mirrors the result.
SCRIPT_TWIN_TOOLS = frozenset({"set_page_script", "update_script"})


class CancelledError(Exception):
	"""Raised inside the stream loops when the user cancels the turn."""


def looks_like_page_yaml(text: str) -> bool:
	"""Heuristic: did the model emit page YAML as plain content?"""
	if not text:
		return False
	stripped = re.sub(r"^```(?:yaml)?\s*", "", text.strip())
	return stripped.startswith(("el:", "- el:", "id: root", "- id:"))


# First-person / sentence-initial past-tense claims that the page was changed. The
# no-op-claim guard uses this: if the model says it did the work but called no tool,
# nothing was applied — a hallucinated success (weaker models narrate the action
# instead of doing it). Anchored to "I added…" / "Added a…" shapes so a truthful
# answer ABOUT past work ("your page was created last week") doesn't trip it.
ACTION_VERBS = (
	"added|created|updated|changed|removed|deleted|applied|attached|inserted|"
	"replaced|moved|translated|restyled|recolou?red|rebuilt|built|wired|enabled|"
	"adjusted|swapped|renamed|resized|reordered|set up"
)
ACTION_CLAIM_RE = re.compile(
	rf"\b(?:I|I've|I have|we|we've)(?:\s+\w+){{0,2}}\s+(?:{ACTION_VERBS})\b"
	rf"|^\s*(?:{ACTION_VERBS})\b",
	re.IGNORECASE | re.MULTILINE,
)

NOOP_CORRECTION = (
	"You wrote a summary describing changes, but you called no tools — so NOTHING was "
	"applied to the page. If the request needs a change, call the appropriate tool(s) now "
	"(update_block/add_block for targeted edits, run_python for bulk mutations, "
	"set_page_script, generate_page, …) and actually do the work. If no change is genuinely "
	"needed, or you were only answering a question, reply plainly and do NOT claim you "
	"changed anything."
)


def claims_unbacked_action(summary_text: str) -> bool:
	"""True if the summary reads like a completed edit ('Added a confetti burst…')."""
	return bool(summary_text) and bool(ACTION_CLAIM_RE.search(summary_text))


# Persisted present_ui cards replay to the model as plain text ("[buttons: …]"),
# and a model can MIMIC that format — writing a card as chat text instead of
# calling present_ui. Text renders no controls, so the user is stuck.
CARD_TEXT_RE = re.compile(r"\[\s*(?:input|choices|buttons|upload|swatches|sketch)\s*:", re.IGNORECASE)

CARD_CORRECTION = (
	"Your last message wrote an interactive card as plain TEXT (markup like [input: …] "
	"or a raw JSON blob). Text renders NO controls — the user cannot answer it. "
	"Ask again properly: ONE present_ui call composing the same fields from its ui atoms "
	"(input/choices/upload/actions), following the tool's exact schema. Do not repeat "
	"the markup or JSON in your text."
)


def looks_like_card_text(summary_text: str) -> bool:
	return bool(summary_text) and bool(CARD_TEXT_RE.search(summary_text))


# The subtler mimic: a question with enumerated options written as clean prose
# ("Choose a typography pairing: • Syne + Albert Sans — … • …"). No card markup,
# so CARD_TEXT_RE misses it — but the user gets a dead list instead of tappable
# chips, and one such message in the history teaches the model to answer every
# later question the same way (the design flow degrades permanently).
BULLET_LINE_RE = re.compile(r"(?m)^\s*(?:[-*•]|\d+[.)])\s+\S")
ASKS_CHOICE_RE = re.compile(
	r"(?mi)^\s*(?:choose|pick|select|which|what(?:'s| is)? your|would you (?:like|prefer)|let me know which|"
	r"here are|let's (?:explore|look at)|consider (?:these|the following)|a few (?:more )?options)\b"
)
# Option-DECORATION markers (fonts/palette/layout/image) are the exact format
# option_text() replays a card in — a model writing "[fonts: Fraunces + Albert Sans]"
# in a bullet is mimicking a past card as prose, whatever the lead-in reads like.
OPTION_MARKER_RE = re.compile(r"\[\s*(?:fonts?|palette|layout|image)\s*:", re.IGNORECASE)

OPTIONS_AS_TEXT_CORRECTION = (
	"You ended your turn by asking a question with a LIST OF OPTIONS as plain text — text "
	"renders no controls, so the user has nothing to tap. Ask it again as ONE present_ui "
	"call: a single short lead-in `text` atom, then a `choices` group with one option per "
	"item (label + short description; include `font` for font pairings and `svg`+`colors` "
	"for layout directions so previews render). A single-question card needs no extra "
	"button. Do NOT repeat the options in your message text."
)


def asks_options_as_text(summary_text: str) -> bool:
	"""True when a no-tool round poses a multi-option question as prose (2+ bullets
	plus either a question, a presenting lead-in, or leaked card-option markers)."""
	text = (summary_text or "").strip()
	if not text or len(BULLET_LINE_RE.findall(text)) < 2:
		return False
	return "?" in text or bool(ASKS_CHOICE_RE.search(text)) or bool(OPTION_MARKER_RE.search(text))


# Weaker models sometimes emit a pseudo tool call as plain TEXT instead of calling
# the tool ("calc:default_api:write_page_data_script{…}", "```tool_code…"). That
# must never reach the chat as the turn's summary. Conservative signals only —
# `default_api` is Gemini's function namespace, never natural prose.
TOOL_SYNTAX_RE = re.compile(r"\bdefault_api\b|<tool_code|```tool_code")


def looks_like_tool_syntax(text: str) -> bool:
	return bool(text) and bool(TOOL_SYNTAX_RE.search(text))


# Weaker models sometimes emit their tool call as a plain-text JSON blob instead
# of a native tool call — without salvage the raw JSON lands in the chat as the
# turn's summary. Two salvageable shapes (an optional prose prefix is tolerated):
# a wrapped call ({"type": "present_ui", "args": {…}}) naming a REGISTERED tool,
# and bare present_ui args ({"text": …, "ui": […]} — the exact schema, nothing
# looser). Card-ish JSON that matches neither (hallucinated schemas) gets the
# corrective round instead — see looks_like_json_card.
TEXT_TOOL_NAME_KEYS = ("type", "name", "tool", "tool_name")
TEXT_TOOL_ARG_KEYS = ("args", "arguments", "parameters", "input")
UI_CARD_KEYS = frozenset({"ui", "choices", "options", "buttons", "inputs", "swatches", "upload"})


def split_trailing_json(text: str) -> tuple[str, str | None]:
	"""Split "prose… {json}" into (prose, blob). The blob must run to the end of
	the message; code fences are tolerated. blob is None when there isn't one."""
	text = (text or "").strip()
	if text.startswith("```"):
		text = re.sub(r"^```[a-zA-Z]*\s*|\s*```$", "", text).strip()
	start = text.find("{")
	if start == -1 or not text.endswith("}"):
		return text, None
	return text[:start].strip(), text[start:]


def parse_text_tool_call(text: str, known_tools: list[str]) -> tuple[str, dict, str] | None:
	"""Salvage a tool call the model wrote as text. Returns (tool_name, args,
	prose_prefix) or None when nothing safely matches."""
	prose, blob = split_trailing_json(text)
	if not blob:
		return None
	parsed, _ = llm.loads_tolerant(blob)
	if not isinstance(parsed, dict):
		return None
	name = next((parsed[k] for k in TEXT_TOOL_NAME_KEYS if isinstance(parsed.get(k), str)), None)
	if name in known_tools:
		args = next((parsed[k] for k in TEXT_TOOL_ARG_KEYS if isinstance(parsed.get(k), dict)), {})
		return name, args, prose
	if (
		"present_ui" in known_tools
		and isinstance(parsed.get("text"), str)
		and isinstance(parsed.get("ui"), list)
	):
		return "present_ui", parsed, prose
	return None


def looks_like_json_card(text: str) -> bool:
	"""A JSON blob that TRIES to be an interactive card but matches no salvageable
	shape (hallucinated schema, e.g. {"text": …, "choices": {…}, "actions": {…}}).
	Mapping arbitrary invented schemas is a losing game — send the model a
	corrective round instead."""
	_, blob = split_trailing_json(text)
	if not blob:
		return False
	parsed, _ = llm.loads_tolerant(blob)
	return (
		isinstance(parsed, dict)
		and isinstance(parsed.get("text"), str)
		and bool(UI_CARD_KEYS & parsed.keys())
	)


# Above this many chars of compact-YAML page structure, switch the page context
# from the full tree to a compact outline (read_block pulls detail on demand).
# Tuned so a typical multi-section page still ships in full; only big pages skeletonise.
FULL_CONTEXT_LIMIT = 9000

# Tools that already surface as their own card in the chat (clarify question, plan,
# task group) — no activity line for them.
ACTIVITY_SILENT = frozenset({"present_ui", "spawn_parallel_agents"})

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

# --- prompt-cache breakpoints (Claude via OpenRouter; stripped elsewhere) ------
# Ported from the agent-v2 rewrite, where this scheme measured ~90% cache reads
# on real multi-round builds (~80% input-cost cut). The system breakpoint holds
# the prompt + tools; user turns are minutes apart, so the default 5-minute TTL
# would expire between turns — 1h costs 2x to write but breaks even by the third
# turn of a session.
SYSTEM_CACHE_CONTROL = {"type": "ephemeral", "ttl": "1h"}
TURN_CACHE_CONTROL = {"type": "ephemeral"}
# Anthropic allows at most 4 cache_control markers per request.
MAX_CACHE_MARKERS = 4
# Anthropic matches an existing cache entry only within ~20 content blocks
# behind a marker; long turns get a mid-turn anchor every this many messages so
# consecutive rounds always land inside the lookback window.
MID_TURN_MARKER_EVERY = 15


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
		"update_blocks, or run_python (refs are blockIds in the `page` dict it sees).",
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
	if tool_name == "set_design_token":
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
	def __init__(
		self,
		prompt: str,
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
		headless: bool = False,
	):
		self.prompt = prompt
		self.model = model
		self.api_key = api_key
		self.user = user or frappe.session.user
		self.page_id = page_id
		self.session_id = session_id
		# Headless = no browser/canvas listening (dashboard chat + fan-out sub-agents):
		# no page-YAML streaming, and client tools with a server twin (page scripts)
		# apply via their handlers. Block edits are server-applied in BOTH modes.
		self.headless = headless or not page_id
		# The realtime channel is fixed at construction: focus_page() may change
		# self.page_id mid-turn (the agent opening another page), and the chat that
		# started the turn must keep receiving events on the channel it subscribed to.
		self.channel = page_id or session_id
		# The page the user's editor canvas is showing (None headless). When focus
		# moves to ANOTHER page mid-turn, client tools with a server twin must apply
		# server-side — the canvas can't apply ops for a page it isn't showing.
		self.canvas_page_id = page_id if not self.headless else None
		self.selected_block_ids = selected_block_ids or []
		self.image_url = image_url
		self.registry = registry or build_default_registry()
		# The editor-URL prefix is site-configurable; resolve it so the links the
		# agent writes (e.g. to a page it built off-canvas) actually work here.
		self.system_prompt = (system_prompt or Prompts.AGENT_SYSTEM).replace(
			"{BUILDER_PATH}", frappe.conf.builder_path or "builder"
		)
		# The authoritative working tree — loaded from the DB by focus_page (in run(),
		# or mid-turn when the dashboard agent opens/creates a page).
		self.tree: WorkingTree | None = None
		# Page locks acquired via focus_page this turn ((key, token) pairs, token-fenced);
		# released in run()'s finally.
		self.held_locks: list[tuple[str, str]] = []
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
		# Every client op the tree accepted this turn (block edits, scripts, generation).
		self.applied_operations: list[dict] = []
		# Revert bookkeeping: pending_state is the focused page's pre-turn state, not yet
		# snapshotted; revert_snapshots maps each mutated page to its snapshot doc, so a
		# multi-page dashboard turn reverts EVERY page it touched (not just the last).
		self.pending_state: dict | None = None
		self.revert_snapshots: dict[str, str] = {}
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
		# Tool calls the model emitted as plain-text JSON instead of native calls
		# (see parse_text_tool_call) — salvaged, but a signal the model is weak.
		self.text_tools_salvaged = 0
		self.finish_reasons: list[str | None] = []
		# Client ops the WorkingTree rejected (bad ref, wrong parent, partial bulk miss).
		# Each is fed back to the model to self-correct; also logged and surfaced here so a
		# "why didn't my edit land" is traceable in the agent debugger, not just live logs.
		self.tool_failures: list[str] = []
		# How many streaming rounds had to be retried after a transient failure this turn.
		# Surfaced like args_repaired so a flaky provider shows up in the data, not as a
		# silent turn failure.
		self.stream_retries = 0
		# Client ops a server tool queued mid-call (run_python mutating the page).
		# Drained right after the handler returns — see drain_queued_ops.
		self.pending_client_ops: list[dict] = []
		# Tiered model selection: resolved in run() once we know the scenario.
		self.loop_model = self.model
		# Cache-breakpoint anchors, set by build_messages (see refresh_cache_markers).
		self.history_end_index = 0
		self.prompt_index = 0
		# Redis run-lock token for this session's turn (see AISession.start_run).
		self.run_token: str | None = None
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
			# Approximate USD, from the registry's per-1M prices (None-cost calls skipped).
			"cost": 0.0,
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

	def emit_page(self, suffix: str, **kwargs):
		"""Emit on the FOCUSED PAGE's channel (regardless of self.channel) so any open
		editor acts as a live viewport on a headless build — the user can click through
		from the chat and watch the page assemble. origin_page names the page whose
		chat is driving this build, so the watching editor can link back to it."""
		if not self.page_id:
			return
		frappe.publish_realtime(
			f"{EVENT_PREFIX}_{suffix}_{self.page_id}",
			{
				"page_id": self.page_id,
				"session_id": self.session_id,
				"origin_page": self.canvas_page_id,
				**kwargs,
			},
			user=self.user,
		)

	def ensure_revert_snapshot(self) -> None:
		"""Snapshot the focused page's pre-turn state the first time the turn mutates it
		— before the mutation lands, so even a cancelled multi-round edit stays
		revertable. One snapshot per focused page per turn (focus_page arms the next)."""
		if self.pending_state is None or not self.page_id:
			return
		state, self.pending_state = self.pending_state, None
		if snapshot := save_revert_snapshot(self.page_id, state):
			self.revert_snapshots[self.page_id] = snapshot

	@staticmethod
	def cached_prompt_tokens(usage) -> int:
		"""The cache-read slice of prompt tokens, across provider shapes: OpenAI/litellm
		put it under prompt_tokens_details.cached_tokens; Anthropic exposes
		cache_read_input_tokens. 0 when the provider reports neither."""
		details = getattr(usage, "prompt_tokens_details", None)
		if details and (cached := getattr(details, "cached_tokens", None)):
			return cached
		return getattr(usage, "cache_read_input_tokens", 0) or 0

	def record_usage(self, chunk, model: str | None = None) -> None:
		"""Add a streamed chunk's usage to the per-turn tally. Only the final chunk of
		a stream (stream_options.include_usage) carries usage; the rest are None.
		`model` is the model that produced this stream (the generation stream runs on
		self.model; loop rounds on self.loop_model) — it prices the call."""
		usage = getattr(chunk, "usage", None)
		if not usage:
			return
		prompt = getattr(usage, "prompt_tokens", 0) or 0
		completion = getattr(usage, "completion_tokens", 0) or 0
		total = getattr(usage, "total_tokens", 0) or 0
		cached = self.cached_prompt_tokens(usage)
		cost = ModelRegistry.estimate_cost(model or self.loop_model, prompt, completion, cached)
		self.usage["prompt_tokens"] += prompt
		self.usage["completion_tokens"] += completion
		self.usage["total_tokens"] += total
		self.usage["cached_tokens"] += cached
		self.usage["calls"] += 1
		if cost is not None:
			self.usage["cost"] = round((self.usage.get("cost") or 0) + cost, 6)
		self.usage["per_call"].append(
			{"prompt": prompt, "completion": completion, "cached": cached, "cost": cost}
		)

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

	def build_site_context(self) -> str:
		"""A compact inventory of the site's pages, so the agent starts every turn
		knowing what exists instead of spending a query_records round-trip (or
		guessing) to find out."""
		rows = frappe.get_all(
			"Builder Page",
			fields=["name", "route", "page_title", "published", "project_folder"],
			order_by="modified desc",
			limit=100,
		)
		if not rows:
			return "This site has no pages yet."
		lines = [
			f"- {r.name} | /{(r.route or '').lstrip('/')} | {r.page_title or ''}"
			f" | {'published' if r.published else 'draft'}"
			+ (f" | folder: {r.project_folder}" if r.project_folder else "")
			for r in rows
		]
		return "Pages on this site (id | route | title | status):\n" + "\n".join(lines)

	def build_memory_context(self) -> str:
		"""Facts the agent saved in past conversations (see tools/memory.py) — part of
		the cached context block, so remembering costs nothing per-round."""
		from builder.ai.agent.tools.memory import memory_context

		return memory_context()

	def build_messages(self) -> list[dict]:
		messages: list[dict] = [{"role": "system", "content": self.system_prompt}]

		# Prior conversation FIRST, as proper role-tagged turns: old turns replay
		# byte-stable from the session rows, so system + history stays a provider-
		# cache prefix hit ACROSS turns. The page context goes after — it changes
		# every turn and would otherwise invalidate everything behind it.
		messages.extend(AISession.build_context_messages_from_id(self.session_id))
		self.history_end_index = len(messages) - 1

		# The page structure plus the site inventory (page-less turns get just the
		# inventory). It's resent on every round of a multi-round turn, so a cache
		# marker on the prompt right after it cuts both latency and input cost
		# across the loop. The inventory is what lets the agent act on OTHER pages
		# (read_page/open_page/manage_pages) without spending a discovery round-trip.
		page_context = self.build_page_context()
		site_context = self.build_site_context()
		context = "\n\n".join(filter(None, [page_context, site_context, self.build_memory_context()]))
		if context:
			messages.append({"role": "user", "content": context})
			messages.append({"role": "assistant", "content": "Understood. I have the current context."})

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
		self.prompt_index = len(messages) - 1
		return messages

	def refresh_cache_markers(self, messages: list[dict]) -> None:
		"""Re-derive the prompt-cache breakpoints before every LLM round (Claude
		routes only benefit; llm.py strips the markers for other providers).
		Deterministic positions: the system prompt (1h TTL), the end of the replayed
		history (the prefix next turn's first request re-matches), the current user
		prompt (the stable turn-start prefix), the newest message (caches this
		round's prefix for the next), and a mid-turn anchor every
		MID_TURN_MARKER_EVERY messages so a long turn's rounds stay inside
		Anthropic's cache-lookback window. Capped at 4 markers, oldest dropped
		first — their cache entries were already written by earlier rounds."""
		for m in messages:
			m.pop("cache_control", None)
			if isinstance(m.get("content"), list):
				for block in m["content"]:
					if isinstance(block, dict):
						block.pop("cache_control", None)
		last = len(messages) - 1
		positions = {0, max(self.history_end_index, 0), self.prompt_index, last}
		span = last - self.prompt_index
		if span > MID_TURN_MARKER_EVERY + 3:
			anchor = self.prompt_index + MID_TURN_MARKER_EVERY * (span // MID_TURN_MARKER_EVERY)
			positions.add(min(anchor, last))
		for pos in sorted(positions)[-MAX_CACHE_MARKERS:]:
			messages[pos]["cache_control"] = SYSTEM_CACHE_CONTROL if pos == 0 else TURN_CACHE_CONTROL

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
		if not tool_operations and (salvaged := parse_text_tool_call(content, self.registry.names())):
			name, args, prose = salvaged
			self.text_tools_salvaged += 1
			logger.warning(
				"AI tool call emitted as TEXT, salvaged (tool=%s): %s",
				name,
				BlockCodec.truncate_for_log(content, 300),
			)
			tool_operations.append({"tool_name": name, "args": args})
			raw_tool_calls.append(
				{
					"id": f"call_text_salvage_{len(self.trace)}",
					"type": "function",
					"function": {"name": name, "arguments": json.dumps(args)},
				}
			)
			content = prose
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

	def queue_client_op(self, op: dict) -> None:
		"""Called by a server tool mid-handler to emit a client op (run_python queues
		the mutated page tree here). Drained by the loop right after the handler."""
		self.pending_client_ops.append(op)

	def drain_queued_ops(self) -> list[dict]:
		"""Snapshot, sync the working tree, persist, and emit ops a server tool queued
		mid-handler (run_python queues the mutated page as set_page_blocks), so the
		canvas updates live and a later run_python sees the tree it already mutated."""
		from builder.ai import page_writer

		ops, self.pending_client_ops = self.pending_client_ops, []
		if not ops:
			return []
		if any(op["tool_name"] in SNAPSHOT_TOOLS for op in ops):
			self.ensure_revert_snapshot()
		for op in ops:
			if op["tool_name"] == "set_page_blocks":
				# run_python lets the model hand-build component instances; repair
				# childless ones or they render as nothing (editor + published alike).
				op["args"]["blocks"] = page_writer.normalize_component_instances(op["args"]["blocks"])
				self.tree.root = op["args"]["blocks"]
		self.applied_operations.extend(ops)
		self.emit("tool_batch", operations=ops)
		if self.channel != self.page_id:
			self.emit_page("tool_batch", operations=ops)
		if self.page_id and self.tree and self.tree.root:
			page_writer.save_draft_blocks(self.page_id, self.tree.root)
		return ops

	def page_root(self) -> dict | None:
		"""The current page's root block — the authoritative working tree. Edits made
		this turn are visible to context rebuilds and the query tools, and refs stay
		valid across rounds."""
		return self.tree.root if self.tree else None

	def focus_page(self, page_id: str, *, lock: bool = True) -> str:
		"""Point the turn at a page: load its blocks from the DB into the working tree
		(context, query tools, and block edits all read/write it), and capture the
		pre-edit state so the turn stays revertable. With lock=True the page lock is
		held for the rest of the turn so parallel AI tasks can't fight over one page
		(sub-agents pass lock=False — their task runner already holds it).
		Returns the rendered page context — the tool result for open_page/create_page."""
		from builder.ai import page_writer

		key = locks.page_key(page_id)
		if lock and key not in (k for k, _ in self.held_locks):
			token = locks.acquire(key, locks.PAGE_LOCK_TTL)
			if token is None:
				return (
					f"FAILED: page {page_id} is being edited by another AI task right now — "
					"try again in a moment."
				)
			self.held_locks.append((key, token))
		root = page_writer.load_page_root(page_id)
		# A focus move away from the page the user is looking at must be VISIBLE —
		# ops there won't show on their canvas, and a silent switch reads as the
		# agent lying about what it built.
		if self.page_id and page_id != self.page_id:
			title = frappe.db.get_value("Builder Page", page_id, "page_title") or page_id
			self.emit("progress", message=f"Now editing another page: '{title}'")
		# Let the origin editor's pill survive navigation/reload: record that this
		# chat's run is working on an off-canvas page (cleared when the run ends).
		if not self.headless and self.canvas_page_id and page_id != self.canvas_page_id:
			frappe.cache().set_value(
				f"builder_ai_offpage_build:{self.canvas_page_id}",
				{"target": page_id, "session_id": self.session_id},
				expires_in_sec=locks.PAGE_LOCK_TTL,
			)
		self.page_id = page_id
		self.tree = WorkingTree(root)
		# Arm the revert snapshot — unless this page was already snapshotted this turn
		# (a refocus must keep its original pre-turn state).
		self.pending_state = None if page_id in self.revert_snapshots else capture_page_state(page_id)
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
		if counts.get("set_page_blocks"):
			parts.append("updated the page")
		if counts.get("set_page_script"):
			parts.append("added a script")
		if counts.get("update_script"):
			parts.append("updated a script")

		if not parts:
			n = len(operations)
			return f"Applied {n} change{'s' if n != 1 else ''} to the page."
		sentence = parts[0] if len(parts) == 1 else f"{', '.join(parts[:-1])} and {parts[-1]}"
		return sentence[0].upper() + sentence[1:] + "."

	# --- round execution ----------------------------------------------------

	def op_kind(self, op: dict) -> str:
		"""How the loop must handle one tool call: "artifact" (streamed generation),
		"terminal" (ends the turn), "server" (run the handler now), or "client"
		(apply to the working tree + mirror to the canvas). A client tool with a
		server twin (page scripts) runs as a server op when there is no canvas to
		apply it — headless, or the agent focused a page the canvas isn't showing."""
		tool = self.registry.get(op["tool_name"])
		if tool and tool.artifact:
			return "artifact"
		side = tool.side if tool else "client"
		off_canvas = self.headless or self.page_id != self.canvas_page_id
		if side == "client" and tool and tool.handler:
			if off_canvas or op["tool_name"] in SCRIPT_TWIN_TOOLS:
				return "server"
		return side

	def apply_client_ops(self, ops: list[dict]) -> tuple[dict[int, str], list[dict]]:
		"""Apply this round's client ops to the working tree — the source of truth —
		then mirror the ACCEPTED ones to the canvas and persist the draft. Rejected
		ops are never emitted, so the canvas can't apply an edit the server refused.
		Returns (tool-result per op, accepted ops)."""
		results: dict[int, str] = {}
		applied: list[dict] = []
		for op in ops:
			if op["tool_name"] in SNAPSHOT_TOOLS:
				self.ensure_revert_snapshot()
			content = self.tree.apply(op["tool_name"], op["args"])
			results[id(op)] = content
			# "FAILED" (hard miss) or "NOT FOUND" (partial bulk miss) — a correction
			# the model is now being asked to make. Record + log so it's not invisible.
			if "FAILED" in content or "NOT FOUND" in content:
				self.tool_failures.append(f"{op['tool_name']}: {content}")
				logger.warning("Client op rejected — %s: %s", op["tool_name"], content)
			if not content.startswith("FAILED"):
				applied.append(op)
		if applied:
			self.applied_operations.extend(applied)
			self.emit("tool_batch", operations=applied)
			# When the focused page isn't the channel's page (headless session chat, or
			# an editor agent that opened another page), mirror accepted ops to the
			# focused page's channel too, so an editor open on it updates live.
			if self.channel != self.page_id:
				self.emit_page("tool_batch", operations=applied)
			if self.page_id and self.tree.root:
				from builder.ai import page_writer

				# Persist after every applied round so a cancel/crash keeps the work
				# done so far (the same live-apply semantics the canvas shows).
				page_writer.save_draft_blocks(self.page_id, self.tree.root)
		return results, applied

	def run_op(self, op: dict, client_results: dict[int, str]) -> str | None:
		"""Produce one tool call's result string. Client ops were already applied by
		apply_client_ops; server ops run their handler here. Returns None when a
		terminal tool ended the turn (its handler emitted the card and persisted it)."""
		kind = self.op_kind(op)
		if kind == "client":
			return client_results[id(op)]
		tool = self.registry.get(op["tool_name"])
		if kind == "terminal":
			# A terminal handler may DECLINE by returning a string (e.g. "that DocType
			# already exists") — the reason goes back as a tool result and the loop
			# continues. None = the card was emitted and the turn is over.
			return self.handle_terminal(op)
		if kind == "artifact":
			# Generation is a STEP of the turn in both modes: the generator streams
			# YAML live (canvas preview in the editor), persists the page, and the
			# loop continues — so the model can add scripts, verify, and refine in
			# the same turn.
			content, ops = self.run_generation_step(tool, op)
			self.applied_operations.extend(ops)
			if ops:
				# The authoritative op replaces the throwaway streamed preview with
				# the server's block tree (shared ids).
				self.emit("tool_batch", operations=ops)
				if self.channel != self.page_id:
					# Mirror to any editor watching the focused page (headless build,
					# or an editor agent that opened another page); the complete
					# resets that watcher's "working" state.
					self.emit_page("tool_batch", operations=ops)
					self.emit_page("complete", message="Page generated — the agent may keep refining it.")
			return content
		entry = self.begin_activity(op["tool_name"], op["args"])
		if op["tool_name"] in SNAPSHOT_TOOLS:
			self.ensure_revert_snapshot()
		content = tool.handler(self, op["args"])
		self.end_activity(entry)
		self.drain_queued_ops()
		if op["tool_name"] not in READ_ONLY_SERVER_TOOLS and not str(content).startswith("FAILED"):
			self.server_mutations += 1
			if op["tool_name"] in SCRIPT_TWIN_TOOLS and not self.headless:
				# Mirror the server-applied script op so the open editor updates its
				# script list / undo tracking — flagged so the canvas does NO DB work.
				op["args"]["server_applied"] = True
				self.applied_operations.append(op)
				self.emit("tool_batch", operations=[op])
				if self.channel != self.page_id:
					self.emit_page("tool_batch", operations=[op])
		return content

	def emit_round_note(self, text: str, applied: list[dict]) -> None:
		"""Live narration: surface what the model said / did this round, so a long
		multi-round turn shows real progress instead of a frozen "Applying…"."""
		note = (text or "").strip()
		if looks_like_tool_syntax(note):
			note = ""
		if not note and applied:
			note = self.describe_operations(applied)
		if note:
			self.emit("progress", message=note)

	def correction_for(self, summary_text: str) -> str | None:
		"""A no-tool round that should have been a tool call gets EXACTLY ONE
		corrective round. Three shapes: card markup written as plain text (mimicking
		the persisted replay format — renders no controls), a multi-option question
		asked as prose bullets (same dead end, no markup to match), and a summary
		that CLAIMS an edit when nothing was applied this turn (hallucinated
		success)."""
		if self.noop_corrected:
			return None
		correction = None
		if looks_like_card_text(summary_text) or looks_like_json_card(summary_text):
			correction = CARD_CORRECTION
		elif asks_options_as_text(summary_text):
			correction = OPTIONS_AS_TEXT_CORRECTION
		elif (
			not self.applied_operations and not self.server_mutations and claims_unbacked_action(summary_text)
		):
			correction = NOOP_CORRECTION
		if correction is None:
			return None
		self.noop_corrected = True
		self.stop_reason = "noop_retry"
		kind = {
			id(CARD_CORRECTION): "card-as-text",
			id(OPTIONS_AS_TEXT_CORRECTION): "options-as-text",
			id(NOOP_CORRECTION): "no-op claim",
		}[id(correction)]
		logger.warning(
			"No-tool round corrected (%s): %s",
			kind,
			BlockCodec.truncate_for_log(summary_text, 300),
		)
		return correction

	def flush_pending_images(self, messages: list[dict]) -> None:
		"""Images a tool captured this round (preview_page screenshots) ride a
		follow-up user message — appended only after every role:"tool" result,
		as the OpenAI message shape requires."""
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

	# --- orchestration ----------------------------------------------------

	def emit_cancelled(self) -> None:
		msg = "Cancelled."
		AISession.try_append_message(
			self.session_id, "assistant", msg, message_type="status", metadata={"status": "cancelled"}
		)
		frappe.db.commit()
		self.emit("complete", message=msg)

	def fail_turn(self, message: str) -> None:
		"""End the turn with a persisted error message + error event."""
		AISession.try_append_message(
			self.session_id, "assistant", message, message_type="status", metadata={"status": "error"}
		)
		frappe.db.commit()  # commit before emit so the client's reload sees it
		self.emit("error", message=message)

	def run(self):
		# Clear any stale cancel flag from a previous turn before starting.
		self.clear_cancel_flag()
		started = time.monotonic()
		logger.info(
			f"AgentRunner.run: page_id={self.page_id}, model={self.model}, "
			f"session_id={self.session_id}, user={self.user}"
		)

		# One turn per session at a time — an atomic Redis lock with a TTL, so a
		# crashed worker can never brick the session (the old is_running DB flag did).
		if self.session_id:
			self.run_token = AISession.start_run(self.session_id)
			if self.run_token is None:
				logger.warning(f"AgentRunner.run: session {self.session_id} already running, rejecting")
				self.emit(
					"error", message="Another AI request is still processing. Please wait for it to finish."
				)
				return

		try:
			self.run_turn(started)
		finally:
			self.clear_cancel_flag()
			if self.canvas_page_id:
				frappe.cache().delete_value(f"builder_ai_offpage_build:{self.canvas_page_id}")
			for key, token in self.held_locks:
				locks.release(key, token)
			self.held_locks = []
			if self.session_id:
				AISession.end_run(self.session_id, self.run_token)

	def run_turn(self, started: float):
		# Load the page into the authoritative working tree. Editor turns take the
		# page lock (a dashboard task could otherwise edit the same page mid-turn);
		# sub-agents arrive with the lock already held by their task runner.
		if self.page_id and self.tree is None:
			focused = self.focus_page(self.page_id, lock=not self.headless)
			if focused.startswith("FAILED"):
				self.fail_turn(focused)
				return
		if self.tree is None:
			self.tree = WorkingTree(None)

		# Editing an existing page runs the loop on the user's CHOSEN model — edit
		# taste matters as much as generation taste, and silently downgrading a
		# deliberately-picked heavy model is the surest way to degrade output.
		# Headless turns (dashboard orchestrator + sub-agents) always use the chosen
		# model too. Only the editor's lightweight empty-page conversation
		# (clarify/plan) drops to the cheap model.
		has_content = self.page_root() is not None
		self.loop_model = (
			self.model if (has_content or self.headless) else ModelRegistry.get_simple(self.model)
		)
		label = ModelRegistry.get_label(self.loop_model)
		self.emit("progress", message=f"Thinking with {label}" if label else "Thinking…")

		messages = self.build_messages()
		summary_text = ""

		try:
			for round_index in range(MAX_ROUNDS):
				self.refresh_cache_markers(messages)
				tool_operations, summary_text, raw_tool_calls = self.call_tool_llm(messages)
				self.record_round(round_index, tool_operations, summary_text)

				if not tool_operations:
					if correction := self.correction_for(summary_text):
						messages.append({"role": "assistant", "content": summary_text})
						messages.append({"role": "user", "content": correction})
						continue
					self.stop_reason = "model_finished"
					break

				# Apply block/script ops FIRST — the canvas updates live, and a terminal
				# tool in the same round can no longer silently discard them.
				client_ops = [op for op in tool_operations if self.op_kind(op) == "client"]
				client_results, applied = self.apply_client_ops(client_ops)

				has_terminal = any(self.op_kind(op) == "terminal" for op in tool_operations)
				if not has_terminal:
					self.emit_round_note(summary_text, applied)

				messages.append(
					{"role": "assistant", "content": summary_text or None, "tool_calls": raw_tool_calls}
				)
				turn_over = False
				for tc, op in zip(raw_tool_calls, tool_operations, strict=True):
					content = self.run_op(op, client_results)
					if content is None:
						turn_over = True  # terminal card emitted + persisted
						break
					messages.append({"role": "tool", "tool_call_id": tc["id"], "content": content})
				if turn_over:
					return
				self.flush_pending_images(messages)
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
			self.fail_turn("Something went wrong while building your changes. Please try again.")
			return

		self.finish_turn(summary_text, started)

	def finish_turn(self, summary_text: str, started: float):
		"""Wrap up a completed loop: recover stray output, guard hallucinated
		summaries, pick/emit the final summary, and persist the turn."""
		# Defensive: a weaker model may emit page YAML as content instead of calling
		# generate_page. Persist it server-side and apply it as a generation op.
		if not self.applied_operations and self.page_id and looks_like_page_yaml(summary_text):
			logger.info("Recovering YAML-as-content into a synthetic generate_page op")
			from builder.ai import page_writer

			self.ensure_revert_snapshot()
			root, data_script = page_writer.persist_page(self.page_id, BlockCodec.strip_fences(summary_text))
			if root:
				op = {"tool_name": "generate_page", "args": {"blocks": [root], "data_script": data_script}}
				self.applied_operations.append(op)
				self.emit("tool_batch", operations=[op])
			summary_text = ""

		# Leaked tool-call syntax (or a JSON card that survived its corrective round)
		# is never a summary — suppress it. With applied work the deterministic
		# fallbacks below take over; with none, say what happened.
		if looks_like_tool_syntax(summary_text) or looks_like_json_card(summary_text):
			logger.warning(
				"Suppressed tool-syntax leak in summary: %s", BlockCodec.truncate_for_log(summary_text, 300)
			)
			summary_text = (
				""
				if self.applied_operations
				else "My last step came out garbled and was not applied — ask me to try that again."
			)

		if not self.applied_operations and not summary_text:
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
		if not self.applied_operations and not self.server_mutations and claims_unbacked_action(summary_text):
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
		generated = any(op["tool_name"] == "generate_page" for op in self.applied_operations)
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
			summary_text = self.describe_operations(self.applied_operations)
			self.emit("stream", chunk=summary_text)

		# The turn built/edited a DIFFERENT page than the one on the user's canvas:
		# the editor link is their only path to the result, and models (especially
		# cheap ones) skip the prompt rule — append it deterministically.
		if (
			not self.headless
			and self.applied_operations
			and self.page_id
			and self.canvas_page_id
			and self.page_id != self.canvas_page_id
			and f"/page/{self.page_id}" not in summary_text
		):
			title = frappe.db.get_value("Builder Page", self.page_id, "page_title") or self.page_id
			builder_path = frappe.conf.builder_path or "builder"
			link_note = f"\n\nOpen the page: [{title}](/{builder_path}/page/{self.page_id})"
			summary_text += link_note
			self.emit("stream", chunk=link_note)

		# Hit the per-turn round cap → the work is INCOMPLETE. Say so, so a big edit
		# doesn't look finished; the user can reply "continue" to resume from here.
		if self.stop_reason == "max_rounds":
			hint = '\n\n⚠️ I hit my edit-step limit for one turn before finishing — reply "continue" and I\'ll pick up where I left off.'
			summary_text += hint
			self.emit("stream", chunk=hint)

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
			"operations": len(self.applied_operations),
			# Trace for the agent debugger: why the turn ended + what the model did each
			# round. Explains cases like "only 2 blocks updated" at a glance.
			"debug": {
				"stopReason": self.stop_reason or "model_finished",
				"loopModel": self.loop_model,
				"rounds": len(self.trace),
				"noopCorrected": self.noop_corrected,
				"argsRepaired": self.args_repaired,
				"textToolsSalvaged": self.text_tools_salvaged,
				"finishReasons": self.finish_reasons,
				"toolFailures": self.tool_failures,
				"streamRetries": self.stream_retries,
				# Per-turn cost signal for the selector/tiered-context experiment.
				"tokens": self.usage,
				# How much room the conversation has: the loop model's window; the
				# latest call's prompt_tokens (per_call) is the current context size.
				"contextWindow": ModelRegistry.context_window(self.loop_model),
				"elapsedMs": elapsed_ms,
				"trace": self.trace,
			},
		}
		# Revert handles: one snapshot per page the turn mutated. revertSnapshot (the
		# most recent) keeps the existing frontend contract; revertSnapshots carries
		# the full set so a multi-page dashboard turn reverts every page it touched.
		if self.revert_snapshots:
			final_metadata["revertSnapshot"] = next(reversed(self.revert_snapshots.values()))
			if len(self.revert_snapshots) > 1:
				final_metadata["revertSnapshots"] = self.revert_snapshots
		if self.activity:
			# The chat's activity feed (tool lines + screenshots) — rendered live from
			# tool_activity events, rehydrated from here on a session reload.
			final_metadata["activity"] = self.activity
		AISession.try_append_message(
			self.session_id,
			"assistant",
			summary_text or f"Applying {len(self.applied_operations)} change(s).",
			message_type="chat",
			task_type="agent",
			metadata=final_metadata,
		)
		self.maybe_name_session()
		frappe.db.commit()  # commit before emit so the client's reload sees the final turn
		self.emit("complete", message=summary_text or "Done")

	def maybe_name_session(self) -> None:
		"""The first completed turn names the chat: a short generated title reads
		better in the session switcher than the raw first prompt ("Collection page
		for The Pieces" vs "Create a collection page and link it here")."""
		if not self.session_id or frappe.db.get_value(AISession.DOCTYPE, self.session_id, "title"):
			return
		first = frappe.db.get_value(
			AISession.MESSAGE_DOCTYPE,
			{"session": self.session_id, "role": "user"},
			"content",
			order_by="creation asc",
		)
		if not first:
			return
		try:
			title = llm.complete(
				ModelRegistry.get_simple(self.model),
				[
					{
						"role": "user",
						"content": (
							"Name this website-builder chat in 2-5 words — what it's about, not what was "
							"asked. Title case, no quotes, no trailing punctuation. Reply with the title "
							f"only.\nFirst message: {first[:400]}"
						),
					}
				],
				{"max_tokens": 24, "temperature": 0.3},
				stream=False,
				api_key=self.api_key,
			)
			title = (title or "").strip().strip("\"'.").strip()
			if 0 < len(title) <= 60 and "\n" not in title:
				frappe.db.set_value(AISession.DOCTYPE, self.session_id, "title", title, update_modified=False)
		except Exception as e:
			logger.warning("session title generation skipped: %s", e)

	def handle_terminal(self, op: dict) -> str | None:
		"""Run a terminal tool's handler (which emits the appropriate event and
		persists the message). Returns the handler's return value: None = the turn
		is over (question/plan/confirm card emitted); a string = the handler DECLINED
		(invalid proposal) and the loop should continue with that as the tool result."""
		tool = self.registry.get(op["tool_name"])
		if tool and tool.handler:
			return tool.handler(self, op["args"])
		return None

	def run_generation_step(self, tool, op: dict) -> tuple[str, list[dict]]:
		"""Run generate_page as one STEP of the turn (editor and headless alike). The
		generator persists the page server-side; point the working tree at the result
		so the model can read back — and build on — what it just made (scripts,
		surgical fixes, one verify pass)."""
		if not self.page_id:
			return ("FAILED: no page is open — call create_page or open_page first, then generate.", [])
		entry = self.begin_activity(op["tool_name"], op["args"])
		self.ensure_revert_snapshot()  # generation replaces the block tree
		ops = tool.generator(self, op["args"])
		self.end_activity(entry)
		if not ops:
			return ("FAILED: generation produced nothing. Retry generate_page with a fuller brief.", [])
		root = ops[0]["args"]["blocks"][0]
		self.tree = WorkingTree(root)
		return (
			"Page generated and saved. Now finish the build: add the client scripts the plan "
			"calls for (set_page_script), fix obvious breakage with the block tools, verify "
			"with preview_page at most once, then finish with a short summary."
			f"{self.script_hook_gap_note(root)}\n"
			f"{render_page_context(root)}",
			ops,
		)

	def script_hook_gap_note(self, root: dict) -> str:
		"""The class-contract check: scripts written in parallel with generation
		target class hooks the generated blocks must carry — a missing hook silently
		kills the behaviour (seen live: scripts selecting .suraj-project-card on a
		page whose blocks only carried .suraj-reveal). Compare the attached scripts'
		querySelector targets and CSS class selectors against the blocks' classes
		and tell the model NOW, while it can still patch with update_blocks."""
		if not self.page_id:
			return ""
		names = frappe.db.get_all(
			"Builder Page Client Script",
			filters={"parent": self.page_id, "parenttype": "Builder Page"},
			pluck="builder_script",
		)
		if not names:
			return ""
		scripts = frappe.get_all(
			"Builder Client Script", filters={"name": ["in", names]}, fields=["script_type", "script"]
		)
		selected, runtime_added, css_used = set(), set(), set()
		for s in scripts:
			text = s.script or ""
			if s.script_type == "CSS":
				css_used.update(re.findall(r"\.([a-zA-Z][\w-]{2,})", text))
			else:
				selected.update(re.findall(r"""querySelector(?:All)?\(\s*['"]\.([\w-]+)""", text))
				# Classes the JS creates/toggles at runtime are not expected on blocks.
				runtime_added.update(
					re.findall(r"""classList\.(?:add|remove|toggle)\(\s*['"]([\w-]+)""", text)
				)
				runtime_added.update(re.findall(r"""\.className\s*=\s*['"]([\w\s-]+)['"]""", text))
		blob = json.dumps(root)
		present = set(re.findall(r'"([^"]+)"', " ".join(re.findall(r'"classes":\s*\[([^\]]*)\]', blob))))
		missing_js = sorted(selected - present - runtime_added)
		missing_css = sorted(css_used - present - runtime_added - selected)[:8]
		if not missing_js and not missing_css:
			return ""
		parts = ["\nCLASS CONTRACT CHECK:"]
		if missing_js:
			parts.append(
				f"your JS selects {', '.join('.' + c for c in missing_js)} but NO block carries "
				"those classes — that behaviour will never fire. Add each class to the intended "
				"blocks (update_blocks) or rewrite the script."
			)
		if missing_css:
			parts.append(
				f"CSS rules target unused classes: {', '.join('.' + c for c in missing_css)} — "
				"apply them to the intended blocks or they are dead styling."
			)
		return " ".join(parts)


def run_agent_job(prompt: str, model: str, api_key: str, **kwargs):
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
	AgentRunner(prompt, model, api_key, **kwargs).run()
