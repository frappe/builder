# Flow session architecture review for Bob

Reviewed **frappe/flow main at `9562f406e2c246ffe80e51d27768fac50e4a17e5`**, cloned to `/tmp/bob-flow-review`, on 2026-11-01. All Flow source links below are pinned to this commit. No `AGENTS.md` was found in Flow or its applicable `/tmp` ancestors. Builder's `/home/t3run/builder/AGENTS.md` was read. Builder comparison is against checkout HEAD **`a112a3e6aea1f9e712c75cdb9aeb713009467a90`**, including the supplied `reviews/bob` findings. No Builder app files were changed; Flow's checkout remains clean.

**Recommendation: adopt Flow's dedicated async service boundary and durable event/replay contract. Do not put its in-process Agent inside another ordinary RQ job, and do not copy its storage or concurrency assumptions unchanged.** The service boundary is the part that frees Frappe workers. The event contract makes refresh, pause, recovery and compaction coherent. Bob additionally needs stable submission/run identity, effect receipts, page revision checks, persistent design state and atomic revert.

The promptly delivered [server contract](/tmp/bob-flow-server-contract.md) specifies the runtime split and admission/outbox/callback contract. This report extends it with the session, frontend and compaction comparison.

## Decisions to make while implementing

1. **Separate long model orchestration from Frappe web/RQ workers.** A supervised async runtime owns coordinator, generation, research-model, summary and title calls. Frappe handles short authenticated admission, reads and canonical mutations. Moving generation into a synchronous tool callback would preserve the worker-occupancy problem.
2. **Create the run before execution.** Persist a unique user `request_id`, stable `run_id`, queued state and input together; dispatch through a recoverable outbox. Duplicate submissions and duplicate delivery return the existing run. Cancel by run ID, including queued work. Flow's public `/run` does not implement this contract for us.
3. **Make one event journal authoritative for execution.** Typed durable events + sequence cursor feed both recovery and the UI. Keep transient text/YAML replaceable. Keep page effects and their idempotency receipts atomic in Frappe, with expected revision/run fencing. Flow's DB transcript is a projection of its daemon journal, not a second execution engine.
4. **Persist paused continuation and typed design state.** Cards/approvals are durable states; settling while waiting frees resources. Brief, chosen assets, direction and verification state must survive compaction independently of prose summaries.
5. **Replace ad hoc async UI mutation with ownership checks and a common reducer.** Every response/event must belong to the intended page/session/run/view generation. Reconnect hydrates active state and catches up from a cursor. Stable request/message IDs reconcile optimistic sends.

## 1. Runtime: what does and does not occupy workers

Flow starts a dedicated `flow serve --uds ... --profile deployed` process, either supervised or detached. The server runs async sessions with `asyncio.create_task`; its async LiteLLM adapter awaits `litellm.acompletion()` and asynchronously iterates the stream. Frappe's Unix-socket HTTP client is synchronous, but its run request returns after admission, unless a caller explicitly chooses the daemon's `wait=true` API. It does not hold the request/RQ worker for the entire model run. Evidence: [process lifecycle:189–275][lifecycle], [short client submission:26–99][daemon-client], [task creation:584–596][start-operation], [async model stream:169–189][model-stream], [optional wait:501–506][finish].

Tools are an important exception. Ordinary Frappe tools execute inside a synchronous callback request as the session owner. A tool marked for background execution enqueues on `queue="long"`, performs the effect, commits and delivers its result. The daemon's HTTP request/future wait is async; the background tool itself still occupies an RQ worker. Its `tool_waiting` preflight is a check, not an atomic cancellation fence. Evidence: [Frappe callbacks:41–72,128–169][callback], [async callback/pending-result protocol:26–67,101–112][client-tools].

**Bob comparison:** `builder/ai/api.py:116–132` already releases the web worker by queueing `run_agent_job`, but `queue="default"` then hosts a synchronous `AgentRunner` for up to 600 seconds. `loop.py:1161–1382` owns the entire model/tool orchestration. Enqueueing is useful web isolation, not nonblocking model execution. An `async def` wrapper around the existing synchronous runner would still block the daemon event loop; `asyncio.to_thread` would consume a thread per run and would require careful separation from Frappe's request/transaction state. Prefer genuine async provider drivers plus explicit RPC tool boundaries.

**Checkpoint limitation:** Flow persists semantic boundaries, not arbitrary Python execution stacks. A paused approval can be reconstructed. A crashed active task/provider stream is settled as an interrupted error on load, with missing tool results repaired. There is no transparent mid-token resume. A callback that committed before the daemon lost its response needs an effect receipt and reconciliation; the log alone cannot prove that it did nothing. See [restart repair:237–255][restart] and [transcript reconstruction:161–175][transcript].

## 2. Durable sessions, turns and event ownership

Flow's typed events include `RunStarted(run_id)`, user/assistant messages, `ToolResult(tool_call_id, content, is_error, details, attachments)`, `Usage`, `ApprovalRequired`, `RunEnded(reason)`, model changes, rewind and compaction. `seq`, `parent_seq` and timestamp are assigned on append; transient deltas are explicitly not durable. Tool `content` is for model context; structured `details` are for rendering/audit. See [event types:113–273][events].

The useful architectural center is `Session._commit`: **persist → fold transcript → publish**. It clears provisional preview at durable message/run boundaries, uses bounded subscriber queues, and treats relay publication as best-effort because the log can heal gaps. See [commit and snapshot:487–580][commit]. Keep this single event-write path in Bob rather than adding persistence separately to each emit handler.

The Frappe integration reads only events after `last_synced_seq`, records them as Flow Runs/messages, and advances the cursor under a session row lock. The lock is followed by `reload()`, so the projection does not append from a stale document copy. A terminal callback can retry safely by syncing through its sequence. See [DB sync:336–367][sync], [LogRecorder:126–217][recorder], [terminal callback:75–98][callback]. Bob can project messages, usage, accepted operations and recovery metadata from the same protocol instead of writing complete/error/cancel message variants independently.

**Turn identity differs from execution attempt identity.** Flow emits a new daemon `RunStarted` when resuming; its Frappe recorder associates a resumed paused operation with the existing logical Flow Run (`LogRecorder.start_run`, lines 156–165). Bob should choose explicit semantics: stable user turn/run ID across a card pause, separate attempt/continuation ID for each execution segment if needed. Do not infer the current turn from "last assistant message" or timestamp order. The current `api.py:545–552` / `session.py:302–322` metadata update can target a newer assistant message after an asynchronous completion.

**Do not copy these limitations:**

- `SessionLog` uses an object-local `threading.Lock`; session admission uses `asyncio.Lock`. These do not coordinate independent Frappe workers or multiple daemon processes. Flow relies on one owning session object/daemon. Bob needs ownership partitioning or distributed lease/fencing plus database uniqueness. [Log:31–77][log], [session admission:307–343][admission].
- JSONL append uses `os.write`/close, but no `fsync`; `read_since` reparses the full file, and malformed rows fail strict validation. It is not a transactional multi-process database or a power-loss guarantee. If Bob uses SQL events, allocate `(session_id,seq)` under a row lock/atomic counter and add a uniqueness constraint; index cursor queries. If adopting Flow's file log, explicitly preserve its one-writer assumption and decide backup/corrupt-tail recovery requirements. [Log implementation:41–122][log].
- Not every Flow event includes `run_id`; only the start event defines it and subsequent events are interpreted in order. Bob should put `run_id` on every event because its page channel, delayed callbacks and independent tools make ownership more complex.

## 3. Admission, pause/resume and waiting for the user

`Session.run/resume/rewind/compact` serialize admission through `_operation_lock`. A paused session refuses a new run. Resume requires the exact pending `approval_seq` and exact set of tool-call answer IDs; stale/missing/extra answers fail. Cancellation of a pending batch records a result for each undecided call, keeping the next provider transcript valid. See [answer validation:110–134][resume-validation], [resume:345–368][resume], [cancel pending:442–460][cancel-pending].

When an approval is needed, the loop emits `ApprovalRequired` then `RunEnded(reason="paused")` and returns. The pending batch lives in the transcript, so no ordinary worker/model request remains waiting for the person. See [pause:329–337][pause]. This maps well to Bob's visual questions and direction selection: persist `card_id`, schema/version, typed answers, status and continuation; return from execution. Resolve the exact card under a lock, save the answer/result once, and enqueue/resume exactly once.

**Do not adopt Flow's running-message policy accidentally.** A new message sent while the session runs is appended to an **in-memory steering deque**, and the endpoint returns `steered`; it is not durable until the loop consumes it. Abort/terminal paths discard unconsumed steering. This is acceptable only with an explicit product contract and recoverable UI draft. Bob's default should reject or durably queue a second turn; support steering only deliberately. [Admission:307–343][admission], [discard:681–690][settle].

**Request retries are not idempotent in Flow.** The daemon `RunRequest` contains only message and attachments; the response is just status. A repeated POST can become duplicate steering or a new turn. Bob needs a client-generated submission key scoped to user/site (including first-session creation), an immutable payload fingerprint and stored outcome. Its present busy check (`api.py:73–78`) precedes a worker-held lock; messages are persisted (`98`) before execution admission. Flow's concurrency model is instructive, but it does not solve that queue gap by itself. [Request schema:47–51][run-request], [response:501–506][finish].

## 4. Streaming and reconnect

Flow distinguishes a durable cursor (`seq`) from transient delivery version (`stream_id`, `revision`). A new stream ID resets transient revision comparisons when the owner object/process changes. `event_snapshot(since)` contains durable entries, current preview, latest sequence and current state. The client subscribes to the relay **before** fetching the snapshot, buffers live traffic, and deduplicates events already covered by the snapshot. Gaps, reconnect, a resync notice or a changed stream ID cause a refetch. See [snapshot/subscribe:487–524][commit] and [SessionStream:79–159][stream].

On reconnect the client emits `preview_replay_started`, so recovered provisional text **replaces** the prior preview. A durable assistant message replaces provisional rendering too. Re-appending preview chunks would duplicate text. Terminal sync callbacks are deduplicated by terminal sequence. Relay queues are bounded, and overflow requests resync rather than silently losing the durable history. See [reducer:138–193, preview handling][reducer], [Redis backpressure:61–78,123–127][redis].

**Bob implementation:** make `get_ai_session` return active/queued/paused run identity and a coherent event cursor; `api.py:491–497` currently returns messages only. `get_active_build` (`595–601`) only recovers generation preview, not every agent run. Add `events(since)`/snapshot recovery; subscribe on refresh and reconnect, not just initial send. Transport can remain Frappe Socket.IO—the contract matters more than SSE versus sockets.

Snapshot/preview/cursor must be captured consistently. Buffer newer events while hydrating; never advance the cursor past a gap merely because a refetch succeeded but returned an incomplete page. Add explicit pagination/watermark or resync-required semantics if Bob bounds event retention. For a lost preview buffer, recover the authoritative page and durable transcript rather than pretending partial text is final.

## 5. Frontend state: reuse the reducer and ownership pattern

Flow's `initialConversation` separates committed entries, optimistic sends, steering and provisional assistant blocks. `applyEvent` folds both replayed and live events through one path. `openSession` increments an opening epoch and checks both session and epoch **after each await**. The stream loop checks ownership against the exact stream object as well as session ID, including error/finally handlers. See [store hydration/stream ownership:535–627][store-open], [conversation state:53–89 and reducer:138–193][reducer].

**Bob comparison:** `AIChatController.ts:358–387` guards loads by page/load epoch, but `submitPrompt:853–863` increments `sessionIntentEpoch` without invalidating the load epoch. An older load can overwrite new optimistic messages before a later guard runs. Completion reload (`664–687`) validates turn ownership only **after** `loadSession()` has already mutated the visible state. Existing event filtering (`459–467`) is by session, not run; late terminal events from an earlier turn can affect the next turn. Borrow Flow's ownership checks, extending the identity to `{pageId, sessionId, runId, viewEpoch}`.

Keep per-session draft text, attached images, selected blocks and card answers separate from hydrated server messages. A send failure must restore the complete draft, not only prose. Match optimistic messages by `request_id`/server message ID. Flow's reducer currently shifts the oldest optimistic send and its steering reconciliation uses text/attachment comparisons (`transcript.js:149–157`, `store.js:645–665`); those are not strong identities for identical simultaneous messages across tabs. Its `applyEvent` also does not itself reject every duplicate sequence; deduplication is a transport responsibility. Preserve that layering or make Bob's reducer explicitly idempotent.

## 6. Cancellation and terminal completeness

Flow allocates a fresh abort signal per operation and rejects steering while aborting. Its async cancellation helper races the provider await against the signal, gives cancellation precedence when both finish, cancels the pending task and closes the iterator. This works even while waiting for the next chunk, instead of checking only when another token arrives. The loop checks before new tool work and cancellation-aware waits wrap callbacks. See [fresh signal:598–609][fresh-signal], [cancellation helpers:19–74][cancellation], [tool execution checks:512–559,627–645][tool-execution].

Every failed/aborted operation settles the transcript: repair unanswered calls, preserve partial assistant content for aborts, record typed error if applicable, record `RunEnded`, then report completion. Startup repairs crashed sessions similarly. Usage is a durable event rather than metadata written only on happy-path completion. See [settlement:692–743][settle] and [Usage:201–210][events]. Bob should centralize finalization across complete/failed/stopped/paused outcomes, retaining usage, accepted effects, snapshot and verification status. Current `loop.py:1147–1159` loses metadata present in success finalization (`1343–1380`).

**Flow is not a full cancellation solution for Bob:** its HTTP abort targets the session's current task, not an explicit run ID, and its abort signal is memory-local. Bob must persist cancellation before runtime admission and scope it to the run. Its current `api.py:226–237` sets a session Redis flag but treats a queued job as inactive; `loop.py:1162–1163` clears the flag before lock acquisition. A new cancellation must never be cleared by a duplicate worker or previous run's cleanup.

Cancel does not imply rollback. A callback's effect may commit after the daemon cancels its await, and Flow's background-tool preflight can race cancellation. Require effect receipts, no new mutation admission after cancellation is observed, and accurate partial/uncertain outcomes. Do not claim every pending tool was unexecuted merely because its result was missing. Bob's page lock token currently fences **release** (`locks.py:5–6,58–63`), not necessarily every mutation after lease expiry; fence writes or verify page revision and ownership at execution.

## 7. Context compaction and long-lived design state

Flow keeps original events, appends `Compaction(summary, compact_up_to_seq, reason)`, and folds only the model-facing transcript into summary plus recent messages. The planner chooses a boundary at a user turn where possible and never starts the retained tail on a bare tool result. A previous summary is updated explicitly. A summary becomes durable only on successful completion. See [compaction planning:120–171,262–341][compaction], [folding:232–245][transcript].

It budgets the whole request—system prompt, tool schemas, messages and approximate attachments—reserves output room, scales the retained tail to the model window, and permits a single context-overflow compaction/retry per run. An attempted retry clears the abandoned preview, and provider retries do not replay completed tools. See [full estimate:538–580][estimate], [overflow and scaled-tail logic:387–451][context-loop]. Central tool-result truncation retains head/tail and explicit diagnostics, including a warning not to repeat a mutation simply to recover omitted output. [Result cap:671–690][result-cap].

**Bob comparison:** `AISession.CONTEXT_WINDOW=10` (`session.py:16`) limits message rows, not full turns; `build_context_messages:184–202` drops the newest row by position and filters failed/stopped messages. Adding Flow-style compaction should replace this implicit position-based window with an explicit current input identity plus budgeted retained history. Do not lose records of partial effects just because their run failed.

**Design memory must be stronger than a model summary.** Persist the approved brief, selected variant/assets with immutable IDs and provenance, factual constraints, pending questions, verification results and base page revision as typed project/page state. Build model context from that state + summary + recent complete turns. A summary can omit or distort an asset choice; it must not be the authority for the chosen original image, an approval, or a fact. Likewise Flow's character-count heuristic/fixed image estimate is approximate, not an exact provider bill or a guarantee that a huge fresh tool response fits. Bound results before context assembly and provide artifact handles/cursors.

## 8. Pending actions, side effects, rewind and concurrency

Flow validates a pending batch's sequence/IDs under its operation lock, and its Frappe completion callback claims `on_complete` under a row lock, clears it, then invokes the handler. That is useful local transaction/idempotency discipline. It does not promise exactly-once external network effects. See [resume validation][resume-validation], [completion claim:236–258][completion-claim]. Bob's `confirm_pending_settings:155–175` reads status, performs the effect, then sets applied: two tabs can both pass. Claim/validate and persist result under a database lock or equivalent atomic operation; use provider idempotency or reconciliation for external effects. Continuation scheduling must also be unique.

Flow rewinds by appending a branch marker and validates that the target leaves no unanswered tools or pending approval; the old rows remain in its journal. It refuses rewind while running/paused. Its frontend seeds from the active branch, not the raw full journal. See [rewind:378–396][rewind], [active path:64–99][active-path].

**Rewind is conversation branching, not page rollback.** Bob's `api.py:241–249` truncates chat before the controller restores the snapshot (`AIChatController.ts:950–964`). Replace that split with one server operation that validates snapshot availability, permission, expected current page revision, absence/termination of active work, and effect scope before changing anything. Commit the page restore and conversation branch/turn status together where effects are transactional. Shared scripts/files/external operations need explicit compensation/versioning; neither Flow's rewind nor a DB rollback makes them reversible. Keep the audit trail instead of deleting evidence.

Serialize mutation tools by default. Flow opts tools into concurrency with `Tool.concurrent`, grouping only adjacent compatible calls and settling results with call IDs. [Batching:512–559][tool-execution], [tool interface:113–148][tool-interface]. Bob should parallelize independent reads; page/tree/script mutations require a page-level policy independent of per-session exclusion. Two sessions can share a page, and a human editor does not honor an AI-only Redis lock—expected revision checks are still needed.

## 9. Reusable interfaces and adoption cost

- **Standalone Python harness:** distribution `frappe-flow==0.1.20`, namespace `flow_harness`, MIT. `SessionStore`, `SessionConfig`, `Session.run/resume/abort/rewind/compact/events/event_snapshot`; `Agent.run/resume/compact` async event iterators are an embedding wrapper over the same sessions. [Agent interface:23–87][agent], [package manifest][python-package]. Embedding it in an RQ job does not free that worker.
- **Model boundary:** `flow_harness.model.base.Model.run(ModelRequest) -> AsyncIterator[AnyEvent]` and cancellation-aware provider adapters are reusable in an isolated runtime. The session system is coupled to its typed messages/tools/configuration; it is not a small drop-in replacement for `AISession`.
- **Tool boundary:** `Tool`/`@tool`, `ToolContext` (abort signal, tool_call_id), and `ToolResult(content, details, is_error, attachments)`. Useful for distinguishing model text from canonical accepted operations/UI metadata. [Definitions:67–158][tool-interface]. Note callback `_dispatch` currently forwards only content/is_error into the returned event (`agent/loop.py:663–665`); Bob's structured accepted-operations receipts need an explicit extension/adapter, not an assumption that remote details already round-trip.
- **Service boundary:** `POST /sessions/{sid}/run`, `/resume` with `approval_seq`, `/abort`, `/compact`, `/rewind`; `GET /entries?path=active` for a branch snapshot, `path=all&since=N` for incremental replay; `/stream?since=N` for SSE. Client tools use authenticated callbacks, optional `{pending:true,timeout:N}` and `/tool_result` with a result token. [Frappe DaemonClient:80–167][daemon-client], [entries/stream routes:450–495][routes]. Tokens/futures for background tools are in-memory delivery handles, not durable job IDs.
- **UI package:** `@flow/ui-core` version `0.0.0`, consumed from source through Flow's local link, exports `createFlowStore`, `initialConversation`, `applyEvent`, clients and Vue components. Host options include custom tool rendering, storage key, attachment preparation and disabling filesystem workspace/skills. [Package][ui-package], [host API docs:31–83][ui-docs]. The small reducer/transport patterns are directly useful; replacing Bob's rich design cards/controller wholesale would be a larger product migration. No registry publication/stability claim was verified.
- **Compatibility blocker for a direct dependency:** harness requires Python **>=3.14**, LiteLLM **1.103.2**, FastAPI/Uvicorn/HTTPX/Pydantic; Builder declares Python **>=3.10**, LiteLLM **1.95.1**. The complete Flow Frappe app also brings unrelated vector/OCR/document packages and a Python `>=3.14,<3.15` constraint. An isolated Flow service with a Bob adapter is a credible option; adding the complete Flow app or changing Builder's Python baseline implicitly is not. [Harness dependencies][python-package], [Flow app dependencies][flow-package].

## Verification and focused release checks

Source review and offline JS tests only; no live Frappe site, daemon deployment, provider billing, restart fault injection or capacity test was run. **34 targeted tests passed:** 5 relay-stream tests, 2 event presentation tests, 27 pure transcript tests. A broader initial `runs.test.js` attempt passed its 3 pure tests but its 2 Vue-dependent tests could not load because the fresh read-only clone has no installed `vue`; this is an environment limitation, not an observed product assertion failure. A `/tmp` Node loader maps only `@flow/ui-core/*` to the clone's source; no dependencies or source files were added to either checkout.

Commands:

```sh
node --loader /tmp/bob-flow-test-loader.mjs --test frontend/test/stream.test.js frontend/test/events.test.js
node --test harness/ui/core/test/transcript.test.js
```

Highest-value Bob tests to implement alongside the contract:

1. Concurrent duplicate submissions, including a first message: one session/run/input; lost response can be retried with the same request ID.
2. Cancel immediately after admission but before runtime claim: zero provider requests and zero tool effects; an old cancel/terminal cannot stop a newer run.
3. Run many simultaneous slow stub model streams while verifying ordinary Frappe/RQ work is available; include nested generation/research calls so callbacks cannot conceal worker occupancy.
4. Pause on a typed card, restart runtime, submit twice from two tabs: exact continuation once, original model/brief/asset selection retained.
5. Refresh/reconnect during prose and YAML streaming; duplicate/reordered events, relay overflow and a changed stream ID: transcript and page converge without duplicate content or mutation replay.
6. Crash after effect commit but before result delivery: receipt reconciles the outcome, no duplicate write/charge; partial/error run retains cost and snapshot metadata.
7. Delayed load/completion/cancel responses after a page/session switch or a fresh send: no cross-view mutation, lost draft or wrong-session selection.
8. Compact long history containing pending choices/tool pairs/images: preserve protocol validity, approved brief and original asset identity; failed/cancelled summary folds nothing.
9. Revert an expired snapshot or a turn whose page was edited since: reject before either page or conversation is changed.

[lifecycle]: https://github.com/frappe/flow/blob/9562f406e2c246ffe80e51d27768fac50e4a17e5/flow/daemon/lifecycle.py#L189-L275
[daemon-client]: https://github.com/frappe/flow/blob/9562f406e2c246ffe80e51d27768fac50e4a17e5/flow/daemon/client.py#L26-L167
[start-operation]: https://github.com/frappe/flow/blob/9562f406e2c246ffe80e51d27768fac50e4a17e5/harness/src/flow_harness/session/session.py#L584-L596
[model-stream]: https://github.com/frappe/flow/blob/9562f406e2c246ffe80e51d27768fac50e4a17e5/harness/src/flow_harness/model/litellm.py#L137-L189
[finish]: https://github.com/frappe/flow/blob/9562f406e2c246ffe80e51d27768fac50e4a17e5/harness/src/flow_harness/server/routes/sessions.py#L501-L506
[callback]: https://github.com/frappe/flow/blob/9562f406e2c246ffe80e51d27768fac50e4a17e5/flow/daemon/callback.py#L41-L169
[client-tools]: https://github.com/frappe/flow/blob/9562f406e2c246ffe80e51d27768fac50e4a17e5/harness/src/flow_harness/agent/client_tools.py#L26-L112
[restart]: https://github.com/frappe/flow/blob/9562f406e2c246ffe80e51d27768fac50e4a17e5/harness/src/flow_harness/session/session.py#L237-L255
[transcript]: https://github.com/frappe/flow/blob/9562f406e2c246ffe80e51d27768fac50e4a17e5/harness/src/flow_harness/session/transcript.py#L161-L245
[events]: https://github.com/frappe/flow/blob/9562f406e2c246ffe80e51d27768fac50e4a17e5/harness/src/flow_harness/events.py#L113-L273
[commit]: https://github.com/frappe/flow/blob/9562f406e2c246ffe80e51d27768fac50e4a17e5/harness/src/flow_harness/session/session.py#L487-L580
[sync]: https://github.com/frappe/flow/blob/9562f406e2c246ffe80e51d27768fac50e4a17e5/flow/flow/doctype/flow_session/flow_session.py#L336-L367
[recorder]: https://github.com/frappe/flow/blob/9562f406e2c246ffe80e51d27768fac50e4a17e5/flow/lib/session.py#L126-L217
[log]: https://github.com/frappe/flow/blob/9562f406e2c246ffe80e51d27768fac50e4a17e5/harness/src/flow_harness/session/log.py#L31-L122
[admission]: https://github.com/frappe/flow/blob/9562f406e2c246ffe80e51d27768fac50e4a17e5/harness/src/flow_harness/session/session.py#L307-L343
[resume-validation]: https://github.com/frappe/flow/blob/9562f406e2c246ffe80e51d27768fac50e4a17e5/harness/src/flow_harness/session/session.py#L110-L134
[resume]: https://github.com/frappe/flow/blob/9562f406e2c246ffe80e51d27768fac50e4a17e5/harness/src/flow_harness/session/session.py#L345-L368
[cancel-pending]: https://github.com/frappe/flow/blob/9562f406e2c246ffe80e51d27768fac50e4a17e5/harness/src/flow_harness/session/session.py#L442-L460
[pause]: https://github.com/frappe/flow/blob/9562f406e2c246ffe80e51d27768fac50e4a17e5/harness/src/flow_harness/agent/loop.py#L329-L337
[settle]: https://github.com/frappe/flow/blob/9562f406e2c246ffe80e51d27768fac50e4a17e5/harness/src/flow_harness/session/session.py#L681-L743
[run-request]: https://github.com/frappe/flow/blob/9562f406e2c246ffe80e51d27768fac50e4a17e5/harness/src/flow_harness/server/routes/sessions.py#L47-L51
[stream]: https://github.com/frappe/flow/blob/9562f406e2c246ffe80e51d27768fac50e4a17e5/frontend/src/api/stream.js#L79-L159
[reducer]: https://github.com/frappe/flow/blob/9562f406e2c246ffe80e51d27768fac50e4a17e5/harness/ui/core/src/transcript.js#L53-L278
[redis]: https://github.com/frappe/flow/blob/9562f406e2c246ffe80e51d27768fac50e4a17e5/harness/src/flow_harness/server/redis_sink.py#L61-L127
[store-open]: https://github.com/frappe/flow/blob/9562f406e2c246ffe80e51d27768fac50e4a17e5/harness/ui/core/src/store.js#L535-L627
[fresh-signal]: https://github.com/frappe/flow/blob/9562f406e2c246ffe80e51d27768fac50e4a17e5/harness/src/flow_harness/session/session.py#L598-L609
[cancellation]: https://github.com/frappe/flow/blob/9562f406e2c246ffe80e51d27768fac50e4a17e5/harness/src/flow_harness/model/cancellation.py#L19-L74
[tool-execution]: https://github.com/frappe/flow/blob/9562f406e2c246ffe80e51d27768fac50e4a17e5/harness/src/flow_harness/agent/loop.py#L512-L645
[compaction]: https://github.com/frappe/flow/blob/9562f406e2c246ffe80e51d27768fac50e4a17e5/harness/src/flow_harness/agent/compaction.py#L120-L341
[estimate]: https://github.com/frappe/flow/blob/9562f406e2c246ffe80e51d27768fac50e4a17e5/harness/src/flow_harness/agent/compaction.py#L538-L580
[context-loop]: https://github.com/frappe/flow/blob/9562f406e2c246ffe80e51d27768fac50e4a17e5/harness/src/flow_harness/agent/loop.py#L387-L451
[result-cap]: https://github.com/frappe/flow/blob/9562f406e2c246ffe80e51d27768fac50e4a17e5/harness/src/flow_harness/agent/loop.py#L671-L690
[completion-claim]: https://github.com/frappe/flow/blob/9562f406e2c246ffe80e51d27768fac50e4a17e5/flow/lib/session.py#L236-L258
[rewind]: https://github.com/frappe/flow/blob/9562f406e2c246ffe80e51d27768fac50e4a17e5/harness/src/flow_harness/session/session.py#L378-L396
[active-path]: https://github.com/frappe/flow/blob/9562f406e2c246ffe80e51d27768fac50e4a17e5/harness/src/flow_harness/session/transcript.py#L64-L99
[tool-interface]: https://github.com/frappe/flow/blob/9562f406e2c246ffe80e51d27768fac50e4a17e5/harness/src/flow_harness/tools/tool.py#L67-L158
[agent]: https://github.com/frappe/flow/blob/9562f406e2c246ffe80e51d27768fac50e4a17e5/harness/src/flow_harness/agent/agent.py#L23-L87
[routes]: https://github.com/frappe/flow/blob/9562f406e2c246ffe80e51d27768fac50e4a17e5/harness/src/flow_harness/server/routes/sessions.py#L450-L495
[python-package]: https://github.com/frappe/flow/blob/9562f406e2c246ffe80e51d27768fac50e4a17e5/harness/pyproject.toml#L1-L22
[flow-package]: https://github.com/frappe/flow/blob/9562f406e2c246ffe80e51d27768fac50e4a17e5/pyproject.toml#L1-L21
[ui-package]: https://github.com/frappe/flow/blob/9562f406e2c246ffe80e51d27768fac50e4a17e5/harness/ui/core/package.json#L1-L27
[ui-docs]: https://github.com/frappe/flow/blob/9562f406e2c246ffe80e51d27768fac50e4a17e5/harness/ui/README.md#L31-L83
