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
    ai_chat_stream         {chunk, kind?, replace?}  kind="page_yaml" → live canvas
                                            preview; kind="reasoning" → append to the
                                            open thinking step; absent → append to the
                                            live answer text. replace=True means this
                                            chunk REPLACES the live answer (a guard
                                            rewrote it, or a retry is re-sending).
    ai_chat_tool_batch     {operations: [{tool_name, args}]}
                           (generate_page args carry the expanded {blocks, data_script};
                           add_block args carry block_json — the canvas applies those
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
	"(update_block/add_block for targeted edits, query_blocks + update_blocks for bulk ones, "
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
# Any card-atom name in bracket notation is mimicry, never natural prose — cover the
# replay vocabulary AND the schema vocabulary (a model can leak either: Kimi wrote
# "[actions: Continue]", blending the schema's kind name into the replay format).
CARD_TEXT_RE = re.compile(
	r"\[\s*(?:input|choices|buttons|upload|swatches|actions|color_input)\s*:"
	r"|\[\s*colou?r picker\b",
	re.IGNORECASE,
)

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
# Option-DECORATION markers (palette/image) are the exact format option_text()
# replays a card in — a model writing "[palette: #C4552D, …]" in a bullet is
# mimicking a past card as prose, whatever the lead-in reads like. Control-atom
# markers (actions/buttons/input/…) count the same way: a bulleted question that
# leaks ANY card notation is a card written as text.
OPTION_MARKER_RE = re.compile(
	r"\[\s*(?:palette|image|actions|buttons|input|choices|upload|swatches)\s*:",
	re.IGNORECASE,
)

BUILD_INCOMPLETE_CORRECTION = (
	"You set up the design system (tokens, page settings) but NEVER built the page — it is "
	"still EMPTY. Call generate_page NOW with a full brief: the chosen layout SYSTEM and its "
	"signature move, the font pairing, the palette and spacing as the exact var(--<id>) token "
	"handles you just minted, every section with real copy, and — if the user asked for "
	"movement — the class hooks your scripts will target. The turn is NOT done until the page "
	"has content."
)

OPTIONS_AS_TEXT_CORRECTION = (
	"You ended your turn by asking a question with a LIST OF OPTIONS as plain text — text "
	"renders no controls, so the user has nothing to tap. Ask it again as ONE present_ui "
	"call: a single short lead-in `text` atom, then a `choices` group with one option per "
	"item (label + short description, plus `colors` on a layout direction so its palette "
	"shows). A card that is one tappable question needs no extra button. Do NOT repeat the "
	"options in your message text."
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
# Skeletonising a page the model just wrote costs whole rounds re-reading its own
# work, so the threshold has to clear a real generated page. Measured across four
# models: eleven landed between 15.4k and 30.9k chars, one ran to 48.6k. 45k keeps
# the normal spread whole (~11k tokens, once per turn, behind a cache marker) and
# still lets a runaway page fall back to the outline, which is what it is for.
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
		"query_blocks",
		"read_block",
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


def render_page_context(root: dict | None, selected_block_ids: tuple | list = ()) -> str:
	"""Render a page's block tree as model-readable context: the full compact YAML
	for a normal page, or an outline (+ full detail for selected blocks) past
	FULL_CONTEXT_LIMIT. Shared by the turn's page-context message and the page
	tools."""
	if root is None:
		return ""
	full = to_compact_yaml(BlockCodec.compress(root, depth=0, task_tier="complex"))
	# Most pages: ship the full structure — cheapest path is no extra read_block
	# round-trips, and the model can match existing styles directly. Big pages: ship
	# a compact outline instead (styles/attrs omitted) and let the model pull detail
	# on demand with read_block. The threshold is on the full serialisation length,
	# which tracks token cost closely.
	if len(full) <= FULL_CONTEXT_LIMIT:
		context = (
			f"Current page structure (YAML — pass a block's 'ref' value as block_id to edit it):\n{full}"
		)
	else:
		context = render_skeleton_context(root, selected_block_ids)
	# THIS page's component contracts — without them an instance advertises nothing
	# (declared props were unreachable from the open page).
	from builder.ai.agent.tools.query import render_components

	if contract := render_components(root, on_open_page=True):
		return f"{context}\n\n{contract}"
	return context


OUTLINE_PREAMBLE = (
	"This page is large, so you're given a compact OUTLINE (one line per block: "
	"indentation = nesting, then ref, element, optional name, and a short text "
	"preview). Styles and attributes are omitted. Pass a block's ref as block_id to "
	"edit it. To see a block's full styles/attributes/text before editing, call "
	"read_block(ref); to act on many blocks at once, call query_blocks then update_blocks."
)


def render_skeleton_context(root: dict, selected_block_ids: tuple | list = ()) -> str:
	"""Outline + full detail for any blocks the user has selected (so the common
	targeted-edit case needs no read_block round-trip)."""
	from builder.ai.agent.selectors import find_block, render_skeleton

	outline = render_skeleton(root)
	parts = [OUTLINE_PREAMBLE, outline]
	for ref in selected_block_ids:
		block = find_block(root, ref)
		if block is None:
			continue
		detail = to_compact_yaml(BlockCodec.compress(block, depth=0, task_tier="complex"))
		parts.append(f"Full detail for selected block {ref}:\n{detail}")
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
	"query_blocks": ("Searching the page", "Searched the page"),
	"search_images": ("Searching for photos", "Searched for photos"),
	"extract_component": ("Making a reusable component", "Made a reusable component"),
	"write_page_data_script": ("Connecting the page to data", "Connected the page to data"),
	"list_doctypes": ("Looking for existing data", "Looked for existing data"),
	"run_python": ("Looking up site data", "Looked up site data"),
	"read_url": ("Reading a web page", "Read a web page"),
	"research": ("Researching online", "Researched online"),
	"get_page_scripts": ("Reading the page scripts", "Read the page scripts"),
	"set_page_settings": ("Updating page settings", "Updated page settings"),
	"remember": ("Saving a note for next time", "Saved a note for next time"),
	"seed_sample_data": ("Adding sample records", "Added sample records"),
	"create_doctype": ("Creating a place to store data", "Created a place to store data"),
	"connect_form": ("Connecting the form", "Connected the form"),
	"edit_global_settings": ("Updating site settings", "Updated site settings"),
	"set_home_page": ("Setting the home page", "Set the home page"),
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
	if tool_name == "read_block":
		return f"{voice('Reading', 'Read')} block: {resolved_label(args.get('block_id'))}".rstrip(": ")
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
	if tool_name == "create_component":
		return f"{voice('Creating', 'Created')} component: {args.get('name') or ''}".strip()
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
		self.registry = registry or build_default_registry()
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
		# read_page calls this turn — same idea, a reference sweep can't run up context.
		self.page_read_count = 0
		# Web tools this turn — bounded like every other read that costs context/latency.
		self.web_read_count = 0
		self.research_count = 0
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
		# Set once the no-op-claim guard has spent its single corrective round this turn.
		self.noop_corrected = False
		# Set once the incomplete-build guard has fired (foundation minted but page
		# left empty because generate_page was never called).
		self.build_correction_used = False
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
		# Client ops a server tool queued mid-call (extract_component rewriting the
		# page). Drained right after the handler returns — see drain_queued_ops.
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

	def build_open_page_context(self) -> str:
		"""The one fact the agent cannot discover for itself: WHICH page the user has
		open. Everything else about the site is pulled on demand (run_python, read_page,
		query_records) — nothing is pre-baked into the context."""
		if not self.page_id:
			return ""
		row = frappe.db.get_value(
			"Builder Page", self.page_id, ["page_title", "route", "published"], as_dict=True
		)
		if not row:
			return ""
		state = "published" if row.published else "draft"
		route = "/" + (row.route or "").lstrip("/")
		return f"Open page: '{row.page_title or self.page_id}' — id {self.page_id}, route {route}, {state}."

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

		# The page structure. It's resent on every round of a multi-round turn, so a
		# cache marker on the prompt right after it cuts both latency and input cost
		# across the loop.
		blocks = [self.build_open_page_context(), self.build_page_context(), self.build_memory_context()]
		context = "\n\n".join(block for block in blocks if block)
		if context:
			messages.append({"role": "user", "content": context})
			messages.append({"role": "assistant", "content": "Understood. I have the current context."})

		user_text = self.prompt
		if self.selected_block_ids:
			user_text += "\n\n" + self.attached_blocks_note()
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
			self.registry.schemas(),
			llm.TASK_PARAMS["agent"],
			api_key=self.api_key,
			stream=True,
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
		token = locks.acquire(key, locks.PAGE_LOCK_TTL)
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
			"current styles first (page context or read_block). Touch other blocks only when "
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

	def run_handler(self, tool, op: dict) -> str:
		"""Run a server tool's handler, turning a crash into a tool result.

		An unguarded handler takes the whole turn down: the exception unwinds to
		run_turn, which can only apologise and abandon everything else the turn was
		going to do. Seen live from a duplicate token id and from an image URL the
		provider could not fetch. Reported as FAILED instead, which the tools already
		use for expected failures, so the model can adjust and carry on. The savepoint
		keeps a half-applied write from riding along."""
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
			# Generation is a STEP of the turn: the generator streams YAML live (the
			# canvas preview), persists the page, and the loop continues — so the model
			# can add scripts, verify, and refine in the same turn.
			content, ops = self.run_generation_step(tool, op)
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
		called tools without saying anything. Emitted even when there is nothing to
		show — that is what tells the client to drop what it has been streaming (a
		round whose text turned out to be leaked tool syntax)."""
		note = (text or "").strip()
		if looks_like_tool_syntax(note):
			note = ""
		if not note and applied:
			note = self.describe_operations(applied)
		self.live_text = ""
		self.add_step("text", status="done", text=note)

	def correction_for(self, summary_text: str) -> str | None:
		"""A no-tool round that should have been a tool call gets EXACTLY ONE
		corrective round. Three shapes: card markup written as plain text (mimicking
		the persisted replay format — renders no controls), a multi-option question
		asked as prose bullets (same dead end, no markup to match), and a summary
		that CLAIMS an edit when nothing was applied this turn (hallucinated
		success)."""
		# Incomplete build: the model minted the design system (tokens/scripts) but
		# never called generate_page, so the page is still empty. Its own dedicated
		# one-shot correction, independent of the no-op guard (this turn DID mutate).
		if not self.build_correction_used and self.build_incomplete():
			self.build_correction_used = True
			self.stop_reason = "build_retry"
			logger.warning(
				"Incomplete build corrected: foundation set but page still empty (no generate_page)"
			)
			return BUILD_INCOMPLETE_CORRECTION
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

	def build_incomplete(self) -> bool:
		"""True when this turn laid the FOUNDATION (minted design tokens) but never
		called generate_page, leaving the page empty — the model stopped mid-build.
		Only meaningful on a page turn; the fix is one more round that generates."""
		if not self.page_id:
			return False
		root = self.page_root()
		if root and (root.get("children") or []):
			return False  # the page has content — build reached the layout
		tools_called = {t.get("name") for entry in self.trace for t in entry.get("tools") or []}
		return "set_design_token" in tools_called and "generate_page" not in tools_called

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
		self.emit("complete", message=msg, after_commit=True)

	def fail_turn(self, message: str) -> None:
		"""End the turn with a persisted error message + error event."""
		AISession.try_append_message(
			self.session_id, "assistant", message, message_type="status", metadata={"status": "error"}
		)
		self.emit("error", message=message, after_commit=True)

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
				self.flush_pending_images(messages)
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
			# Show a generic message to the user — raw provider/exception strings can
			# leak internals (keys, model ids, stack detail). Full error is logged above.
			self.fail_turn("Something went wrong while building your changes. Please try again.")
			return

		self.finish_turn(summary_text, started)

	def checkpoint(self) -> None:
		"""Make this round's work durable. A turn runs as a background job, and a job
		that raises rolls the WHOLE transaction back (background_jobs.execute_job) —
		without this, a provider timeout in round 7 would discard the pages, scripts
		and messages written in rounds 1-6. It is also what lets the editor and the
		chat, both separate requests, see a long turn progress instead of nothing
		until it ends. One commit per round: individual tools never commit."""
		frappe.db.commit()  # nosemgrep

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
		if not summary_text:
			if generated:
				# Skip a summary call after generation (the YAML arg would bloat its
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
				"rounds": len(self.trace),
				"noopCorrected": self.noop_corrected,
				"argsRepaired": self.args_repaired,
				"textToolsSalvaged": self.text_tools_salvaged,
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
		if tool and tool.handler:
			return tool.handler(self, op["args"])
		return None

	def run_generation_step(self, tool, op: dict) -> tuple[str, list[dict]]:
		"""Run generate_page as one STEP of the turn. The generator persists the page
		server-side; point the working tree at the result so the model can read back —
		and build on — what it just made (scripts, surgical fixes, one verify pass)."""
		if not self.page_id:
			return ("FAILED: no page is open.", [])
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
	AgentRunner(prompt, model, api_key, **kwargs).run()
