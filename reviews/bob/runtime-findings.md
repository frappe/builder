# Bob backend: critical experimental review

Reviewed `/home/t3run/builder`, branch `develop`, commit `a112a3e6aea1f9e712c75cdb9aeb713009467a90`, on 2026-11-01.

**Main judgment:** Bob already has useful building primitives and several good reliability fixes. Its largest quality problem is the mismatch between what the model is asked to guarantee and what the runtime preserves, validates, and measures. The system spends about **21.7k text tokens of static instructions and tool definitions per coordinator call**, forgets the original brief after roughly five ordinary exchanges, can apply incomplete model output, and verifies viewport-dependent layouts at the wrong viewport height. More prompt instructions or a stronger default model will not repair these failures.

The most promising direction is a small, durable execution kernel with a persistent design brief, bounded context, validated page artifacts, and browser verification. Keep the editable Builder tree and the single writer. Do not start by replacing the system with a swarm of autonomous agents.

## Scope and experimental limits

- Read application source and tests; did not change application code, branch, or tracked files. The checkout already had a dirty `frappe-ui` submodule and untracked `.scratch/` and `CONTEXT.md`; these were not used or modified.
- Did not initialize a Frappe site, query the real application database, inspect credentials/configuration values, or make model calls. Test data and credential-shaped strings were synthetic.
- Experiments imported the checked-out implementation under Python 3.14.7 from `/home/t3run/frappe-bench/env/bin/python`, disabled bytecode writes, replaced the Frappe logger and database with local stubs, and blocked socket connections. Tokenizer vocabularies were already locally available.
- Ran **109 existing tests, all passing**, from eight reviewed modules. Some otherwise pure tests inherit `FrappeTestCase`; the harness replaced that base with `unittest.TestCase` to avoid site/database setup. This is an offline subset, **not** a successful full bench integration run.
- Static inventory: **26 `builder/ai/test_*.py` files, 264 test methods**. None of those files directly exercise `run_turn(...)` or `stream_tool_round(...)`. This observation is limited to that directory and those direct calls, not a claim that no indirect integration coverage exists anywhere.
- Findings below distinguish reproduced implementation failures from structural judgments. No empirical claim is made about real-model visual quality, production failure incidence, cache hit rate, latency, or billed dollars.

Reproduction files:

- `/tmp/bob-backend-experiments.py`: standalone offline harness.
- `/tmp/bob-backend-experiments.jsonl`: measured counts and probe results.

Run it without paid calls:

```bash
PYTHONDONTWRITEBYTECODE=1 /home/t3run/frappe-bench/env/bin/python /tmp/bob-backend-experiments.py
```

## What the backend actually does

1. `api.run` stores the user message and queues a 600-second job (`builder/ai/api.py:73`, `:98`, `:116`). The job resolves credentials itself, so keys are not serialized into Redis job arguments (`builder/ai/agent/loop.py:1506`).
2. The worker acquires a session lock and page lock, loads a `WorkingTree`, and captures pre-turn page state (`builder/ai/agent/loop.py:871`, `:1170`, `:1191`).
3. Each coordinator call receives the system prompt, up to ten prior message rows, current page context, all saved site memories, the new request, and all 37 tool schemas (`builder/ai/agent/loop.py:595`, `:712`; `builder/ai/agent/registry.py:78`).
4. It streams tool arguments, tolerantly parses them, applies all block operations first, then runs the other tools in sequence. It appends every tool result to the in-memory transcript and commits after each nonterminal round (`builder/ai/agent/loop.py:783`, `:1225`, `:1239`, `:1267`).
5. `generate_page` makes a separate call on the **same selected model**, with a different prompt, a model-written brief, prior session messages, and selected reference/image context. It streams YAML, parses it, and replaces draft blocks (`builder/ai/agent/artifact.py:219`). Comments describing a fast coordinator and heavy generator are obsolete; `loop_model = self.model` is explicit (`builder/ai/agent/loop.py:1201`).
6. The coordinator gets the generated page back as a large tool result, adds scripts or edits, optionally takes screenshots, then stores the final summary and successful-turn debug metadata (`builder/ai/agent/loop.py:1431`, `:1276`).

## Static token overhead, measured carefully

These are **BPE counts of source-derived text**, using `tiktoken`'s `cl100k_base` and `o200k_base`. Tools are serialized as compact JSON using `ensure_ascii=False, separators=(',', ':')`. The agent prompt is the fully expanded `Prompts.AGENT_SYSTEM`, not its unexpanded template. Its inserted voice/style/memory rules are already included in its total.

These are not exact provider input-token bills. APIs internally represent function schemas differently; message framing, provider wrappers, images, user input, page data, history, tool results, reasoning, and output are excluded. Neither encoding is an authoritative Claude tokenizer. The two encodings are useful sensitivity checks, not an error bound on every model.

| Payload | Characters | `cl100k_base` | `o200k_base` |
|---|---:|---:|---:|
| Expanded agent system prompt | 49,720 | 11,044 | 10,971 |
| All 37 tool schemas, compact JSON | 47,030 | 10,711 | 10,748 |
| Agent static subtotal, sum of rows | 96,750 | **21,755** | **21,719** |
| Generation system prompt, separate call | 22,385 | 5,606 | 5,679 |
| Nine existing edit/inspection/UI schemas only | 17,583 | 3,987 | 4,021 |

The nine-tool comparison contains `read_block`, `query_blocks`, `update_block`, `update_blocks`, `add_block`, `remove_block`, `move_block`, `present_ui`, and `preview_page`. It demonstrates **62.6% less tool-schema text** under `o200k_base`, or **31.0% less total static agent text**, without shortening any descriptions. It is an illustrative task-specific subset, not a sufficient catalog for every request. A staged tool loader must retain a way to discover additional capabilities.

Largest schema contributors under `o200k_base`: `write_plugin` 1,654 tokens; `update_block` 869; `add_block` 851; `present_ui` 804; `update_blocks` 575. A request to change a heading currently carries the editor-plugin authoring manual as well as data-schema creation, web research, forms, and site settings.

Within the agent prompt, voice is 824 tokens, style rules 1,211, AI-tell guidance 401, and memory rules 158. Those are **subsets**, not additional overhead. Most prompt weight is the workflow and detailed behavior instructions; deleting just the personality paragraph will not solve this.

For scale, five coordinator calls plus one generator call repeat about **114,274 static text tokens** under the same accounting. Forty coordinator rounds repeat about **868,760** before any dynamic content or generation calls. Those are aggregate input presentations, **not uncached billed tokens**. Provider caches can make repetition cheaper; they do not remove it from the model's context window or eliminate cache-read charges.

There is no useful dollar estimate from this checkout alone: the tally omits calls, failures, and cache writes, and the runtime catalog does not retain pricing. Report measured provider usage and configured price snapshots before claiming savings in dollars.

## Prioritized concrete findings

Priority convention: P1 means fix before trusting broad rollout or using quality/cost comparisons to steer the product. P2 means a substantial quality, efficiency, or UX issue. P3 means a useful incremental improvement. Priorities are review judgments, not measured production frequencies.

### F1 — P1: `get_document` bypasses record and field-level read permissions

**Evidence:** `builder/ai/agent/tools/data.py:79–122` checks `frappe.has_permission(dt, 'read')` at the DocType level, then fetches an arbitrary named document and serializes `doc.as_dict()`. It never calls `doc.check_permission('read')` or applies field-level read permissions. In contrast, the general Python tool does both at `builder/ai/agent/tools/python.py:113–119`.

**Reproduced:** a synthetic DocType-level authorization succeeded while the fetched synthetic document's `check_permission` was configured to reject the read. `get_document` returned its synthetic restricted field, with both document and field permission checks uncalled.

**Impact:** a role allowed to read some records can ask Bob to retrieve another user's restricted record or fields. The output is then sent into model context and, on LiteLLM routes, logged with the full transcript. This is a source-level access-control failure, not an assertion that any real private record was accessed during this review.

**Fix:** share a permission-aware reader between `get_document` and `run_python`; apply document and field-level permissions before selection/truncation. Add an owner-only record test and a field-permission test. Audit the other generic readers using the same contract.

### F2 — P1: output truncation is repaired into executable mutations

**Evidence:** `builder/ai/agent/loop.py:783–821` parses arguments with `loads_tolerant`; the repair helper explicitly repairs truncated JSON (`builder/ai/llm.py:84–104`). `finish_reason == 'length'` only logs a warning at `builder/ai/agent/loop.py:824–828`. The returned operations are executed normally at `:1227–1244`.

**Reproduced with the real stream assembler:**

```text
Input tool arguments: {"block_id":"headline","inner_text":"Only half
Finish reason: length
Returned operation: update_block(block_id="headline", inner_text="Only half")
args_repaired: 1
```

**Impact:** a cut-off translation, script, bulk patch, or destructive replacement can be committed as if it were complete. Repairing punctuation in a complete value is materially different from inventing the end of an unfinished command, but the runtime does not distinguish them.

**Fix:** reject mutating calls from incomplete streams before executing any command; carry structured parse/completion status; validate parameters against the tool's schema. A bounded continuation/reissue may recover the intended operation. Preserve a visible failed attempt and its usage rather than silently accepting the prefix.

### F3 — P1: artifact parsing can overwrite a page with an empty or degraded tree

**Evidence:** YAML salvage drops parser-error lines (`builder/ai/page_writer.py:432–469`); `expand_page_yaml` requires only a mapping with `el` (`:490–505`); `persist_page` saves any resulting block (`:530–545`). Generation quality logging warns on zero sections but does not gate persistence (`builder/ai/agent/artifact.py:166–197`, `:320–327`). The coordinator says “Page generated and saved” whenever any ops return (`builder/ai/agent/loop.py:1441–1450`).

**Reproduced:**

```text
el: div
c:
```

is accepted as a root with no children. A heading `text: unescaped: colon` is deleted during salvage; the output is accepted with an empty `h1` and its following paragraph. Neither result communicates a structured “partial/degraded” status to the coordinator.

**Impact:** cancellation, output limits, or ordinary YAML slips can replace an existing design with incomplete work. A model may inspect and repair it later, but there is no dependable commit boundary ensuring that happens.

**Fix:** compile to a candidate artifact first. Return diagnostics including dropped lines, missing sections, invalid nodes, unresolved bindings, and completeness. Require a meaningful validated artifact before replacing an existing page. Keep recoverable partial output as a resumable draft artifact, with an explicit partial status; do not label it successful generation.

### F4 — P1: the repeater data writer generates invalid Python and loses wrapper data

**Evidence:** `builder/ai/page_writer.py:423–426` interpolates `json.dumps(items)` directly into Python source. JSON `true`, `false`, and `null` are not Python literals. `expand_page_yaml` unwraps the root for block conversion at `:498`, but builds the data script from the original `parsed` wrapper at `:504`. `collect_repeater_data` only traverses `repeat` and `c`, not `page/root/body` wrappers (`:407–420`).

**Reproduced:**

```text
items: [{title: A, live: true, optional: null}]
→ data.products = [{"title":"A","live":true,"optional":null}]
→ NameError: name 'true' is not defined
```

A valid `page: {el: div, repeat: ...}` wrapper produces a bound repeater but an **empty data script**. Both failures are accepted as successful expansion.

There is another integration hazard: any generated repeater shim replaces the entire existing `page_data_script` (`builder/ai/page_writer.py:537–539`), including data setup performed earlier in the same build. The prompt explicitly asks for data setup before generation (`builder/ai/prompts.py:130–131`).

**Impact:** empty repeated content or a failing page render, plus loss of existing dynamic data behavior.

**Fix:** keep static repeater data as structured data instead of source, or emit validated Python literals through one renderer. Traverse the normalized root, normalize data keys consistently, and merge through an explicit generated-data namespace rather than replacing arbitrary user code. Tests must execute the shim, including booleans/null and wrapped/nested repeaters. The current shim test checks a numeric-only string (`builder/ai/test_page_writer.py:93–104`).

### F5 — P1: broad reads can exceed a model's context in one tool result

**Evidence:** there is no input budget or transcript compaction in `builder/ai/agent/loop.py:1208–1248`; results are appended verbatim. `query_blocks` returns every match's full text (`builder/ai/agent/tools/query.py:49–71`); `read_block` returns an unrestricted subtree (`:113–127`); `get_page_scripts` serializes all attached code (`builder/ai/agent/tools/scripts.py:43–51`). `query_records` allows 100 rows and caps each code field at 8,000 characters, with no total response cap (`builder/ai/agent/tools/data.py:63–76`, `:125–149`).

**Reproduced using synthetic fixtures, both tokenizers agreeing here:**

| Tool fixture | Result characters | Text tokens |
|---|---:|---:|
| `query_blocks(text_only=True)`, 100 long paragraphs | 461,712 | 83,206 |
| `query_records`, 100 rows with one capped Code field each | 841,590 | 306,102 |

The second result alone exceeds the registry's default 200,000-token context assumption (`builder/ai/models.py:28`). It is an allowed tool response, not a malformed input. These are stress fixtures, not samples of production pages.

`read_page` permits three references, each with up to 120,000 characters of full structure before scripts/components are appended (`builder/ai/agent/tools/query.py:155`, `:204`, `:240–251`). Its comment calls this a “ONE-TIME tool result” (`:236`), but the loop resends it on every later round. A selected subtree can also bypass the 45,000-character page threshold via `render_skeleton_context` (`builder/ai/agent/loop.py:206–219`).

**Impact:** expensive context growth, output-budget starvation, context-limit failures, and re-reading loops. Starting `/new`, as the context-error message suggests, does not fix a single oversized read or oversized current page (`builder/ai/llm.py:57`).

**Fix:** total token budgets per call and per tool result; paginated/ranged reads with artifact handles; bounded text projections for selectors; explicit batch ranges for translations. Preserve exact complete coverage through cursors, not silent truncation. Reserve output and reasoning budget before choosing what to include.

### F6 — P1: failures, cancellations, and question cards drop accounting and rollback metadata

**Evidence:** normal completion persists usage/debug/revert data at `builder/ai/agent/loop.py:1343–1380`. Cancellation and failure persist only their status at `:1147–1159`. Empty-response exits at `:1278–1298` also bypass that finalization. `present_ui` persists steps but no usage or revert snapshot (`builder/ai/agent/tools/conversation.py:66–80`); confirm cards keep only part of the debug object (`builder/ai/agent/pending.py:39–55`).

**Reproduced:** a runner with 12,345 accumulated prompt tokens, an applied operation, and an existing revert snapshot emitted only `{"status":"error"}` or `{"status":"cancelled"}` in its persisted assistant metadata. The snapshot link is what the UI uses to offer Revert (`frontend/src/components/AIChatController.ts:947–950`).

The snapshot itself does not cover all writes: `write_page_data_script` and `attach_page_script` are absent from `SNAPSHOT_TOOLS` (`builder/ai/agent/loop.py:80–92`), despite captured state containing data and script links (`builder/ai/snapshots.py:31–46`). A turn doing only one of those operations does not create the expected AI revert snapshot. Page settings and token/component mutations have still wider undo semantics.

**Impact:** the most expensive/unsuccessful turns disappear from usage analysis, and users lose the convenient rollback control exactly when partial changes need it. A generation ending in a form confirmation can lose its generation usage from the persisted record.

**Fix:** persist one durable turn/run record, finalized on **every** exit path, with usage, attempts, tool outcomes, partial state, and rollback references. Link all assistant cards/status messages to it. Put effects and snapshot scope on tool metadata instead of maintaining an incomplete name set.

### F7 — P1: visual verification uses an 8,000px viewport, not a normal viewport with a full-page capture

**Evidence:** `CAPTURE_HEIGHT = 8000`; `render_page_image` passes that as the renderer height (`builder/ai/agent/tools/preview.py:26–43`). The Builder renderer forwards it to Frappe (`builder/html_preview_image.py:12–22`). The installed framework explicitly applies it as device metrics: `/home/t3run/frappe-bench/apps/frappe/frappe/utils/preview.py:71–74`. This framework citation is environmental evidence, not part of commit `a112a3e6`.

**Reproduced call boundary:** desktop preview requested `{width:1280, height:8000}`. By CSS viewport-unit semantics, `100vh` is therefore 8,000px. The review attaches at most three 2,000px tiles, or 6,000px (`builder/ai/agent/tools/preview.py:35–36`, `:67–84`). A full-height hero can consume the entire reviewed region before any following section appears. The generation prompt itself recommends `100vh` and other `vh` layouts (`builder/ai/prompts.py:186`, `:190`, `:206`). This geometric conclusion is derived from the actual device-metrics call; no live browser screenshot was taken in this review.

**Impact:** Bob can “fix” a layout that is correct at a real screen size, miss the rest of a page, and evaluate the wrong sticky/viewport behavior. Mobile is especially distorted at 390×8,000.

Also, the two-preview limit is shared between reference study and output verification (`builder/ai/agent/tools/preview.py:124–136`). Two reference screenshots leave no verification for the actual build. Two images cannot cover desktop/mobile × light/dark plus interaction states. The generation tool result still says “preview_page at most once” (`builder/ai/agent/loop.py:1446–1448`), contradicting the system's permitted second verification (`builder/ai/prompts.py:104`, `:135`).

**Fix:** render at realistic viewport dimensions; capture document extent without changing viewport metrics, or scroll through fixed-size captures. Separate reference-image and verification budgets. Choose required states from actual changes, and explicitly record coverage/unverified states. Motion quality needs interaction/timeline sampling, not a single static bitmap.

### F8 — P1/P2: cancellation is not tied to a durable run and can be erased

**Evidence:** `AgentRunner.run` clears the cancel flag **before** trying to acquire the session lock (`builder/ai/agent/loop.py:1161–1179`). The API only checks whether a worker currently owns that lock; admission and enqueue are not atomic (`builder/ai/api.py:73–78`, `:116–130`). `cancel` reports no active run when the session lock is absent (`:226–237`).

**Reproduced:** a worker rejected because `AISession.start_run` returned `None` still called `clear_cancel_flag` once. Thus a duplicate job can erase another active job's stop request.

**Reproducible sequence from the code:** queue a turn while workers are busy; click Stop before a worker claims it; API responds `not_running`; the queued worker later starts and clears the stop flag, then makes model calls. A flag keyed by session cannot distinguish stale cancellation from cancellation of this queued run.

Cancellation is checked between streamed chunks and at subsequent round boundaries (`builder/ai/agent/loop.py:737–743`, `:1215`), not before each tool mutation. A large tool batch can keep writing after Stop. A stalled stream can wait up to the 120-second timeout (`builder/ai/llm.py:305`), while the frontend's cancellation watchdog resets its local UI after 20 seconds (`frontend/src/components/AIChatController.ts:847–850`).

**Fix:** create a run ID and queued state atomically at admission; cancel that run ID; check it before the first call, each command, and each retry; never clear someone else's cancellation on lock failure. Expose queued/running/cancelling/partial/completed states durably. Use transport cancellation or short polling timeouts where supported.

### F9 — P2: session memory forgets the design brief, while generation gets a lossy subset

**Evidence:** `CONTEXT_WINDOW = 10` is documented as prior turns but is a limit on **message rows** (`builder/ai/session.py:16`, `:185–193`). Filtering transient rows happens after the limit (`:197–202`). Only role/content and special attachment/plan restoration survive; tool calls, results, and most timeline metadata do not (`:173–215`).

**Reproduced:** a 13-row synthetic conversation consisting of the original identity brief followed by six ordinary assistant/user exchanges returned ten historical messages and lost the original brief. It retained roughly five exchanges, not ten turns. Error/status/card rows can shorten meaningful memory further.

The generator does not inherit the coordinator's transcript. It gets prior stored rows, a brief, found photos, and selected reference geometry (`builder/ai/agent/artifact.py:232–270`). The current user message is excluded from historical replay; the current exact request, saved memory block, current page, and most current tool evidence reach the generator only if the coordinator repeats them correctly in `brief`.

**Reproduced generation capture:** on a first turn, messages were `[system, user(brief)]`; the exact current user wording was absent. No saved-memory block is independently loaded on this path. This delegation boundary is intentional, but there is no structured contract checking that the brief preserves required facts.

Saved memory is all-site, unscoped, oldest-first, up to 50×500 characters (`builder/ai/agent/tools/memory.py:12–26`, `:50–61`). That is useful for shared brand facts but can mix personal preferences or different client/brand work and consumes context even when irrelevant.

**Impact:** repeated questions, forgetting why decisions were made, inconsistent copy across revisions, and expensive rediscovery. The behavior will appear “dumb” even with a capable model because the required information is not present.

**Fix:** durable structured `DesignBrief`/decision state: identity, audience, conversion goal, exact supplied facts, selected reference IDs, copy requirements, palette roles, typography, accessibility and motion preferences, outstanding questions, completed operations. Store provenance and distinguish fixed user choices from model suggestions. Scope memories by site/brand/user/page and retrieve relevant ones. Feed this canonical brief to both coordinator and generator.

### F10 — P2: confirmation resume silently switches back to the session's original model

**Evidence:** session creation saves `selected_model` (`builder/ai/session.py:49–58`). An explicit later `api.run(..., model=...)` uses the new selection but never updates that session field (`builder/ai/api.py:84–130`). `resume_after_action` reads the stale field (`:189–202`). The frontend picker stores its selection in local storage and sends it on ordinary turns (`frontend/src/components/AIChatController.ts:73`, `:908`).

**Reproduced with mocked queue and DB:** an ordinary turn enqueued `model-selected-now`; confirming its pending action enqueued `model-original`.

**Impact:** design or reasoning quality changes halfway through a task, contradicting the explicit policy of preserving the user's selected model. It can also route to an unavailable/disabled original selection.

**Fix:** persist the resolved provider/model/options on each run and pending action; resume that exact run selection. A removed selection should yield an explicit recoverable error, not a silent arbitrary fallback. `ModelRegistry.get_default` currently substitutes the first catalog entry for any unknown selection (`builder/ai/models.py:376–383`).

### F11 — P2: “parallel tool calls” are sequential, reorder writes, and drop calls after a terminal tool

**Evidence:** the prompt asks for parallel independent calls (`builder/ai/prompts.py:64`, `:129`). Actual execution applies all client ops first, then calls the remaining handlers one by one (`builder/ai/agent/loop.py:1225–1244`). A successful terminal tool immediately breaks the loop and returns, dropping later calls in that batch (`:1241–1246`).

**Reproduced:** a synthetic terminal `pause` followed by an independent server `later` executed the first and never invoked the second. This is not a recommendation to execute writes after user confirmation is required: the problem is that pending work is discarded rather than explicitly deferred and persisted.

**Impact:** batched photo searches and independent reads still incur summed network latency; ordering can differ from the returned call order; multi-action proposals require model reconstruction after resume. Prompt-level batching saves inference round trips, but it is not actual parallel tool execution.

**Fix:** explicit tool effect metadata and a batch scheduler. Run only safe independent reads concurrently, with cancellation and bounded concurrency; serialize dependent writes in declared order. Terminal output should pause a recorded work queue, not erase it. Keep one page writer.

The same name-list approach misclassifies `search_images` as a mutation because it is absent from `READ_ONLY_SERVER_TOOLS` (`builder/ai/agent/loop.py:123–140`, `:1108`). A probe returning “No images found” increments `server_mutations` to one. If the model then returns no text, the fallback can say “Done. The steps above were applied” (`:1283–1287`). Typed results/effects would eliminate this class of misleading summary.

### F12 — P2: Lucide compression hides editing handles and behavior hooks

**Evidence:** the icon special case returns early with only `icon`, optional `name`, and base style (`builder/ai/block_codec.py:54–69`). It loses `ref`, classes, attributes, mobile/tablet overrides, bindings, and component context that the normal path preserves. `read_block` uses this same compression despite promising full detail (`builder/ai/agent/tools/query.py:121–122`).

**Reproduced:** an icon with ID `icon-edit-me`, class `motion-hook`, HTML ID `next`, tooltip/title, and `mobileStyles.display='none'` compressed to:

```json
{"icon":"arrow-right","name":"Arrow","style":{"color":"red"}}
```

**Impact:** Bob cannot reliably identify an icon's current responsive state or interaction hooks from page context or even its “full” read. Additional selector calls recover its ref/classes but not all omitted state. The existing collapse test explicitly expects the stripped shape (`builder/ai/test_block_codec.py:44–52`).

**Fix:** retain normal block metadata; replace only the bulky SVG payload and redundant icon defaults. Add a round-trip invariant covering handles, responsive state, and hooks, not just icon appearance.

## Accounting, routing, caching, and operational bottlenecks

### Usage is a partial success counter, not a cost ledger

`record_usage` increments `calls` only when a chunk carries usage, ignores its model argument, and records no call ID, phase, finish state, cache-write tokens, reasoning breakdown, provider price, or cost (`builder/ai/agent/loop.py:520–537`). This makes a usage-bearing chunk count stand in for request count. Missing provider usage is indistinguishable from zero cost; partial failed streams commonly have no final usage chunk.

Two other paid paths are absent from the ledger:

- `research` calls the same routed model's `:online` variant through a nonstreaming plain completion, with `params={}` and no explicit output cap (`builder/ai/agent/tools/web.py:111–131`). The 6,000-character cap is applied **after** generation, so it does not cap provider work or cost.
- Session title generation uses the selected model and a nonstreaming completion, after final timing/debug data has already been assembled (`builder/ai/agent/loop.py:1326`, `:1381–1419`). `llm.complete(stream=False)` discards usage and returns only text (`builder/ai/llm.py:270–273`). The final complete event waits for this title attempt; the requested 24 output tokens do not guarantee short latency on every route, especially since the Codex adapter intentionally ignores output-token knobs (`builder/ai/codex.py:60–69`).

`models.py` claims it merges pricing (`builder/ai/models.py:9–12`), but its OpenRouter metadata fetch stores only context length and vision (`:45–55`). No dollar cost is calculated by the loop. The frontend's context meter is simply the last recorded call's prompt size (`frontend/src/components/AIDebugPanel.vue:212–220`), without phase or output reserve.

**Recommendation:** put a `UsageLedger` at the adapter boundary, recording request start, attempt, completion/failure/cancellation, phase, provider/model/options, input/output/cache-read/cache-write/reasoning usage when available, and explicit `unknown` fields. Store provider request IDs for reconciliation. Title and research calls must use the same interface. Show measured cost separately from estimates and include price-version provenance. Finalize the turn before doing an optional background title.

### Retry behavior is inconsistent between conversation and page generation

- Coordinator rounds retry transient failures up to three attempts with 1s/2s backoff (`builder/ai/agent/loop.py:674–698`); the LiteLLM call also sets `num_retries=1` (`builder/ai/llm.py:304`). The layers can multiply connection-level attempts; “three attempts” is not necessarily three underlying provider requests.
- Artifact generation has no corresponding retry/resume wrapper (`builder/ai/agent/artifact.py:277–327`). A synthetic stream yielding a valid paid-for YAML prefix then raising `ConnectionError` deleted the stream buffer and never invoked `persist_page`. Cancellation deliberately salvages a partial artifact, but a transport interruption does not. Any frontend autosave of its preview would be incidental, not authoritative recovery.
- The Codex SSE path does not require a terminal event. `stream_chunks` ends normally on transport EOF even if `assembler.finished` is false (`builder/ai/codex.py:111–118`). A synthetic stream with one text delta and no `response.completed` returned “Partial page”, `finish_reason=None`, and no error. That prevents the coordinator retry logic from distinguishing a dropped response from success.
- Credential resolution is outside the runner's failure finalization (`builder/ai/agent/loop.py:1506–1509`); a queued job whose credential disappears can fail before any persisted assistant error or completion event.

**Recommendation:** one request/attempt policy with an overall time/token budget, explicit completed/partial transport states, provider retry guidance where available, and cancellation between attempts. Persist partial artifacts for resume, but never execute incomplete tool arguments. Record all attempts, including those without final usage.

### Cache machinery is worth keeping, but its claims need measurement

The code correctly places Claude markers in content blocks and pins the OpenRouter Anthropic route (`builder/ai/llm.py:121–145`). The coordinator derives a capped set of system/history/turn/mid-turn markers (`builder/ai/agent/loop.py:643–670`). Byte-stable prefixes are the right idea.

However:

1. Once the ten-message replay window slides, its first historical message changes. A synthetic comparison of two full windows found only the system message shared at the start. The tool prefix can still cache; historical-prefix reuse is impaired. Do not generalize comments about an earlier rewrite's ~90% cache reads (`builder/ai/agent/loop.py:142–148`) into a current measured guarantee.
2. Current page context, user context, and later tool results remain in each request. Cache hits reduce compute/billing according to provider policy; they do not shrink context. The memory comment “costs nothing per-round” is too strong (`builder/ai/agent/loop.py:588–590`).
3. Every generator call marks the system prompt for a one-hour cache write (`builder/ai/agent/artifact.py:232–239`), but there is no measured reuse/cost policy per model/site/workload. A short-lived single-page session may not amortize a premium write.
4. Model lookup attempts the OpenRouter public catalog even for another provider (`builder/ai/models.py:301–314`, `:343–348`). Successful fetches are Redis-cached; failures fall back without an explicit negative cache, so repeated `find` calls can repeatedly hit an unavailable external service. Offline/local gateway work should not depend on this for its hot path.

**Recommendation:** stable versioned prefix groups, recent exact transcript plus a durable older summary, provider-supported caching descriptors, and telemetry by prompt/toolpack version. Measure cache reads **and writes**, cold/warm behavior, first-turn overhead, and end-to-end cost. Avoid switching toolpacks mid-turn without accounting for cache invalidation.

### Routing preserves the selected model, but lacks a real capability contract

Keeping the user's selected design model is a strength. Gateway discovery filters some nonchat model names and supports custom providers; catalog/discovery paths also have tool-call filters (`builder/ai/catalog.py:58–67`, `builder/ai/discovery.py:213–219`). But the runtime model record used by the loop retains only vision/context and route information (`builder/ai/models.py:105–115`), not maximum output, supported reasoning options, schema restrictions, or tool support.

All coordinator calls request 16,000 output tokens/high reasoning and all generation calls 40,000/high reasoning (`builder/ai/llm.py:108–117`). `litellm.drop_params = True` and provider-name substring checks handle incompatibilities (`:16`, `:148–156`). The Codex route intentionally treats those budgets differently. For a 32k-window route, the measured ~21.7k static text plus a 16k requested reserve already illustrates the incompatibility before a page is included; the exact rejection/normalization depends on the provider.

**Recommendation:** persist a `ModelCapabilities` object and resolve a task policy once per run. Keep the user's chosen model as the design owner; let inexpensive deterministic validation and optional explicitly configured specialists do supporting work. Clamp output reserve to actual context and task needs; report unsupported options rather than silently assuming equivalent behavior across routes.

### Full transcript logging is expensive and overbroad

Both LiteLLM completion paths log every message's content at INFO (`builder/ai/llm.py:249–252`, `:294–297`). Images stored as data URLs and large tool results are printed again on every subsequent call. A 3MiB source image becomes about 4MiB of base64; replaying even a few attachments can create large repeated log records. This is a byte/I/O observation, not an image-token estimate.

There is no reason for routine performance telemetry to require raw business copy, document contents, or full image bytes. Use sizes, hashes, call IDs, tool summaries, and structured usage; make tightly scoped, redacted payload tracing an explicit diagnostic mode.

## Design quality, motion, and separation of concerns

### The motion-quality ceiling is verification, not just model intelligence

Bob can author native blocks, CSS/JavaScript page scripts, component scripts/props, and class hooks. That is enough to make many polished animated sites without a framework rewrite. The code also correctly warns that screenshots cannot verify interactions (`builder/ai/prompts.py:66`, `:103`; `builder/ai/agent/tools/preview.py:201`).

But its own verification stops there. There are no agent tools for clicking, scrolling, inspecting computed styles, collecting console errors, testing focus, or sampling animation progress. `validate_script` only rejects a few style-injection strings and otherwise accepts code (`builder/ai/agent/tree.py:278–289`). Unlike plugin writing, page-script writing does not perform even a syntax check. The class-contract checker is a regex over a subset of selectors, called after generation (`builder/ai/agent/loop.py:1454–1503`); scripts normally written afterward are not automatically checked at that boundary. It is a useful hint, not a behavioral contract.

The still-by-default policy (`builder/ai/prompts.py:121`, `:132`) is a deliberate UX choice, not an implementation bug. For the requested motion-design-quality work, however, Bob needs an explicit motion brief and an execution path that proves the requested experience: entry states, scroll states, hover/click feedback, keyboard access, reduced-motion behavior, and mobile performance. Asking the user to manually confirm every behavior leaves capability incomplete.

The single-page scope is also explicit (`builder/ai/prompts.py:69`). Shared components make site consistency possible, but Bob cannot complete a multi-page personalized site autonomously through this public toolset. Treat that as a product boundary to change deliberately; do not claim the existing system is a full-site agent.

### Prompt quality has improved through many local fixes, but now encodes too much policy and implementation

Strengths include exact user color roles, avoiding fabricated proof, research for real-world facts, studying the actual reference site, preserving semantic editable blocks, batching, and self-review. These are sensible requirements.

Problems:

- Long repeated instructions substitute for typed state: component contracts, class contracts, data keys, approved image URLs, immutable user colors, and allowed edits should be represented structurally.
- Some guidance conflicts. The agent result requests one preview while the system allows two. Global anti-tell guidance warns about an eyebrow over every section, while certain layout recipes prescribe repeated tiny uppercase labels. “Every brand colour as a token” and an unconditional rgba black/white text hierarchy can pull in different directions (`builder/ai/prompts.py:158`, `:172–176`). These are pressures to resolve with reference/design state, not necessarily universally wrong aesthetic choices.
- The caption rule `rgba(0,0,0,0.36)` on white produces approximately `#A3A3A3`, about **2.5:1 contrast** under the standard sRGB luminance formula: below 4.5:1 for normal text, and below 3:1 for large text. This default undermines the stated “unreadable contrast” self-review goal (`builder/ai/prompts.py:176`; `builder/ai/agent/tools/preview.py:182`).
- “Exactly one signature move,” a small menu of named layout systems, and 4–8 sections (`builder/ai/prompts.py:154`, `:183–202`) can become a different template fingerprint. They are useful scaffolds for an underspecified request, not universal quality criteria. The reference-overrides-defaults rules help, but a verifier should judge the actual brief rather than forcing every reference into 3.5× type and treated photos.

Use a short invariant core, task-specific capability documentation, and a structured brief. Keep design guidance as selectable examples and review criteria, not an ever-growing law book sent with every heading edit.

### The registry is a good seam; orchestration still knows too much

`Tool` is a clean first step (`builder/ai/agent/registry.py:32–56`). But its claim “Adding a capability = registering one Tool. The loop never changes” (`:22`) is contradicted by several name sets and tool-specific paths in the 1,509-line loop: snapshots, read/write classification, script twins, activity strings, generation messages, and class-hook analysis.

The loop owns execution, transport streaming, UI narration, cancellation, caching, persistence, rollback references, debugging, usage, titles, and part of design verification. Adding tools requires remembering hidden global invariants. `search_images` becoming a mutation and missing snapshot tools are concrete symptoms.

Strings such as `FAILED` are used as a transaction/result protocol; server failures are not consistently added to `tool_failures`, and activity steps finish as “done” regardless of a failure result (`builder/ai/agent/loop.py:1037–1041`, `:1102–1116`). The trace stores shortened input arguments and text but not a structured outcome (`:539–557`). This makes diagnosing repeated wrong attempts harder than it needs to be.

The frontend/server YAML/style conversion duplication is justified for live preview, but the contract needs differential tests. The authoritative server tree is the important invariant; frontend optimism must never silently redefine what succeeded.

## Strengths worth keeping

1. **One authoritative page writer.** The working tree applies edits before they reach the canvas; unknown refs produce useful correction feedback. Per-round checkpoints preserve earlier progress (`builder/ai/agent/loop.py:1025–1056`, `:1267–1274`). This is a much better foundation than independent browser and server writers.
2. **Batch editing primitives.** `query_blocks` plus uniform/per-block `update_blocks` avoids one expensive LLM round per element. Improve pagination and budgets without losing complete coverage.
3. **Streaming artifacts as content.** Moving full-page YAML out of tool argument buffering gives live progress. Retain that UX while adding explicit partial/completed artifact states.
4. **Deterministic normalization.** CamelCase keyword repair, units, gradients, binding normalization, and component child skeletons handle recurrent model slips at the implementation boundary rather than relying solely on prompts (`builder/ai/page_writer.py:84–142`, `:203–265`, `:373–401`).
5. **Reference-aware design.** Design digests, explicit primary reference geometry, exact photo inventories, component props, and shared scripts are valuable ingredients for personalization (`builder/ai/agent/artifact.py:113–163`; `builder/ai/agent/tools/query.py:195–233`).
6. **Bounded image/reference reads and readable screenshot tiles.** The intent is sound. Correct viewport geometry and use coverage-aware budgets rather than removing all limits.
7. **Token-fenced locks and queue hygiene.** Redis NX/TTL locks with token-checked release prevent a stale worker from deleting another worker's lock (`builder/ai/locks.py:49–63`); credential resolution inside jobs avoids queued secrets. Extend these with durable run IDs and revision checks.
8. **Explicit confirmation for privileged changes.** Pending action payloads are stored and applied from user-triggered endpoints. Retain that boundary while making resume and metadata reliable.
9. **Provider adapter and focused tests.** The consolidated LLM boundary, Codex transcript/SSE adapter, permission-aware Python sandbox, and many targeted regressions are useful. The passing 109-test subset shows there is a base to build on, even though the most important orchestration paths are under-tested.

## Ambitious but practical redesign

### 1. Make a durable run the unit of work

Create a `TurnRun` record at enqueue time: run ID, session/page, triggering message ID, resolved provider/model/options, base revision, status, pending commands, budget, usage ledger, final outcome, and rollback references. Store a small append-only event log; stream those same event IDs to the chat. Reconnect rehydrates the run, not only generation YAML or final summaries.

Use a typed `ToolResult` containing success/partial/failure, bounded summary, artifact handles, affected entities, revision, and diagnostics. Tools declare effects, permissions, read projections, snapshot scope, idempotency, and whether they can run concurrently. The executor should not infer effects from tool names or the prefix of an English string.

### 2. Separate conversational history from project state

Maintain a canonical `DesignBrief` and a revisioned `PageIndex`. Keep recent exact exchanges and a small summary of older decisions, with provenance linking back to messages. Retrieve selected/current sections and relevant memory by intent. Every page read is an artifact with a digest, version, and requested projection; only the needed slice enters the prompt.

This supports concise interactions without asking the user to repeat the brand story after five exchanges. It also makes cancellation/resume deterministic: “continue” uses pending work and verified page revision rather than guessing from the last two sentences.

### 3. Make tool selection and budgets explicit

Start with a compact core: inspect/query, patch, task discovery, and conversational response. Activate stable toolpacks for generation, scripts/motion, data/forms, or editor plugins. Load detailed plugin SDK material only for plugin tasks. Select once per task phase when practical to preserve caching.

`ContextBuilder` receives capabilities, output reserve, budget, brief, page index, recent history, and artifact references. It measures or conservatively estimates the next request before calling a provider. A broad read returns count/cursor/handle plus a bounded sample, not 300k tokens. Large translations progress by exact batches tracked outside model prose.

Keep the user's chosen model for design ownership. A smaller helper is optional for bounded classification/summarization, and its effect must be evaluated; a silent cheap-model substitution on creative edits would reverse an existing strength.

### 4. Compile page generation rather than trusting the streamed string

The generator produces sections or a structured candidate IR, with stable section IDs, content bindings, reusable components, image references, and motion hooks. Validate semantics and compile it into Builder blocks. Stream provisional previews, but commit validated chunks with explicit revisions and completeness.

Use local checks for binding targets, missing assets, invalid script syntax, unresolved classes, layout overflow, and token references. Recover one failed section instead of paying to regenerate the entire page. Reuse the current normalization functions and `WorkingTree`; replace the permissive success boundary around them.

### 5. Add a real design and motion verifier

First fix viewport dimensions. Then expose a bounded verification service that can render at standard desktop/mobile sizes, collect DOM/computed style facts, inspect console errors, scroll/click/hover/focus, and capture selected timestamps/states. It should produce evidence and a small actionable report, not another huge transcript.

For motion briefs, store an interaction contract: trigger, target, initial/final states, timing/easing, interruption behavior, reduced-motion fallback, and mobile behavior. Compile common patterns from tested primitives where appropriate; permit custom CSS/JS when needed, followed by validation. Check real class matches after scripts and markup both exist. A motion-disabled reference or accessibility preference must remain a durable constraint.

Keep the final judgment on brand fit with the chosen design model or human; deterministic checks catch objective defects cheaply. Use a small remaining critique budget for issues that need visual taste.

### 6. Measure cost per accepted outcome, not tokens per successful reply

Adapter-level `UsageLedger` records every call/attempt, including research, titles, partial streams, and retries. Track cold/warm input, cache reads/writes, output/reasoning, price snapshots, latency, and accepted changes. Compare models and prompts on completed task quality, revision count, user correction rate, and cost per accepted design.

Targets worth testing, **not promised results**: a common-edit static payload below 5k text tokens; bounded one-to-two-call surgical edits; no unaccounted request; no completed status without artifact/completion evidence; no question-card turn losing usage; and no viewport-dependent layout judged at 8,000px height.

## Suggested implementation order and acceptance tests

**First: correctness and observability.** Fix record/field authorization; reject truncated mutating calls; enforce completed SSE streams; fix repeater compilation; preserve partial generation artifacts; unify all exit-path metadata and rollback references; add run-scoped cancellation and preserve the actual selected model on resume.

Acceptance tests should use deterministic scripted streams and fake tool handlers, then a disposable Frappe test site for permission/transaction integration:

- Truncated `update_block`/`update_script` never applies partial values.
- Transport EOF without completion cannot be a successful turn.
- A failed generation retains its recoverable artifact and cannot overwrite an existing page with an empty root.
- Wrapped/nested repeaters with booleans, nulls, quotes, and non-ASCII text populate valid data without erasing an existing script.
- Every termination path carries usage/unknown-usage status, tool outcomes, partial changes, and revert references.
- Queued cancellation prevents the first paid call; duplicate workers cannot clear another run's cancel state.
- A confirmation after switching model resumes the same model/options.
- Unauthorized record and field reads are denied before serialization.

**Second: bounded context and trustworthy verification.** Fix the screenshot viewport; add a central context/result budget; paginate broad reads; preserve a canonical brief; retain icon metadata. Add transcript-budget tests and browser fixtures for `100vh`, sticky rails, long pages, mobile overflow, and required dark/light coverage.

**Third: task-specific toolpacks and motion-quality workflow.** Split tool documentation by phase, add typed effect/result metadata, and introduce actual browser interaction verification. Only then experiment with smaller specialists and prompt ablations.

For future quality experiments, use a frozen benchmark set: a tiny text edit, page-wide translation, continuation after many exchanges, a reference-matching page, a personalized business page with supplied facts, mobile/dark repair, a motion-heavy portfolio, and interruption/recovery. Blindly score brief fidelity, editability, responsive layout, typography, contrast, asset validity, interaction success, and invented facts; record all cost, latency, and correction rounds. This review made no paid calls, so it supplies the failure fixtures and measurement plan rather than inventing model rankings.

The practical opportunity is substantial: the strongest parts are already the native editing primitives and deterministic application path. Making the execution/context/verification boundaries explicit will improve both efficiency and apparent intelligence, while giving ambitious personalized and motion work a dependable foundation.
