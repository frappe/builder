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
    ai_chat_stream         {chunk, kind?, replace?}  kind="page_blocks" {blocks} → live
                                            canvas preview frame of a page still being
                                            generated; kind="reasoning" → append to the
                                            open thinking step; absent → append to the
                                            live answer text. replace=True means this
                                            chunk REPLACES the live answer (a guard
                                            rewrote it, or a retry is re-sending).
    ai_chat_tool_batch     {operations: [{tool_name, args}]}
                           (generate_page args carry the expanded {blocks, data_script};
                           add_block args carry block_json; the canvas applies those
                           verbatim so both sides share block ids)
    ai_chat_step           {id, kind: "thinking"|"tool"|"text", status: "running"|"done",
                            summary?, text?, ms?, tool?}
                           One entry of the turn's timeline; the same id is emitted
                           twice (running then done), so upsert by id. A "text" step
                           commits the narration the client has been streaming live
                           and tells it to clear the live buffer for the next round.
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

from builder.ai import llm, locks, markup
from builder.ai.agent.edits import EditScript, composition_notes
from builder.ai.agent.registry import ToolRegistry, build_default_registry
from builder.ai.agent.selectors import walk_blocks
from builder.ai.agent.tree import WorkingTree
from builder.ai.block_codec import BlockCodec
from builder.ai.models import ModelRegistry
from builder.ai.prompts import Prompts
from builder.ai.session import AISession
from builder.ai.skills import Skills
from builder.ai.snapshots import capture_page_state, save_revert_snapshot

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
		"edit_page",
		"set_page_blocks",
		"generate_page",
		"set_page_script",
		"update_script",
		"attach_page_script",
		"detach_page_script",
		"write_page_data_script",
	}
)

# Script tools ALWAYS apply through their server handlers, editor sessions included.
# Applying them in the browser (frappe.client.insert from toolDispatch) lost scripts
# silently — two parallel attaches in one round raced and .catch(() => null) ate the
# failure; a page then published with its reveal CSS but not the JS that fires it.
# The server apply is atomic and verified; the canvas just mirrors the result.
SCRIPT_TWIN_TOOLS = frozenset(
	{"set_page_script", "attach_page_script", "update_script", "detach_page_script"}
)


# name, = or :, an opening quote (JSON-escaped in dumped args), then the value
SECRET_RE = re.compile(
	r"""(?i)\b(api[_-]?key|api[_-]?secret|client[_-]?secret|secret|password|passwd|"""
	r"""access[_-]?token|auth[_-]?token|authorization)(\\?["']?\s*[:=]\s*\\?["'])([^"'\\]{4,})"""
)


def redact_secrets(text: str) -> str:
	return SECRET_RE.sub(lambda m: f"{m.group(1)}{m.group(2)}[redacted]", text)


class CancelledError(Exception):
	"""Raised inside the stream loops when the user cancels the turn."""


# Skeletonising a page the model just wrote costs whole rounds re-reading its own
# work, so the threshold has to clear a real generated page: a full read is once
# per turn, behind a cache marker, and an outline is what a runaway page falls back to.
FULL_CONTEXT_LIMIT = 45_000

# Tools that already surface as their own card in the chat (clarify question, plan,
# task group) — no activity line for them.
ACTIVITY_SILENT = frozenset({"present_ui"})

# Server tools that only READ. Everything else that runs server-side (settings, theme,
# data scripts, page creation, generation…) mutates real state — the no-op-claim guards
# must count that as backing for an action claim, or a purely-server-tool turn (the
# dashboard's normal mode) gets its truthful summary replaced with "I didn't apply it".
READ_ONLY_SERVER_TOOLS = frozenset(
	{
		"read_page",
		"run_python",
		"read_url",
		"research",
		"get_document",
		"query_records",
		"list_doctypes",
		"get_doctype_schema",
		"get_page_scripts",
		"preview_page",
		"read_plugin",
		"read_editor_source",
		"read_skill",
	}
)

# --- prompt-cache breakpoints (Claude via OpenRouter; stripped elsewhere) ------
# Ported from the agent-v2 rewrite, where this scheme measured ~90% cache reads
# on real multi-round builds (~80% input-cost cut). The system and end-of-history
# breakpoints hold the cross-turn prefix (prompt + tools + conversation); user
# turns are minutes apart, so the default 5-minute TTL would expire on exactly
# the entries the next turn re-matches — 1h costs 2x to write but breaks even by
# the third turn of a session.
SYSTEM_CACHE_CONTROL = {"type": "ephemeral", "ttl": "1h"}
TURN_CACHE_CONTROL = {"type": "ephemeral"}
# Anthropic allows at most 4 cache_control markers per request.
MAX_CACHE_MARKERS = 4
# Anthropic matches an existing cache entry only within ~20 content blocks
# behind a marker; long turns get a mid-turn anchor every this many messages so
# consecutive rounds always land inside the lookback window.
MID_TURN_MARKER_EVERY = 15


def marker_position(messages: list[dict], pos: int) -> int:
	"""The nearest position at or before `pos` whose message HAS content. A marker
	on a content-less assistant tool_calls message would materialize as an empty
	text block on the Claude path (see llm.patch_messages_for_provider), which
	Anthropic's API rejects."""
	while pos > 0 and not messages[pos].get("content"):
		pos -= 1
	return pos


PAGE_PREAMBLE = "The open page in markup (@ref is each block's handle for edit_page):"

OUTLINE_PREAMBLE = (
	"This page is large, so it is shown as an OUTLINE: every block with its @ref, tag, "
	"classes and full text, styles omitted. read_page(ref=@x) shows a block's styles."
)


def render_page_context(
	root: dict | None, selected_block_ids: tuple | list = (), sets: dict | None = None
) -> str:
	"""A page's block tree as model-readable markup: the whole page with its style
	sets ($s1…, collected into `sets` so edits can reuse them), or past
	FULL_CONTEXT_LIMIT an outline plus the selected blocks in full."""
	if root is None:
		return ""
	refs = markup.short_refs(root)
	found: dict = {}
	full = markup.dump_block(root, refs=refs, sets=found)
	if len(full) <= FULL_CONTEXT_LIMIT:
		if sets is not None:
			sets.update(found)
		context = f"{PAGE_PREAMBLE}\n{full}"
	else:
		outline = markup.dump_block(root, refs=refs, styles=False)
		selected = render_selected_context(root, selected_block_ids, include_components=False)
		context = "\n\n".join(part for part in (OUTLINE_PREAMBLE, outline, selected) if part)
	# THIS page's component contracts: without them an instance advertises nothing
	# (declared props were unreachable from the open page).
	from builder.ai.agent.tools.query import render_components

	if contract := render_components(root, on_open_page=True):
		return f"{context}\n\n{contract}"
	return context


def render_selected_context(
	root: dict | None, selected_block_ids: tuple | list, *, include_components: bool = True
) -> str:
	from builder.ai.agent.selectors import find_block
	from builder.ai.agent.tools.query import render_components

	refs = markup.short_refs(root) if root else {}
	parts = []
	for ref in selected_block_ids:
		block = find_block(root, ref) if root else None
		if block is None:
			continue
		detail = markup.dump_block(block, refs=refs, set_prefix=None)
		parts.append(f"Selected block @{refs.get(ref, ref)}:\n{detail}")
		if include_components and (contract := render_components(block, on_open_page=True)):
			parts.append(contract)
	return "\n\n".join(parts)


# The DocTypes the agent reads to understand the site it's working in. These are
# Frappe's internal names — "Read Builder Token" means nothing to someone who just
# asked for a ramen page, so say what was actually looked at. A DocType that isn't
# here belongs to the user's own data, where the name IS the friendly word (Event,
# Product), so it passes through.
BUILDER_DOCTYPE_LABELS = {
	"Builder Token": "the design tokens",
	"Builder Component": "the components",
	"Builder Page": "the pages",
	"Builder Client Script": "the page scripts",
	"Builder Settings": "the site settings",
	"Builder Variable": "the variables",
}

# Plain-English name for each tool, for tools whose line needs no arguments. The
# derived fallback (tool_name.replace("_", " ")) leaks the vocabulary of the tool
# API — "Get doctype schema", "Seed sample data" — which is ours, not the user's.
# (while running, once done) — finish_step re-emits the step with the done voice.
TOOL_LABELS = {
	"generate_page": ("Building the page", "Built the page"),
	"preview_page": ("Checking how it looks", "Checked how it looks"),
	"search_images": ("Searching for photos", "Searched for photos"),
	"extract_component": ("Making a reusable component", "Made a reusable component"),
	"edit_component": ("Updating a shared component", "Updated a shared component"),
	"write_page_data_script": ("Connecting the page to data", "Connected the page to data"),
	"list_doctypes": ("Looking for existing data", "Looked for existing data"),
	"run_python": ("Looking up site data", "Looked up site data"),
	"read_url": ("Reading a web page", "Read a web page"),
	"research": ("Researching online", "Researched online"),
	"get_page_scripts": ("Reading the page scripts", "Read the page scripts"),
	"attach_page_script": ("Attaching a shared script", "Attached a shared script"),
	"set_page_settings": ("Updating page settings", "Updated page settings"),
	"remember": ("Saving a note for next time", "Saved a note for next time"),
	"seed_sample_data": ("Adding sample records", "Added sample records"),
	"create_doctype": ("Creating a place to store data", "Created a place to store data"),
	"connect_form": ("Connecting the form", "Connected the form"),
	"edit_global_settings": ("Updating site settings", "Updated site settings"),
	"set_home_page": ("Setting the home page", "Set the home page"),
	"read_plugin": ("Reading the editor plugins", "Read the editor plugins"),
	"read_editor_source": ("Reading the editor's code", "Read the editor's code"),
}


def block_label(block: dict) -> str:
	return block.get("blockName") or f"<{block.get('element') or 'div'}>"


def readable_doctype(doctype: str | None) -> str:
	if not doctype:
		return "records"
	return BUILDER_DOCTYPE_LABELS.get(doctype) or f"{doctype} records"


def activity_summary(tool_name: str, args: dict, tree=None, done: bool = True) -> str:
	"""A short human line for the chat's timeline ("Read block: Hero"). Written for
	someone who asked for a web page, not someone who knows the tool API. The voice
	follows the step's status: running or done."""
	args = args or {}

	def resolved_label(ref: str | None) -> str:
		block = tree.resolve(ref) if (tree and ref) else None
		return block_label(block) if block else (ref or "")

	def voice(running: str, finished: str) -> str:
		return finished if done else running

	if pair := TOOL_LABELS.get(tool_name):
		return voice(*pair)
	if tool_name == "read_page" and args.get("ref"):
		return f"{voice('Reading', 'Read')} block: {resolved_label(args.get('ref'))}"
	if tool_name == "read_page":
		title = args.get("page_id") and frappe.db.get_value("Builder Page", args["page_id"], "page_title")
		if title:
			return f"{voice('Reading', 'Read')} page: {title}"
		return voice("Reading another page", "Read another page")
	if tool_name == "set_design_token":
		# The tool's argument is token_name; reading `name` meant every token in the
		# chat read "Set theme variable" no matter which one it was.
		label = args.get("token_name") or args.get("id")
		if label:
			return f"{voice('Setting', 'Set')} token: {label}"
		return voice("Setting a theme variable", "Set theme variable")
	if tool_name == "set_page_script":
		return f"{voice('Adding', 'Added')} script: {args.get('name') or ''}".rstrip(": ")
	if tool_name == "update_script":
		return f"{voice('Updating', 'Updated')} script: {args.get('script_name') or ''}".rstrip(": ")
	if tool_name == "detach_page_script":
		return f"{voice('Removing', 'Removed')} script: {args.get('script_name') or ''}".rstrip(": ")
	if tool_name == "write_plugin":
		label = args.get("label") or args.get("name")
		return (
			f"{voice('Building', 'Built')} plugin: {label}"
			if label
			else voice("Building a plugin", "Built a plugin")
		)
	if tool_name == "get_doctype_schema":
		checking = voice("Checking", "Checked")
		return (
			f"{checking} the {args['doctype']} fields"
			if args.get("doctype")
			else f"{checking} the data fields"
		)
	if tool_name in ("get_document", "query_records"):
		return f"{voice('Reading', 'Read')} {readable_doctype(args.get('doctype'))}"
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
		image_file_url: str | None = None,
		canvas_theme: str | None = None,
		effort: str | None = None,
		registry: ToolRegistry | None = None,
		system_prompt: str | None = None,
	):
		self.prompt = prompt
		self.model = model
		self.api_key = api_key
		self.user = user or frappe.session.user
		self.page_id = page_id
		self.session_id = session_id
		# The realtime channel: the page the chat is attached to.
		self.channel = page_id or session_id
		self.selected_block_ids = selected_block_ids or []
		self.image_url = image_url
		self.image_file_url = image_file_url
		self.canvas_theme = canvas_theme
		self.effort = llm.Effort(effort)
		self.registry = registry or build_default_registry()
		# Skills in context, including read_skill results; reset on every turn.
		self.attached_skills: set[str] = set()
		self.round_skills: set[str] = set()
		# The editor-URL prefix is site-configurable; resolve it so the links the
		# agent writes (e.g. to a page it built off-canvas) actually work here.
		self.system_prompt = (system_prompt or Prompts.AGENT_SYSTEM).replace(
			"{BUILDER_PATH}", frappe.conf.builder_path or "builder"
		)
		# The authoritative working tree — loaded from the DB by load_page in run().
		self.tree: WorkingTree | None = None
		# Page locks acquired this turn ((key, token) pairs, token-fenced);
		# released in run()'s finally.
		self.held_locks: list[tuple[str, str]] = []
		# Images a server tool wants shown to the model (e.g. a preview_page screenshot).
		# Drained after each round as a follow-up user message — OpenAI-shape tool
		# results can't reliably carry image parts through OpenRouter.
		self.pending_images: list[dict] = []
		# Every photo search_images turned up this turn, handed to the generation step
		# so the page can use any of them without the model retyping urls into a brief.
		self.found_images: list[dict] = []
		# Page-level geometry of every reference page read this turn (read_page stashes
		# it), handed to the generation step — a brief's prose loses the root layout.
		self.reference_reads: list[str] = []
		# The turn's timeline, streamed to the chat as ai_chat_step events and persisted
		# on the final message: what the model thought about, the tools it ran, and the
		# narration it wrote between rounds — in the order they happened.
		self.steps: list[dict] = []
		# step id -> monotonic start, so a step can be timed without the clock riding
		# along into the emitted event and the persisted metadata.
		self.step_starts: dict[int, float] = {}
		# step id -> the past-tense label finish_step swaps in (see begin_activity).
		self.step_done_summaries: dict[int, str] = {}
		# What the chat is currently showing as the live answer: the text streamed
		# since the last round was committed. finish_turn compares against it so a
		# summary already on screen isn't said twice.
		self.live_text = ""
		# preview_page calls this turn — hard-capped so a screenshot loop can't run up cost.
		self.preview_count = 0
		self.image_views = 0
		# read_page calls this turn — same idea, a reference sweep can't run up context.
		self.page_read_count = 0
		# A page generated this turn that no preview has looked at yet: a closing
		# `reply` waits until it has been (the self-review catches empty rows and
		# fonts that never loaded). generation_errors: lines the generator wrote that
		# did not parse.
		self.unreviewed_build = False
		self.generation_errors: list[str] = []
		# Style sets the model was shown this turn ($s1 on the open page, $a1… on
		# references), so an edit script can spread them by name.
		self.style_sets: dict[str, dict] = {}
		# Web tools this turn — bounded like every other read that costs context/latency.
		self.web_read_count = 0
		self.research_count = 0
		self.web_sources: list[dict] = []
		# Successful WRITE-side server-tool calls this turn (settings, scripts, data,
		# page creation…) — counts as real work for the no-op-claim guards.
		self.server_mutations = 0
		# Every client op the tree accepted this turn (block edits, scripts, generation).
		self.applied_operations: list[dict] = []
		# Revert bookkeeping: pending_state is the page's pre-turn state, not yet
		# snapshotted; revert_snapshot is its snapshot doc once the turn mutates.
		self.pending_state: dict | None = None
		self.revert_snapshot: str | None = None
		# Per-turn debug trace (one entry per round) + why the turn ended. Persisted on
		# the assistant message so the agent debugger can explain what the model did and
		# why it stopped (e.g. "model_finished after 1 round, 2 tool calls").
		self.trace: list[dict] = []
		self.stop_reason = ""
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
		# Client ops a server tool queued mid-call (extract_component rewriting the
		# page). Drained right after the handler returns — see drain_queued_ops.
		self.pending_client_ops: list[dict] = []
		# The plugins write_plugin saved this turn, for the chat's plugin cards.
		self.plugins_written: list[str] = []
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
		# `cached_tokens` is the cache-read slice of prompt_tokens; `per_call` keeps
		# each call's split so a turn can be read round by round.
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

	def emit(self, suffix: str, *, after_commit: bool = False, **kwargs):
		# The channel is the page (in-editor chat) or, page-less, the session (dashboard
		# chat + sub-agent progress). Fixed at construction — see self.channel.
		#
		# after_commit=True for any event whose handler READS what this turn just wrote
		# (a reload, a refetch, the final transcript): frappe holds the emit until the
		# transaction lands and drops it on rollback, so the client can never fetch
		# state that doesn't exist yet. Live narration (stream/progress) emits at once.
		event = f"{EVENT_PREFIX}_{suffix}"
		if self.channel:
			event = f"{event}_{self.channel}"
		frappe.publish_realtime(
			event,
			{"page_id": self.page_id, "session_id": self.session_id, **kwargs},
			user=self.user,
			after_commit=after_commit,
		)

	def ensure_revert_snapshot(self) -> None:
		"""Snapshot the page's pre-turn state the first time the turn mutates it —
		before the mutation lands, so even a cancelled multi-round edit stays
		revertable. One snapshot per turn."""
		if self.pending_state is None or not self.page_id:
			return
		state, self.pending_state = self.pending_state, None
		if snapshot := save_revert_snapshot(self.page_id, state):
			self.revert_snapshot = snapshot

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
		`model` is unused now that only token counts are tallied; kept so callers can
		keep naming the model that produced the stream."""
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
							redact_secrets(json.dumps(op.get("args", {}), ensure_ascii=False)), 300
						),
					}
					for op in tool_operations
				],
				"text": BlockCodec.truncate_for_log(text or "", 300),
			}
		)

	# --- message construction --------------------------------------------

	def build_page_context(self) -> str:
		return render_page_context(self.page_root(), self.selected_block_ids, self.style_sets)

	def build_initial_page_context(self) -> str:
		"""The open page rides in with the request: nearly every turn reads it first, and
		a read costs a whole round. An empty page brings the new-page skill instead; a
		page past the full-render limit only says where to read it."""
		if not self.page_id:
			return ""
		root = self.page_root()
		if not (root and root.get("children")):
			return "The open page is empty.\n\n" + self.build_skill_context()
		context = render_page_context(root, self.selected_block_ids, self.style_sets)
		if any(block.get("extendedFromComponent") for block, _ in walk_blocks(root)):
			context += "\n\n" + self.attach_skill("components", "This page embeds components")
		if context.startswith(PAGE_PREAMBLE):
			return f"{context}\n\nThis is the page as the turn starts; your edits apply live, and read_page re-reads it."
		return (
			f"The open page is large; read_page('{self.page_id}') returns its outline. Editor plugins "
			"can use the page API at runtime without reading this page's blocks.\n\n"
			+ render_selected_context(root, self.selected_block_ids)
		)

	def build_open_page_context(self) -> str:
		"""The facts the agent cannot discover for itself: WHICH page the user has
		open, and the theme the editor shows it in. Everything else about the site is
		pulled on demand (run_python, read_page, query_records) — nothing is pre-baked
		into the context."""
		if not self.page_id:
			return ""
		row = frappe.db.get_value(
			"Builder Page", self.page_id, ["page_title", "route", "published", "staging"], as_dict=True
		)
		if not row:
			return ""
		state = "live" if row.published else "staging" if row.staging else "draft"
		route = "/" + (row.route or "").lstrip("/")
		context = (
			f"Open page: '{row.page_title or self.page_id}' — id {self.page_id}, route {route}, {state}."
		)
		if self.canvas_theme:
			context += (
				f" The user is viewing it in {self.canvas_theme} mode in the editor, so what they "
				f"describe seeing is the {self.canvas_theme}-mode rendering."
			)
		return context

	def build_skill_context(self) -> str:
		"""Include the build guide when the model asks to inspect an empty page."""
		root = self.page_root()
		if not self.page_id or (root and root.get("children")):
			return ""
		return self.attach_skill("new-page", "For building on this empty page")

	def attach_skill(self, name: str, reason: str) -> str:
		"""A skill the open page's state calls for, put in context before the model asks."""
		if name in self.attached_skills:
			return ""
		self.attached_skills.add(name)
		return f"{reason}, here is the {name} skill in full; no read_skill needed this turn:\n\n{Skills.read(name)}"

	def require_skill(self, name: str) -> str | None:
		# A read alongside a write has not reached the model that authored that write.
		if name not in self.round_skills:
			return (
				f"FAILED: read_skill('{name}') before authoring this work, then retry in the next round "
				"using its guidance. Nothing was changed. Read it again on each continuation turn."
			)
		return None

	def build_memory_context(self) -> str:
		"""Facts the agent saved in past conversations (see tools/memory.py) — part of
		the cached context block, so remembering costs nothing per-round."""
		from builder.ai.agent.tools.memory import memory_context

		return memory_context()

	def build_plugins_context(self) -> str:
		"""History replays only the chat text, where a plugin shows by its label. Its id lets a
		change read_plugin it in the first round instead of listing every plugin first."""
		if plugins := AISession.plugins_written(self.session_id):
			return (
				f"Plugins you wrote in this conversation: {', '.join(plugins)}. To change one, read_plugin "
				"it by that name in the same round as read_skill('editor-plugin')."
			)
		return ""

	def build_messages(self) -> list[dict]:
		messages: list[dict] = [{"role": "system", "content": self.system_prompt}]

		# Prior conversation FIRST, as proper role-tagged turns: old turns replay
		# byte-stable from the session rows, so system + history stays a provider-
		# cache prefix hit ACROSS turns. The page context goes after — it changes
		# every turn and would otherwise invalidate everything behind it.
		messages.extend(
			AISession.build_context_messages_from_id(
				self.session_id, include_images=ModelRegistry.supports_vision(self.loop_model)
			)
		)
		self.history_end_index = len(messages) - 1

		# The page identity and selections stay useful across tasks. Load the full
		# tree on demand: this context is cached across rounds, but changed history
		# ahead of it generally prevents reuse across turns.
		blocks = [
			self.build_open_page_context(),
			self.build_initial_page_context(),
			self.build_memory_context(),
			self.build_plugins_context(),
		]
		context = "\n\n".join(block for block in blocks if block)
		if context:
			messages.append({"role": "user", "content": context})
			messages.append({"role": "assistant", "content": "Understood. I have the current context."})

		user_text = self.prompt
		if self.selected_block_ids:
			user_text += "\n\n" + self.attached_blocks_note()
		if self.image_url and self.image_file_url:
			# The image itself rides below; the model also needs its ADDRESS — the
			# only handle a brief can carry into the generation step.
			user_text += (
				f"\n\n(Attached image, saved at {self.image_file_url} — when it should guide a build, "
				f"carry that exact url in the brief on its own line: REFERENCE IMAGE: {self.image_file_url})"
			)
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
		Deterministic positions: the system prompt and the end of the replayed
		history (both 1h TTL — they are the prefix the NEXT turn re-matches, and
		user turns are minutes apart, so the 5m default would expire exactly on
		the entries that matter across turns), the current user prompt (the stable
		turn-start prefix), the newest message (caches this round's prefix for the
		next), and a mid-turn anchor every MID_TURN_MARKER_EVERY messages so a
		long turn's rounds stay inside Anthropic's cache-lookback window. Capped
		at 4 markers, oldest dropped first — their cache entries were already
		written by earlier rounds."""
		for m in messages:
			m.pop("cache_control", None)
			if isinstance(m.get("content"), list):
				for block in m["content"]:
					if isinstance(block, dict):
						block.pop("cache_control", None)
		last = marker_position(messages, len(messages) - 1)
		history_end = max(self.history_end_index, 0)
		positions = {0, history_end, self.prompt_index, last}
		span = len(messages) - 1 - self.prompt_index
		if span > MID_TURN_MARKER_EVERY + 3:
			anchor = self.prompt_index + MID_TURN_MARKER_EVERY * (span // MID_TURN_MARKER_EVERY)
			positions.add(marker_position(messages, min(anchor, last)))
		long_lived = {0, history_end}
		for pos in sorted(positions)[-MAX_CACHE_MARKERS:]:
			messages[pos]["cache_control"] = SYSTEM_CACHE_CONTROL if pos in long_lived else TURN_CACHE_CONTROL

	# --- LLM call ---------------------------------------------------------

	def call_tool_llm(self, messages: list[dict]) -> tuple[list[dict], str, list[dict]]:
		"""Stream one tool-calling round, retrying the WHOLE round on a transient stream
		failure (network drop, 429, 5xx, mid-stream reset). Safe because a round applies
		nothing until it returns — ops are emitted and `messages` mutated by the caller only
		after this returns, so a failed attempt leaves no partial state; we just re-issue the
		identical completion (the cached prefix makes the retry cheap). litellm can't fall
		back mid-stream (fallbacks are off while streaming), so this is the retry layer."""
		self.round_skills = self.attached_skills.copy()
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
		text_content, raw_tool_calls). Applies nothing (see call_tool_llm) —
		accumulates into locals only, so it is safe to re-run; the narration it
		emits is only ever shown, never state a retry could corrupt.

		Tool-call arguments are accumulated by index across chunks.
		`raw_tool_calls` reconstruct the assistant turn for a follow-up round.
		Large artifacts (e.g. a full page) are NOT streamed here — the model
		calls an artifact tool with a short brief, and the loop hands generation
		to that tool's generator, which streams the artifact as content.
		"""
		stream = llm.complete_with_tools(
			self.loop_model,
			messages,
			self.registry.schemas(self.round_skills),
			self.effort.params("agent"),
			api_key=self.api_key,
			stream=True,
			timeout=self.effort.stall_timeout,
		)

		content_parts: list[str] = []
		# index -> {"id", "name", "args"}; preserves call order across chunks.
		acc: dict[int, dict] = {}
		finish_reason = None
		# The model is thinking until it emits its first output of any kind. Providers
		# that stream reasoning fill this step with it; the rest leave it holding just
		# the latency, which is still the honest answer to "what is it doing?".
		# A retry re-issues the identical completion, so whatever the failed attempt
		# streamed has to come off the screen first or the answer arrives doubled.
		if self.live_text:
			self.live_text = ""
			self.emit("stream", chunk="", replace=True)
		thinking = self.add_step("thinking", status="running")
		thinking_since: float | None = time.monotonic()

		try:
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
				content = getattr(delta, "content", None)
				tool_calls = getattr(delta, "tool_calls", None)
				if reasoning := getattr(delta, "reasoning_content", None):
					thinking["text"] = (thinking.get("text") or "") + reasoning
					self.emit("stream", chunk=reasoning, kind="reasoning")
				if thinking_since is not None and (content or tool_calls):
					self.finish_step(thinking, started=thinking_since)
					thinking_since = None
				if content:
					content_parts.append(content)
					# Stream the model's words as it writes them. A round that turns out
					# to have called tools commits this as a narration step below; the
					# last round's text is the turn's answer and stays as the content.
					self.live_text += content
					self.emit("stream", chunk=content)
				for tc in tool_calls or []:
					idx = tc.index if tc.index is not None else 0
					entry = acc.setdefault(idx, {"id": None, "name": None, "args": ""})
					if tc.id:
						entry["id"] = tc.id
					fn = getattr(tc, "function", None)
					if fn and fn.name:
						entry["name"] = fn.name
					if fn and fn.arguments:
						entry["args"] += fn.arguments
		finally:
			# A cancel or a dropped stream must not leave the spinner running forever.
			if thinking_since is not None:
				self.finish_step(thinking, started=thinking_since)

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

	def queue_client_op(self, op: dict) -> None:
		"""Called by a server tool mid-handler to emit a client op (extract_component
		queues the rewritten page tree here). Drained right after the handler."""
		self.pending_client_ops.append(op)

	def drain_queued_ops(self) -> list[dict]:
		"""Snapshot, sync the working tree, persist, and emit ops a server tool queued
		mid-handler (extract_component queues the rewritten page as set_page_blocks),
		so the canvas updates live and later tools see the tree they already changed."""
		from builder.ai import page_writer

		ops, self.pending_client_ops = self.pending_client_ops, []
		if not ops:
			return []
		if any(op["tool_name"] in SNAPSHOT_TOOLS for op in ops):
			self.ensure_revert_snapshot()
		for op in ops:
			if op["tool_name"] == "set_page_blocks":
				# Repair childless component instances or they render as nothing
				# (editor + published alike).
				op["args"]["blocks"] = page_writer.normalize_component_instances(op["args"]["blocks"])
				self.tree.root = op["args"]["blocks"]
		self.applied_operations.extend(ops)
		self.emit("tool_batch", operations=ops)
		if self.page_id and self.tree and self.tree.root:
			page_writer.save_draft_blocks(self.page_id, self.tree.root)
		return ops

	def page_root(self) -> dict | None:
		"""The current page's root block — the authoritative working tree. Edits made
		this turn are visible to context rebuilds and the query tools, and refs stay
		valid across rounds."""
		return self.tree.root if self.tree else None

	def load_page(self, page_id: str) -> str:
		"""Load the turn's page into the working tree (context, query tools and block
		edits all read/write it), take the page lock for the rest of the turn so two
		AI turns can't fight over one page, and capture the pre-edit state so the turn
		stays revertable. Returns "" on success, or a FAILED reason."""
		from builder.ai import page_writer

		key = locks.page_key(page_id)
		token = locks.acquire(key, self.effort.lock_ttl)
		if token is None:
			return (
				f"FAILED: page {page_id} is being edited by another AI task right now. Try again in a moment."
			)
		self.held_locks.append((key, token))
		self.tree = WorkingTree(page_writer.load_page_root(page_id))
		self.pending_state = capture_page_state(page_id)
		return ""

	# --- turn timeline ------------------------------------------------------

	def add_step(self, kind: str, **fields) -> dict:
		"""Append one timeline entry and stream it. Steps are upserted client-side by
		id, so a running step is finished by re-emitting the same entry."""
		step = {"id": len(self.steps), "kind": kind, **fields}
		self.steps.append(step)
		self.emit("step", **step)
		return step

	def finish_step(self, step: dict | None, started: float | None = None, **fields) -> None:
		if step is None:
			return
		step["status"] = "done"
		if started is not None:
			step["ms"] = round((time.monotonic() - started) * 1000)
		step.update(fields)
		self.emit("step", **step)

	def tool_steps(self) -> list[dict]:
		return [s for s in self.steps if s.get("kind") == "tool"]

	def timeline(self) -> list[dict]:
		"""The steps worth keeping on the message. Empty narration steps exist only to
		tell the client to drop what it streamed, and a thinking step with no reasoning
		behind it is not worth replaying — on reload it would read as a stall."""
		return [
			s
			for s in self.steps
			if (s.get("kind") == "tool")
			or (s.get("kind") == "text" and s.get("text"))
			or (s.get("kind") == "thinking" and s.get("text"))
		]

	def attached_blocks_note(self) -> str:
		"""Attaching is a scoping act, not a hint — and labels ride along because a
		bare ref gives the model nothing to anchor the request's nouns to."""
		from builder.ai.agent.selectors import find_block

		root = self.page_root()
		labelled = []
		for ref in self.selected_block_ids:
			block = find_block(root, ref) if root else None
			labelled.append(f"{ref} ({block_label(block)})" if block else ref)
		return (
			"ATTACHED BLOCKS — the user explicitly attached these blocks to this request: "
			f"{', '.join(labelled)}. They are the SUBJECT and SCOPE of the request: interpret "
			"it as being about them, and make your changes on or within them. Look at their "
			"current styles first (page context or read_page). Touch other blocks only when "
			"the request itself plainly requires it, and say so if you do."
		)

	def begin_activity(self, tool_name: str, args: dict) -> dict | None:
		if tool_name in ACTIVITY_SILENT:
			return None
		entry = self.add_step(
			"tool",
			tool=tool_name,
			summary=activity_summary(tool_name, args, self.tree, done=False),
			status="running",
		)
		self.step_starts[entry["id"]] = time.monotonic()
		# Resolved now, while args/tree still describe the call; finish_step swaps it in.
		self.step_done_summaries[entry["id"]] = activity_summary(tool_name, args, self.tree)
		return entry

	def end_activity(self, entry: dict | None) -> None:
		if entry is None:
			return
		self.finish_step(
			entry,
			started=self.step_starts.pop(entry["id"], None),
			summary=self.step_done_summaries.pop(entry["id"], entry.get("summary")),
		)

	@staticmethod
	def describe_operations(operations: list[dict]) -> str:
		"""A deterministic one-line summary of applied ops — used when the model
		didn't return its own summary text, so we avoid a second LLM round trip."""
		from collections import Counter

		counts = Counter(op.get("tool_name") for op in operations)

		def blk(n: int) -> str:
			return "block" if n == 1 else "blocks"

		parts: list[str] = []
		if n := counts.get("add_block"):
			parts.append(f"added {n} {blk(n)}")
		if n := counts.get("update_block"):
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
		if counts.get("detach_page_script"):
			parts.append("removed a script")

		if not parts:
			n = len(operations)
			return f"Applied {n} change{'s' if n != 1 else ''} to the page"
		sentence = parts[0] if len(parts) == 1 else f"{', '.join(parts[:-1])} and {parts[-1]}"
		# No trailing period: these render as timeline rows beside "Checked how it
		# looks" and friends, which carry none.
		return sentence[0].upper() + sentence[1:]

	# --- round execution ----------------------------------------------------

	def op_kind(self, op: dict) -> str:
		"""How the loop must handle one tool call: "artifact" (streamed generation),
		"terminal" (ends the turn), "server" (run the handler now), or "client"
		(apply to the working tree + mirror to the canvas). A client tool with a
		server twin (page scripts) always runs as a server op — see
		SCRIPT_TWIN_TOOLS."""
		tool = self.registry.get(op["tool_name"])
		if tool and tool.artifact:
			return "artifact"
		side = tool.side if tool else "client"
		if side == "client" and tool and tool.handler and op["tool_name"] in SCRIPT_TWIN_TOOLS:
			return "server"
		return side

	def apply_client_ops(self, ops: list[dict]) -> tuple[dict[int, str], list[dict]]:
		"""Apply this round's client ops to the working tree, the source of truth,
		then mirror the ACCEPTED ones to the canvas and persist the draft. Rejected
		ops are never emitted, so the canvas can't apply an edit the server refused.
		An edit_page script expands into the internal block ops it compiled to.
		Returns (tool-result per op, accepted ops)."""
		results: dict[int, str] = {}
		applied: list[dict] = []
		for op in ops:
			if op["tool_name"] in SNAPSHOT_TOOLS:
				self.ensure_revert_snapshot()
			if op["tool_name"] == "edit_page":
				content, accepted = EditScript(self.tree, self.style_sets).run(op["args"].get("ops") or "")
			else:
				content = self.tree.apply(op["tool_name"], op["args"])
				accepted = [] if content.startswith("FAILED") else [op]
			results[id(op)] = content
			# A correction the model is now being asked to make: record + log it.
			if "FAILED" in content or "NOT FOUND" in content:
				self.tool_failures.append(f"{op['tool_name']}: {content}")
				logger.warning("Client op rejected — %s: %s", op["tool_name"], content)
			applied.extend(accepted)
		if applied:
			self.applied_operations.extend(applied)
			# after_commit: an op can reference a doc this round created (a component
			# extract) — mirrored early, the canvas fetches it before the checkpoint
			# commit lands and caches a Missing placeholder.
			self.emit("tool_batch", operations=applied, after_commit=True)
			if self.page_id and self.tree.root:
				from builder.ai import page_writer

				# Persist after every applied round so a cancel/crash keeps the work
				# done so far (the same live-apply semantics the canvas shows).
				page_writer.save_draft_blocks(self.page_id, self.tree.root)
		return results, applied

	def skill_missing(self, tool) -> str | None:
		"""A skill-bound tool called before its skill reached the model (it named one
		it was never offered)."""
		return self.require_skill(tool.skill) if tool and tool.skill else None

	def run_handler(self, tool, op: dict) -> str:
		"""Run a server tool's handler, turning a crash into a tool result.

		An unguarded handler takes the whole turn down: the exception unwinds to
		run_turn, which can only apologise and abandon everything else the turn was
		going to do. Seen live from a duplicate token id and from an image URL the
		provider could not fetch. Reported as FAILED instead, which the tools already
		use for expected failures, so the model can adjust and carry on. The savepoint
		keeps a half-applied write from riding along."""
		if missing := self.skill_missing(tool):
			return missing
		savepoint = f"tool_{self.server_mutations}"
		frappe.db.savepoint(savepoint)
		try:
			return tool.handler(self, op["args"])
		except CancelledError:
			raise
		except Exception as e:
			frappe.db.rollback(save_point=savepoint)
			logger.warning(f"tool {op['tool_name']} raised: {e}", exc_info=True)
			return f"FAILED: {op['tool_name']} errored ({type(e).__name__}: {e}). Adjust and try again."

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
			# Generation is a STEP of the turn: the generator streams the page live (the
			# canvas preview), persists the page, and the loop continues — so the model
			# can add scripts, verify, and refine in the same turn.
			content, ops = self.run_generation_step(tool, op)
			self.unreviewed_build = self.unreviewed_build or bool(ops)
			self.applied_operations.extend(ops)
			if ops:
				# The authoritative op replaces the throwaway streamed preview with
				# the server's block tree (shared ids).
				self.emit("tool_batch", operations=ops)
			return content
		entry = self.begin_activity(op["tool_name"], op["args"])
		if op["tool_name"] in SNAPSHOT_TOOLS:
			self.ensure_revert_snapshot()
		content = self.run_handler(tool, op)
		if op["tool_name"] == "preview_page" and not str(content).startswith("FAILED"):
			self.unreviewed_build = False
		self.end_activity(entry)
		self.drain_queued_ops()
		if op["tool_name"] not in READ_ONLY_SERVER_TOOLS and not str(content).startswith("FAILED"):
			self.server_mutations += 1
			if op["tool_name"] in SCRIPT_TWIN_TOOLS:
				# Mirror the server-applied script op so the open editor updates its
				# script list / undo tracking — flagged so the canvas does NO DB work.
				op["args"]["server_applied"] = True
				self.applied_operations.append(op)
				self.emit("tool_batch", operations=[op])
		return content

	def commit_round_text(self, text: str, applied: list[dict]) -> None:
		"""Close off a tool-calling round's narration. The words were already streamed
		as they were written; this fixes them in the timeline so the next round starts
		with a clean slate, and stands in with a description of the ops when the model
		called tools without saying anything."""
		note = (text or "").strip()
		if not note and applied:
			note = self.describe_operations(applied)
		self.live_text = ""
		self.add_step("text", status="done", text=note)

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

	def read_notes(self, messages: list[dict]) -> None:
		"""Messages the user sent while this turn ran, read in between rounds. Each is
		saved as a user message of its own so later turns see it too."""
		for note in AISession.pop_notes(self.session_id):
			AISession.try_append_message(
				self.session_id,
				"user",
				note,
				message_type="chat",
				task_type="agent",
				metadata={"canvasTheme": self.canvas_theme, "effort": self.effort.level},
			)
			messages.append({"role": "user", "content": f"(Sent while you were working.)\n{note}"})
			self.emit("note", text=note)

	# --- orchestration ----------------------------------------------------

	def emit_cancelled(self) -> None:
		msg = "Stopped. Kept what was built so far." if self.applied_operations else "Cancelled."
		AISession.try_append_message(
			self.session_id, "assistant", msg, message_type="status", metadata={"status": "cancelled"}
		)
		self.emit("complete", message=msg, after_commit=True)

	def fail_turn(self, message: str) -> None:
		"""End the turn with a persisted error message + error event."""
		AISession.try_append_message(
			self.session_id, "assistant", message, message_type="status", metadata={"status": "error"}
		)
		self.emit("error", message=message, after_commit=True)

	def run(self):
		# Clear any stale cancel flag or notes from a previous turn before starting.
		self.clear_cancel_flag()
		AISession.clear_notes(self.session_id)
		started = time.monotonic()
		logger.info(
			f"AgentRunner.run: page_id={self.page_id}, model={self.model}, "
			f"session_id={self.session_id}, user={self.user}"
		)

		# One turn per session at a time — an atomic Redis lock with a TTL, so a
		# crashed worker can never brick the session (the old is_running DB flag did).
		if self.session_id:
			self.run_token = AISession.start_run(self.session_id, self.effort.lock_ttl)
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
			# Unread ones go back to the chat, which sends them as the next turn.
			AISession.clear_notes(self.session_id)
			for key, token in self.held_locks:
				locks.release(key, token)
			self.held_locks = []
			if self.session_id:
				AISession.end_run(self.session_id, self.run_token)

	def run_turn(self, started: float):
		# Load the page into the authoritative working tree, under the page lock.
		if self.page_id and self.tree is None:
			if self.load_page(self.page_id).startswith("FAILED"):
				# Shown verbatim in the chat — human words, no internal page id.
				self.fail_turn("Another AI request is still working on this page. Try again in a moment.")
				return
		if self.tree is None:
			self.tree = WorkingTree(None)

		# Every turn runs on the model the user picked: edit taste matters as much as
		# generation taste, and silently swapping a deliberately-picked model is the
		# surest way to degrade output.
		self.loop_model = self.model
		label = ModelRegistry.get_label(self.loop_model)
		self.emit("progress", message=f"Thinking with {label}" if label else "Thinking…")

		messages = self.build_messages()
		summary_text = ""

		try:
			for round_index in range(MAX_ROUNDS):
				# A cancel that landed mid-round (e.g. during a generation stream that
				# kept its partial page) ends the turn HERE, before another paid call.
				if round_index and self.is_cancelled():
					raise CancelledError
				self.refresh_cache_markers(messages)
				tool_operations, summary_text, raw_tool_calls = self.call_tool_llm(messages)
				self.record_round(round_index, tool_operations, summary_text)

				if not tool_operations:
					self.stop_reason = "model_finished"
					break

				# Apply block/script ops FIRST — the canvas updates live, and a terminal
				# tool in the same round can no longer silently discard them.
				client_ops = [op for op in tool_operations if self.op_kind(op) == "client"]
				client_results, applied = self.apply_client_ops(client_ops)

				# Committed for a terminal round too: the sentence the model writes
				# before a card ("I'll settle the direction first…") is part of the
				# conversation, and present_ui persists the timeline with the card.
				self.commit_round_text(summary_text, applied)

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
				results = [m["content"] for m in messages[-len(raw_tool_calls) :]]
				if reply := self.turn_reply(tool_operations, results):
					summary_text = reply
					self.stop_reason = "model_finished"
					self.checkpoint()
					break
				self.flush_pending_images(messages)
				self.read_notes(messages)
				self.checkpoint()
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
			# Never the raw provider/exception string: it can leak internals (keys, model
			# ids, stack detail). Full error is logged above.
			self.fail_turn(llm.user_facing_error(e))
			return

		self.finish_turn(summary_text, started)

	def turn_reply(self, ops: list[dict], results: list[str]) -> str:
		"""The reply that ends the turn now, if any: never while a page generated this
		turn is still unreviewed."""
		return "" if self.unreviewed_build else self.closing_reply(ops, results)

	@staticmethod
	def closing_reply(ops: list[dict], results: list[str]) -> str:
		"""An edit_page `reply` ends the turn without another round when nothing in the
		round still needs a look: every call landed, and none was a read (a preview, a
		page) whose result the model has yet to see."""
		replies = [
			reply
			for op in ops
			if op["tool_name"] == "edit_page" and (reply := str(op["args"].get("reply") or "").strip())
		]
		if not replies or any(op["tool_name"] in READ_ONLY_SERVER_TOOLS for op in ops):
			return ""
		return "" if any("FAILED" in str(result) for result in results) else replies[-1]

	def checkpoint(self) -> None:
		"""Make this round's work durable. A turn runs as a background job, and a job
		that raises rolls the WHOLE transaction back (background_jobs.execute_job) —
		without this, a provider timeout in round 7 would discard the pages, scripts
		and messages written in rounds 1-6. It is also what lets the editor and the
		chat, both separate requests, see a long turn progress instead of nothing
		until it ends. One commit per round: individual tools never commit."""
		frappe.db.commit()  # nosemgrep

	def finish_turn(self, summary_text: str, started: float):
		"""Wrap up a completed loop: pick/emit the final summary and persist the turn."""
		if not self.applied_operations and not summary_text:
			# A soft miss, not a failure: the model may have done real tool work (reads)
			# and just failed to write its reply. Warn — and persist, so the turn doesn't
			# vanish on reload.
			logger.warning("Agent returned empty response (no text; tools=%d)", len(self.tool_steps()))
			if self.server_mutations:
				note = "Done. The steps above were applied (I skipped the write-up)."
			elif self.tool_steps():
				note = (
					"I gathered that information but didn't write up a reply. Ask me again and I'll answer."
				)
			else:
				note = "I came back empty on that one. Try rephrasing your request."
			metadata = {"status": "warning"}
			if timeline := self.timeline():
				metadata["steps"] = timeline
			AISession.try_append_message(
				self.session_id, "assistant", note, message_type="status", metadata=metadata
			)
			self.emit("error", message=note, warning=True, after_commit=True)
			return

		# Block/script edits and generation ops were already emitted incrementally inside
		# the loop (live canvas progress); nothing more to emit here.
		generated = any(op["tool_name"] == "generate_page" for op in self.applied_operations)
		if not summary_text:
			if generated:
				# Skip a summary call after generation (the page arg would bloat its
				# context); send a fixed nudge instead.
				summary_text = "Created the page. Ask me to refine it — adjust styles, add sections, or change the layout."
			else:
				# Block/script edits with no model text: synthesise the summary from
				# the ops rather than making a second LLM call. The canvas already
				# updated from the tool_batch above; this just ends the turn sooner.
				summary_text = self.describe_operations(self.applied_operations)
		# The final round's words already reached the chat as they were written. Only
		# say it again when it is NOT what the user is looking at — a synthesised
		# summary, or one of the guards above having replaced what the model wrote.
		if summary_text != self.live_text:
			self.emit("stream", chunk=summary_text, replace=True)

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
				"effort": self.effort.level,
				"rounds": len(self.trace),
				"argsRepaired": self.args_repaired,
				"finishReasons": self.finish_reasons,
				"toolFailures": self.tool_failures,
				"streamRetries": self.stream_retries,
				"tokens": self.usage,
				# How much room the conversation has: the loop model's window; the
				# latest call's prompt_tokens (per_call) is the current context size.
				"contextWindow": ModelRegistry.context_window(self.loop_model),
				"elapsedMs": elapsed_ms,
				"trace": self.trace,
			},
		}
		if self.revert_snapshot:
			final_metadata["revertSnapshot"] = self.revert_snapshot
		if self.plugins_written:
			final_metadata["plugins"] = self.plugins_written
		if self.web_sources:
			final_metadata["sources"] = self.web_sources
		if timeline := self.timeline():
			# The turn's timeline — rendered live from step events, rehydrated from
			# here on a session reload.
			final_metadata["steps"] = timeline
		AISession.try_append_message(
			self.session_id,
			"assistant",
			summary_text or f"Applying {len(self.applied_operations)} change(s).",
			message_type="chat",
			task_type="agent",
			metadata=final_metadata,
		)
		self.maybe_name_session()
		self.emit("complete", message=summary_text or "Done", after_commit=True)

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
				self.model,
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
		if missing := self.skill_missing(tool):
			return missing
		if tool and tool.handler:
			return tool.handler(self, op["args"])
		return None

	def run_generation_step(self, tool, op: dict) -> tuple[str, list[dict]]:
		"""Run generate_page as one STEP of the turn. The generator persists the page
		server-side; point the working tree at the result so the model can read back —
		and build on — what it just made (scripts, surgical fixes, one verify pass)."""
		if not self.page_id:
			return ("FAILED: no page is open.", [])
		if missing := self.require_skill("new-page"):
			return missing, []
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
			"calls for (set_page_script), fix obvious breakage with edit_page, verify "
			"with preview_page at most once, then finish with a short summary."
			f"{self.script_hook_gap_note(root)}{composition_notes(root)}{self.dropped_lines_note()}\n"
			f"{render_page_context(root, sets=self.style_sets)}",
			ops,
		)

	def dropped_lines_note(self) -> str:
		if not (errors := self.generation_errors):
			return ""
		listed = "; ".join(errors[:6])
		return (
			f"\nDROPPED LINES: {len(errors)} line(s) of the generated page did not parse ({listed}). "
			"Whatever they held is missing: put it back with edit_page."
		)

	def script_hook_gap_note(self, root: dict) -> str:
		"""The class-contract check: scripts written in parallel with generation
		target class hooks the generated blocks must carry — a missing hook silently
		kills the behaviour (seen live: scripts selecting .suraj-project-card on a
		page whose blocks only carried .suraj-reveal). Compare the attached scripts'
		querySelector targets and CSS class selectors against the blocks' classes
		and tell the model NOW, while it can still patch with edit_page."""
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
				"those classes, so that behaviour will never fire. Add each class to the intended "
				"blocks (edit_page) or rewrite the script."
			)
		if missing_css:
			parts.append(
				f"CSS rules target unused classes: {', '.join('.' + c for c in missing_css)} — "
				"apply them to the intended blocks or they are dead styling."
			)
		return " ".join(parts)


def run_agent_job(prompt: str, model: str, **kwargs):
	# Resolved here so the key never sits in Redis; jobs queued by older code still pass one.
	kwargs.pop("api_key", None)
	AgentRunner(prompt, model, llm.resolve_api_key(model), **kwargs).run()
