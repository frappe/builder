# Bob session and guided-building review

Reviewed: `develop` at `a112a3e6aea1f9e712c75cdb9aeb713009467a90`, `/home/t3run/builder`, 2026-11-01.

## Scope, method, and conclusion

Read-only review of frontend chat, session lifecycle, API/message persistence, realtime, refresh/reconnect/multitab, cancellation/retry/revert, history/deletion, question cards, and onboarding. All source citations below are relative to `/home/t3run/builder` and name the relevant line or range at this commit.

**Bob has substantial useful building machinery, but its conversation lifecycle is still assembled from local booleans, transient socket events, and “the last message.” It lacks a durable identity and status for an individual turn.** Several ordinary interleavings can lose the visible conversation, misreport cancellation, or separate the page from its history. These should be fixed before relying on “you can always Revert” as the reason to build immediately.

The desired personalized, visually guided experience is partly present: stepped cards, curated color roles, photo choices, explicit block attachments, and instructions to learn about the business. However, the entry suggestions deliberately supply complete fictional briefs, the default design choices are verbal descriptions, and the interaction moves straight from collected answers to building. That is a product mismatch with the requested hand holding, independent of model quality.

Evidence labels:

- **Reproduced:** executed the actual TypeScript controller/card script or selected Python source methods with dependencies mocked. These establish deterministic logic defects; they are not browser, database, Redis, or paid-model integration tests.
- **Confirmed by code:** a complete reachable path is present in source. Concurrency findings specify the necessary interleaving; no claim is made about production frequency.
- **Hypothesis / risk:** the outcome depends on deployment behavior, model choices, permissions, or a timing detail not verified here.

No application code, branch, configuration, live site data, Redis state, or model was changed or invoked. No agents were spawned. The initial checkout already had a modified `frappe-ui` submodule and untracked `.scratch/` and `CONTEXT.md`; these were not changed. Review artifacts are under `/tmp`.

Priority: **P1** = possible wrong work, lost history, unintended continued execution, or misleading recovery; **P2** = significant recovery/interaction defects; **P3** = lower-impact usability/maintainability gaps. These are review priorities, not production incident claims.

## Strengths worth preserving

1. **Server-authoritative page mutation.** Accepted block operations are applied to the working tree, saved, and mirrored to the browser; round checkpoints preserve completed work. See `builder/ai/agent/loop.py:1025-1056,1267-1274`. The client suppresses autosave while mirroring server edits and invalidates older debounced saves with an epoch (`frontend/src/components/AIChatController.ts:614-627`; `frontend/src/pages/PageBuilder.vue:338-360`). This is the right direction, even though it is not yet a cross-tab write protocol.
2. **Atomic worker locks with fenced release and TTL.** `builder/ai/locks.py:21-69` avoids a stale worker releasing a newer holder's lock. Separate page/session keys protect against two AI workers concurrently owning the same page/session. The admission gap discussed below does not negate this improvement.
3. **Useful ownership and persistence boundaries.** Session reads verify user and page (`builder/ai/session.py:64-73`); the history list filters by user (`builder/ai/api.py:516-521`); messages live in separate records rather than a shared transcript blob (`builder/ai/session.py:262-300`). Lazy session creation avoids empty-chat litter (`builder/ai/api.py:478-507`).
4. **Several important stale-response guards already exist.** Session loads have epochs and page checks; first-send events wait for the returned session ID; realtime text is filtered by session; refetches check page-load ownership (`frontend/src/components/AIChatController.ts:358-387,459-474,555-569`). Extend these concepts to turn identity and every asynchronous continuation.
5. **After-commit events for persisted terminal results.** Complete, clarification, and ordinary error paths schedule notifications after commit (`builder/ai/agent/loop.py:482-498,1147-1159,1382`; `builder/ai/agent/tools/conversation.py:66-80`). This avoids the common “socket event arrives before the row exists” race for those paths.
6. **Concrete foundations for personalization.** Prompts explicitly seek the brand's distinctive details, preserve user-picked color roles, use real reference pages, and differentiate structural directions (`builder/ai/prompts.py:112-125`). `AIUISpec.vue:19-36,86-188` supports one-at-a-time questions, photo choices, uploads, and labeled colors. These can support a better discovery flow without replacing the whole chat.
7. **Explicit context and transparent work.** Canvas selection is not silently sent as scope; the user attaches blocks deliberately (`AIChatController.ts:158-180,868-874`). Timeline/debug metadata and affected-item links are valuable for inspecting outcomes. Private pasted-image persistence and bounded image replay also show care (`builder/ai/api.py:26-47`; `builder/ai/session.py:217-243`).
8. **Sensitive proposals have a real user-triggered application endpoint.** Pending payloads are stored, ownership and settings permission are checked, and the endpoint applies the stored payload (`builder/ai/api.py:143-175`). It needs atomic consumption, but is a sound base.

## Confirmed findings

### F1 — P1: Sending does not invalidate an in-flight session load; a late read can erase the new turn

**Reproduced, two variants.**

- Start in session A, choose B on a slow connection, then send while B is loading. `switchSession()` resets transient state but leaves A's ID until the response arrives (`frontend/src/components/AIChatController.ts:401-407`). The composer and `canSubmit` do not check `isLoadingSession` (`:200-207`; `BuilderAIChatPanel.vue:339-349`). `submitPrompt()` captures A and increments `sessionIntentEpoch`, but does not invalidate `loadSessionEpoch` (`AIChatController.ts:853-863`). B's response therefore still commits at `:374-379`, replacing the just-submitted messages and selecting B while A runs. A's subsequent text events are filtered out by `:459-462`.
- Complete a turn, then send the next prompt before the completion handler's history read returns. `onComplete()` enables sending before awaiting `loadSession()` (`:660-685`). The new send does not invalidate that read. The read replaces the optimistic user/assistant messages. The turn-count check at `:686-687` is too late: replacement happened inside `loadSession()` already.

**Impact:** the prompt can go to the old chat, the new turn vanishes from the panel, and controls can indicate a running session with no visible response. This is not solved by the existing “only newest load wins” rule because the new send is not a new load.

**Small fix:** pin a session/turn ownership token through each read, invalidate pending history reads when sending, and disable sending during an explicit switch (or commit the chosen ID atomically before enabling it). A completion read must merge/preserve a newer optimistic tail, or be discarded before mutation. Add both interleavings as controller tests.

### F2 — P1: Refresh and reconnect cannot reconstruct an active turn; missed terminal events leave the panel stuck

**Confirmed by code; refresh text loss reproduced.**

`get_ai_session()` returns messages and model metadata, but no queued/running/cancelling turn or event cursor (`builder/ai/api.py:490-497`). `loadSession()` only replaces the transcript; it does not reconstruct `pendingAssistantId` or activity state (`frontend/src/components/AIChatController.ts:375-379`). After refresh, subsequent progress/stream events set `isSubmitting`, but text is written only through `replacePendingAssistant()`, which returns immediately without a pending ID (`:319-327,480-514,532-547`). In a second tab opened mid-run, the same problem occurs: it can show activity but no live answer/timeline.

Mount calls `loadSession()` but never `syncActiveBuild()` (`:991-996`). The latter is called on a route change or a detected YAML gap (`:102-130,223-238`), so a hard refresh during a quiet generation interval does not proactively restore the buffered canvas. A later chunk may trigger recovery; that is narrower than reliable refresh support.

There is no Bob reconnect reconciliation: `frontend/src/components/ai/realtime.ts:26-49` subscribes only to domain events; `frontend/src/utils/realtimeHandler.ts:9-25` forwards socket events without a reconnect handler. If the connection is down when complete/error/clarify is emitted, no general turn-status poll or rehydration clears the running chat. The 45-second timer only handles canvas-build state (`AIChatController.ts:80-97`), not a text-only turn. A disconnected tab also misses authoritative tool batches; a later manual save can persist its stale page tree (`frontend/src/stores/pageStore.ts:374-389`).

**Small fix:** expose durable active-turn state and the current draft revision in session hydration; reconcile on mount, reconnect, and foreground; synthesize a pending assistant from the server turn, and refetch the authoritative page after an event gap. Realtime should accelerate updates, not be the only record of completion.

### F3 — P1: Queued admission is neither exclusive nor idempotent; concurrent/retried sends persist incompatible turns

**Reproduced for two queued submissions and context corruption; duplicate billing is a consequence if both jobs execute successfully.**

The API checks only a running worker lock (`builder/ai/api.py:73-78`). It then appends the user message and queues a job (`:84-98,116-132`), without reserving a queued slot or accepting a request ID. The lock is first acquired when the worker runs (`builder/ai/agent/loop.py:1170-1179`). Two tabs can therefore both receive acceptance while the queue is delayed, and both prompts are persisted.

Two outcomes follow:

- Workers overlap: one worker emits a session-scoped error and returns without persisting a corresponding failure message (`loop.py:1173-1179`). The client treats this as the active session's failure, stops its running UI, and reloads (`AIChatController.ts:712-726`), even if the other worker still owns the session. Since the error was not saved, the reload also removes the visible explanation.
- Workers execute sequentially: both requests run, even when the second was merely a retry after losing the HTTP acceptance response. There is no idempotency key to return the original run.

Context reconstruction assumes the newest row is the current prompt and drops it unconditionally (`builder/ai/session.py:184-193`). If A and B were queued before worker A starts, A's context retains A as history and drops B, then `build_messages()` appends A again (`builder/ai/agent/loop.py:602-606,618-639`). The worker has no triggering message ID to bound its history.

**Small fix:** create a durable turn at admission, uniquely keyed by client request ID; reserve its queued/running slot atomically before persisting the user prompt; bind the worker to that turn and user-message ID. Reject or intentionally queue competing turns with visible status. Worker events must carry `turn_id`, and history must end before that turn's triggering message.

### F4 — P1: Stop can be ignored before a queued job starts, and a rejected duplicate can clear another run's cancellation

**Reproduced from Python source; watchdog behavior also reproduced in TypeScript.**

`cancel()` sets a session-wide flag, then reports `not_running` when no worker holds the lock (`builder/ai/api.py:223-237`). A queued job is indistinguishable from a dead job here. The frontend says “That run is no longer active” and resets (`frontend/src/components/AIChatController.ts:830-843`). When the queued job eventually starts, `AgentRunner.run()` deletes the flag before acquiring its lock (`builder/ai/agent/loop.py:1161-1179`), then proceeds to the model.

The same ordering lets a duplicate worker clear a real cancellation flag and then fail to acquire the running worker's lock. Cancellation belongs to the session, not the particular turn, so there is no safe distinction between stale and current cancellation.

Separately, after 20 seconds the client watchdog unconditionally resets the UI and claims inactivity without asking whether the worker ended (`AIChatController.ts:830-850`). A stalled provider may still be active. Stream checks are cooperative (`loop.py:738`; `builder/ai/agent/artifact.py:285-295`), so the watchdog cannot infer completion merely from elapsed time.

**Small fix:** cancel a durable turn, including its queued state; check cancellation before any provider call; never clear a cancellation belonging to a current turn when rejecting another worker. On timeout say “Stop requested; checking status” until the server confirms terminal state.

### F5 — P1: Revert is two independent operations and can destroy history without restoring the page

**Confirmed by code; continuing after failed truncation reproduced.**

`revertTurn()` first calls `revert_to_message`, suppresses any error, then restores the snapshot (`frontend/src/components/AIChatController.ts:946-964`). The backend truncates the conversation without checking the snapshot or acquiring the page/turn lock (`builder/ai/api.py:241-249`; `builder/ai/session.py:345-363`). Snapshot restoration is a separate request (`frontend/src/stores/pageStore.ts:301-317`).

- Truncation succeeds, restoration fails: history is permanently removed while the page remains changed.
- Truncation fails: the `.catch(() => null)` still allows restoration, leaving an old transcript attached to a rewound page.
- This is reachable without exotic failures: AI snapshots are pruned to 10 **per page** (`builder/ai/snapshots.py:16-17,58-61`; `builder/builder/doctype/builder_snapshot/builder_snapshot.py:128-144`), but old messages retain `revertSnapshot`, and the button only tests for the string (`BuilderAIChatPanel.vue:150-154`). Reverting an older turn can delete the chat suffix and then fail to load the already-pruned snapshot.
- A second tab/session can be editing the same page. The local `isSubmitting` guard protects only this panel; neither truncation nor `restore_snapshot()` uses the AI page lock (`builder/builder/doctype/builder_page/builder_page.py:489-524`). A still-running worker can subsequently overwrite the restored page from its in-memory tree.

**Small fix:** one server operation validates snapshot existence and page/session ownership, obtains page/turn ownership, checks the current page revision, then restores and truncates together. Account for script/file side effects rather than assuming a DB transaction rolls them back. Mark expired snapshots unavailable in history before offering Revert.

### F6 — P1: Partial changes from cancelled, failed, or card-ending turns lose their Revert handle

**Reproduced for cancel/error metadata; confirmed for card paths.**

The worker creates a pre-turn snapshot before mutations (`builder/ai/agent/loop.py:500-508,1033-1035`) and checkpoints applied work (`:1053-1055,1267-1274`). Only the ordinary success finalizer stores `revertSnapshot` in the assistant message (`:1365-1380`).

Cancellation persists only `{status: 'cancelled'}`; failure persists only `{status: 'error'}` (`:1147-1159`). Both return before `finish_turn()` (`:1254-1265`). `present_ui` and sensitive-action cards likewise omit the snapshot (`builder/ai/agent/tools/conversation.py:66-80`; `builder/ai/agent/pending.py:39-64`), although client operations can run before a terminal card in the same round (`loop.py:1225-1246`).

**Impact:** precisely the interrupted or problematic build most likely to need reversal has no chat Revert button. The underlying snapshot may remain in generic history; this is not a claim that every recovery path is gone. Cancel/error also lose the timeline/debug trace, weakening diagnosis.

**Small fix:** centralize terminal message metadata so every outcome preserves the turn ID, snapshot, partial mutations, steps, and error/cancellation status. Clearly distinguish “stopped; these changes were kept” from “cancelled before any changes.”

### F7 — P1: The Revert promise that the live page will not change is false for existing shared scripts

**Confirmed by code.**

The confirmation says “Your live page won't change until you publish” (`frontend/src/components/AIChatController.ts:951-953`). Restoring a snapshot saves the existing linked `Builder Client Script` records (`builder/builder/doctype/builder_page/builder_page.py:514-523`). Their save hook rewrites the same public file, changes its version query, commits, and clears referencing-page caches (`builder/builder/doctype/builder_client_script/builder_client_script.py:40-49,85-104,114-118`). Script updates during Bob's normal edits have the same behavior (`builder/ai/agent/tools/scripts.py:110-131`).

A published page using that script—and any other page sharing it—therefore receives the restored or updated script independently of publishing the page's draft blocks. The file is shared mutable state, not a draft version of the script.

**Small fix:** correct the confirmation and disclose actual scope immediately; longer-term, version scripts with the page draft/published revision or use copy-on-write for draft edits. Merely wrapping Revert in a transaction does not roll back the public file writes or explicit commit in the script hook.

### F8 — P1: A pending action can be applied twice from two tabs

**Confirmed concurrency defect by code; not run against a database.**

`confirm_pending_settings()` reads `msg.status`, applies the side effect, and only then writes `action_applied`, without a row lock or conditional claim (`builder/ai/api.py:155-175`). Two requests can both read `pending_action` before either changes it. The local loading flag (`frontend/src/components/BuilderAIChatPanel.vue:493-500`) cannot coordinate tabs.

This is not always a harmless repeated assignment: `apply_seed_sample_data()` inserts each record again (`builder/ai/agent/pending.py:143-154`). Both calls can also append outcomes and enqueue continuations because the resume guard sees only running jobs (`builder/ai/api.py:179-208`).

**Small fix:** atomically consume a pending action by message/action ID before executing it, return its stored outcome on retries, and make continuation creation unique. For actions whose underlying DocType/file hooks commit, use an explicit action state/idempotency record rather than relying only on rollback.

### F9 — P2: A late confirmation response starts a phantom resumed turn in the currently viewed chat

**Reproduced.**

`confirmPendingAction()` waits for the action request, then calls `loadSession()` for whatever chat is current and unconditionally calls `beginResumedTurn()` if the response says resumed (`frontend/src/components/AIChatController.ts:784-812`). It captures neither the original session nor an intent epoch.

Click Apply in A, switch to B while the request is outstanding, then receive the response. The worker correctly runs A, but the panel appends a running assistant to B and disables its composer. A's completion is foreign to B and does not clear B's submitting flag (`:649-655`). A similar fast-completion-before-HTTP-response ordering can resurrect a finished turn as running.

**Small fix:** associate the confirmation and continuation with returned session/turn IDs, guard asynchronous UI writes with the original intent, and hydrate status rather than inventing a new local turn after the request completes.

### F10 — P2: YAML preview state has no generation identity; consecutive foreign builds reuse the wrong offset

**Reproduced.**

Canvas YAML is accepted even for another session on the same page (`frontend/src/components/AIChatController.ts:525-530`), which is appropriate for a page-level preview. But foreign completion only calls `endCanvasBuild()` and returns (`:649-655`); it does not clear `pageStreamContent`. Foreign error returns before cleanup (`:712-714`), and foreign clarification does likewise (`:738-739`).

Leave tab A viewing session A while tab B generates in session B. After B completes, A retains B's old accumulated YAML. B's next generation starts at offset zero; A drops it as an already-seen chunk because `offset < have` (`:102-108`). It can continue dropping subsequent chunks or combine an old prefix with a new suffix. The final authoritative tool batch may still correct the canvas; that does not make the intervening preview reliable.

There is no `generation_id` in stream events or the buffer (`builder/ai/agent/artifact.py:204-210,303-310`). Another generation within one turn has the same ambiguity. Foreign completion also assumes a final tool batch exists; on a failed generation that assumption need not hold, so a partial preview can be released without resyncing the persisted draft.

**Small fix:** scope buffers, offsets, timers, and reconciliation to `(page_id, turn_id, generation_id)`. Reset on an explicit generation-start event and finalize or discard every generation regardless of which chat is selected. A late buffer response must not revive a completed generation.

### F11 — P2: Stream offsets disagree for emoji and other non-BMP characters

**Reproduced.**

The server sends Python `len(yaml_content)`, a Unicode code-point count (`builder/ai/agent/artifact.py:303-307`). The frontend compares it to JavaScript `.length`, a UTF-16 code-unit count (`frontend/src/components/AIChatController.ts:102-113`). After the chunk `😀`, the server's next offset is 1 while the browser has length 2. The next chunk is discarded as a duplicate. Subsequent gaps/replays can repeat the mismatch.

**Impact:** streaming previews drop or misassemble text when such characters occur. The final authoritative block tree is a separate path and can still be correct.

**Small fix:** use sequence numbers or one specified byte/code-unit convention at both ends. Test emoji and non-BMP script characters across chunk boundaries and after buffer replay.

### F12 — P2: Failed sends restore only the text, silently losing image and selected-block context

**Reproduced.**

`submitPrompt()` clears attached blocks and image state before awaiting either the page save or API request (`frontend/src/components/AIChatController.ts:868-874,897-916`). `failSend()` restores only `userText` (`:932-939`). A save failure, offline request, busy rejection, or unsupported image/model error therefore leaves the retry without its reference image and block scope.

The user can resend exactly the visible text and receive a materially different build. The comment that a failed send means “nothing reached the chat” is also too strong: losing an accepted HTTP response does not establish that the backend did not queue it. That ambiguity needs F3's request identity, not only prompt restoration.

**Small fix:** retain an immutable pending-send envelope and restore all its fields on a verified pre-admission failure. For unknown outcomes, reconcile by request ID before enabling Retry. Preserve the card-answer metadata in that envelope too.

### F13 — P2: Deleting a chat neither cancels its worker nor reconciles other tabs; older history is inaccessible through the picker

**Confirmed by code.**

Deletion checks ownership and deletes the session/messages, but does not cancel or reject an active/queued run (`builder/ai/api.py:534-540`; `builder/builder/doctype/builder_ai_session/builder_ai_session.py:27-33`). The worker does not need the session to continue editing the page; message persistence merely becomes a no-op when the session is missing (`builder/ai/session.py:75-87`; `builder/ai/agent/loop.py:1191-1208`). A second tab can delete a running chat because its local submitting state is not authoritative (F2). Work can continue without a surviving transcript.

No deletion event informs the other tab. A subsequent send with the deleted session ID fails in `AISession.get()` (`session.py:64-67`); a later load silently falls back to a different last-used chat (`api.py:486-490`), which can be confusing. The deletion UI suppresses request failures and proceeds as though it should select another chat (`AIChatController.ts:420-431`).

History additionally stops at the newest 20 sessions: `list_page_ai_sessions` defaults to 20 and caps at 50 (`api.py:512,516-522`), while `loadSessions()` sends no limit/cursor and both history menus render only this returned array (`AIChatController.ts:390-398`; `BuilderAIChatPanel.vue:459-485`; `frontend/src/components/ai/commands/chats.ts:8-28`). A twenty-first older chat is still stored but has no supported picker path.

**Small fix:** define delete-during-run behavior (cancel and archive until settled, or refuse with an explanation), broadcast a tombstone, report failures, and invalidate affected client state. Add paginated/searchable history and persist the user's selected session per tab/page; do not equate “most recently received a message” with “the chat this tab chose.”

### F14 — P2: Resuming after Apply can silently use an old model

**Confirmed by code.**

A session's `selected_model` is written when it is created (`builder/ai/session.py:49-60`). Later `run()` calls use the newly selected model but never update that field (`builder/ai/api.py:87-110`). The UI also ignores the session's returned selected model and uses a site-wide local-storage key (`frontend/src/components/AIChatController.ts:73,375-379`). `resume_after_action()` uses the original session field (`builder/ai/api.py:189-205`).

Create a chat with model A, choose model B, let B propose a sensitive action, then Apply. The continuation uses A; if A is no longer configured, automatic continuation can fail. This contradicts the worker's explicit promise to use the picked model (`builder/ai/agent/loop.py:1201-1204`) and can change quality or cost unexpectedly.

**Small fix:** bind model/provider settings to the proposing turn and reuse that provenance for the continuation. Separately decide whether switching history should restore a session preference or retain a global picker preference; make that behavior explicit.

### F15 — P2: The card fallback tests for controls, not for a usable submission path

**Reproduced for a multi-select-only card; confirmed for other shapes.**

`hasInteractiveAtoms` is true for `input`, `upload`, `color_input`, `actions`, and choices (`frontend/src/components/ai/cardAnswers.ts:7-8`; `AIUISpec.vue:329-339`). The default “Looks good” button is shown only when it is false (`AIUISpec.vue:212-218`). A lone multi-select choice never auto-submits (`:413-431`), so without an actions row it can collect selections but never send them. The final step of a multi-question form with choices has the same problem. Upload-only and color-only cards have no Enter shortcut and can also dead-end. An `actions` atom with an empty `buttons` array incorrectly suppresses the fallback.

The server rejects empty choices and empty overall UI but does not enforce a usable finish action (`builder/ai/agent/tools/conversation.py:45-65,83-103`). The tool description asks the model to add actions (`:194-203`); a prompt instruction is not a renderer invariant.

**Small fix:** normalize cards so every answer-collecting form has a usable final submit action, including malformed/missing action arrays. Give actions and answers stable IDs; do not depend on the model remembering a button. Add renderer tests for single/multiple choices, empty actions, upload-only, and color-only cards.

### F16 — P2: Answer collapsing can hide the user's important free-text qualifications

**Reproduced.**

`cardAnswers()` guesses structured answers from free text. If a card has one question and no exact label match, it treats the first line—truncated at the first colon—as the entire answer (`frontend/src/components/ai/cardAnswers.ts:71-77`). The panel hides the full next user message whenever **any** answer was inferred (`frontend/src/components/BuilderAIChatPanel.vue:583-588`). The card also replaces the whole form with the inferred answer summary (`AIUISpec.vue:4-11`).

For example, replying `Poster, but change this: keep all prices in euros` shows only `Poster, but change this`; the actual instruction disappears from the visible transcript. On a multi-question card, matching one labeled answer can hide other unmatched lines or qualifications. The backend still stores and sends the original content, so this is display/traceability loss, not proof that the model loses it.

**Small fix:** only replace the user bubble when the reply was generated by this exact card and all content is represented. Preserve free-text additions visibly. Persist `{card_id, question_id, option_id, value}` alongside full text instead of parsing human prose to decide what can be hidden.

### F17 — P2: Card drafts and asset selections are not durable, and escape hatches can land on the wrong step

**Reproduced for step grouping and selected-photo payload; draft loss confirmed by state ownership.**

- Answers, uploads, color changes, and step index exist only in local component refs/reactive objects (`frontend/src/components/ai/AIUISpec.vue:299,355-363`). They are persisted only after the whole form becomes a chat message. Refresh or switch away/back discards a partially completed discovery form; a successfully uploaded image can survive on the server while its selection disappears. This is particularly costly for the requested multi-step personalized brief.
- The grouping algorithm queues non-question atoms for the **next** question (`:279-296`). `[photo choices, upload, brand input, actions]` becomes `[[choices], [upload, input, actions]]`, although the comment promises upload stays with its photo question. Single-select picks auto-advance (`:419-427`), so the upload alternative is encountered on the next question rather than beside the choice.
- A single option reply carries the exact image URL and description (`:405-415`); the multi-question collector submits only option labels (`:440-447`). The original persisted card often still contains those URLs (`builder/ai/agent/tools/conversation.py:179-187`), so the model may infer the right asset. However, the actual answer payload has lost its direct asset identity, and inference becomes ambiguous with duplicate labels or a truncated context window.

**Small fix:** stable card/question/option IDs; group each question with its explicit supporting/alternative controls; store draft answers per session/card, including uploaded asset IDs and touched/default color provenance. Submit selected option IDs and asset URLs directly. Start with tab-local draft recovery if server draft persistence is too large for the first patch.

## Product findings against the requested experience

These are source-backed design gaps, not claims from live model sampling.

### P-UX1: The first-run suggestions encourage a generic example build, not discovering the user's business

`BuilderAIChatPanel.vue:592-629` explicitly makes each suggestion a complete brief with invented names, locations, palette, tone, and sections. `useSuggestion()` prefills it rather than immediately sending (`:707-710`), an important safeguard. But after Send, the prompt explicitly says a detailed brief goes straight to build (`builder/ai/prompts.py:114-115`). Thus the easiest beginner path bypasses the personalized questioning the user wants. It also offers motion in a starter prompt (`BuilderAIChatPanel.vue:629`) while the default product prompt otherwise says pages should be still unless requested.

Replace default starters with personal intent choices: “Help me find a direction,” “Build for my business,” “Use a reference I like,” and “Improve this page.” Ask for the real name, purpose, audience, primary visitor action, and available assets, with sensible skips. Keep the fictional examples in an explicitly labeled inspiration/demo area.

### P-UX2: Layout choices are mostly verbal concepts; the user cannot actually compare the visual direction

The prompt requests concept names and one-line descriptions, explicitly avoiding color decorations for layout options (`builder/ai/prompts.py:116`). The renderer displays image/color decorations only when supplied, otherwise label and description (`AIUISpec.vue:103-122`). There is no deterministic structural thumbnail or rendered mini-layout for the named concepts. The server's validation error even mentions `font` and `svg` decorations (`builder/ai/agent/tools/conversation.py:54-55`) that this choices renderer does not display.

Use a few curated, code-rendered layout thumbnails with the user's name, sample copy, palette, and type pairing. A split layout, editorial grid, and product stage should look different before any full build. This need not involve paid image generation or building three full websites. Show why each fits their audience and let “this direction, with that color” become a structured refinement.

### P-UX3: “One card with everything, then build” is not enough guidance for uncertain users

`builder/ai/prompts.py:115,125` mandates one bundled card and no plan/review step; typography is never a question (`:117`). Each visual step is optional in code: Next simply increments the index (`AIUISpec.vue:311-314`), so the final Build action can submit only its own label when nothing has been filled (`:437-487`). The model then has to resolve omissions despite being told not to repeat questions.

Offer two explicit modes: **Guide me** (default for an uncertain first build) and **Build from this brief** (for a user who already has a clear brief). In guided mode, show a concise, editable direction summary before mutation: real brand, target audience, primary action, chosen visual sample, content gaps. The final action should clearly mean “Build this direction.” Do not add approval friction to small edits or an explicitly complete, authorized brief.

### P-UX4: Personalization is conversational context, not a durable, scoped design brief

`AISession.CONTEXT_WINDOW` is 10 (`builder/ai/session.py:16`), but the query counts **message rows**, not ten user/assistant pairs (`:184-193`): roughly five exchanges in an ordinary chat, less with status messages. There is no separately stored approved brief or design-direction state in this session flow. Early discovery decisions therefore age out unless the model happened to save them elsewhere or the built page reflects them.

Durable memory helps, but it is site-global: all facts are fetched without user/page/project scoping, and every chat can add/delete them (`builder/ai/agent/tools/memory.py:17-26,30-60`). This is explicitly intended in the tool description (`:66-73`), so calling it accidental cross-chat storage would be inaccurate. Nevertheless, a site containing several brands or users has no provenance UI, scoped preference model, or “forget what this chat learned” semantics. Deleting the transcript does not delete those facts.

Create a small durable brief on the page/project: identity, audience, goal, tone, content, chosen direction, palette/type roles, reference assets, and source/confirmed status. Distinguish site-wide defaults from this brand and this page. Surface what Bob remembers and let the user correct it. Whether unrelated memories actually degrade output needs a controlled, model-free fixture first and then explicit evaluation authorization.

## Failure scenario matrix

| Scenario | Actual behavior/path | Evidence status | Priority / finding |
|---|---|---|---|
| Send while switching A → B | Request goes to A; B's late read replaces its visible turn | Reproduced | P1 F1 |
| Send again during completion reload | Reload erases new optimistic messages | Reproduced | P1 F1 |
| Refresh during active text turn | No pending assistant; future live text has nowhere to render | Reproduced | P1 F2 |
| Open same running chat in second tab | No durable run hydration; live bubble missing, initially looks idle | Confirmed / same reproduced mechanism | P1 F2 |
| Disconnect through final complete/card/error | No reconnect reconciliation; activity may remain stuck | Confirmed missing path; transport delivery not simulated | P1 F2 |
| Miss tool batch, then manually edit/save | Stale local tree can overwrite server draft | Confirmed path; real socket/DB interleaving not executed | P1 F2 |
| Two tabs send before worker starts | Both prompts persisted/queued; context bound to wrong “last row” | Reproduced | P1 F3 |
| Acceptance response lost, user retries | No request ID; duplicate run is possible | Confirmed protocol gap; lost response not integrated | P1 F3 |
| Stop a queued run | UI says inactive; worker clears cancellation and starts | Reproduced worker ordering + confirmed API path | P1 F4 |
| Cancel while a duplicate worker starts | Duplicate clears cancellation before rejecting its lock | Reproduced | P1 F4 |
| Provider stalled for 20 seconds after Stop | Client claims inactive without server confirmation | Reproduced | P1 F4 |
| Revert after >10 AI snapshots on page | Old handle offered; chat can truncate before missing snapshot fails | Confirmed | P1 F5 |
| Revert while another tab's run owns page | No shared lock/revision check; worker can overwrite restore | Confirmed concurrent path | P1 F5 |
| Truncation fails but snapshot exists | Page still restored; transcript retained | Reproduced | P1 F5 |
| Stop/error after partial committed edits | Kept edits lack chat Revert handle/debug history | Reproduced metadata loss | P1 F6 |
| Revert an existing script on a live/shared page | Public script changes before publishing draft blocks | Confirmed hook/file path | P1 F7 |
| Apply same pending action in two tabs | Both can apply; sample records and continuations can duplicate | Confirmed race; DB not exercised | P1 F8 |
| Apply in A, navigate to B before response | Phantom running turn created in B | Reproduced | P2 F9 |
| Observe second build from another session | Previous YAML offset makes new stream look duplicated | Reproduced | P2 F10 |
| Emoji in streamed YAML | Python/JS lengths diverge; next chunk dropped | Reproduced | P2 F11 |
| Offline send with attached mock and blocks | Text restored; image/scope lost on retry | Reproduced | P2 F12 |
| Delete chat with queued/running worker | Messages removed; worker can keep editing page | Confirmed | P2 F13 |
| More than 20 chats on one page | Older sessions absent from picker; no pagination | Confirmed | P2 F13 |
| Change model then Apply a card | Continuation can run original session model | Confirmed | P2 F14 |
| Multi-select/color/upload card lacks actions | Controls collect data but no usable submit | Reproduced multi-select; confirmed others | P2 F15 |
| Free-form answer with colon/extra constraints | Collapsed answer hides qualification and full user bubble | Reproduced | P2 F16 |
| Refresh halfway through discovery | Unsaved answers/step/upload selection disappear | Confirmed component-local state | P2 F17 |
| Photo choices + upload + next question | Upload is grouped with next question | Reproduced | P2 F17 |
| Beginner sends a suggested example brief | Fictional details satisfy triage; personalized flow bypassed | Confirmed configured intent; model not sampled | Product P-UX1 |

## Additional risks and limits of confirmation

- **Manual edits during AI work / multiple users:** Redis page locks are acquired by AI workers, while ordinary page saves submit the full tree (`frontend/src/stores/pageStore.ts:361-389`). Local autosave suppression is not a server-wide revision check. Realtime is user-targeted (`builder/ai/agent/loop.py:493-497`), so another user's editor does not necessarily mirror these changes. Lost updates are a credible consequence, but I did not execute a real database/socket interleaving or audit every Frappe document-save conflict rule. Add expected-revision checks at the authoritative write boundary.
- **Worker failure before the protected loop:** API-key resolution, runner initialization, page loading, and `build_messages()` can fail outside `run_turn()`'s inner exception handler (`builder/ai/agent/loop.py:1191-1211,1506-1509`). A credential removed after admission or a missing page can leave only a persisted user prompt and no terminal event. The missing recovery protocol is confirmed; exact queue failure/status behavior was not integration-tested.
- **Terminal commit and lock release:** `run()` releases locks in `finally` (`loop.py:1181-1189`), while some final writes rely on the surrounding job transaction. Another worker could acquire before that surrounding commit. This needs a controlled Frappe transaction test; the review does not claim measured lost writes from that precise window.
- **Pending-action replay and stale cards:** typing an ordinary follow-up after a pending action makes the card no longer the last message, so its Apply/Skip controls disappear (`BuilderAIChatPanel.vue:191`). Backend state remains `pending_action` unless explicitly acted on. Treat superseded actions explicitly, and show whether a question was answered, skipped, or replaced rather than inferring state solely from message position.
- **Unmount cleanup is incomplete:** `AIChatController.unmount()` only detaches socket handlers (`:998-1001`), leaving session reads, send continuations, render/complete/cancel timers, and the canvas quiet timer alive. Some callbacks mutate shared page/build state. A cross-page navigation failure is plausible; exact router/component lifetime timing was not exercised in a browser. Cancel timers and invalidate all ownership tokens on disposal.
- **Input/schema resilience:** card sanitation validates top-level kinds and some option shapes but not a complete control schema (`builder/ai/agent/tools/conversation.py:83-138`). Some bad shapes can throw or render empty labels; `safeSrc()` accepts any leading `/`, including protocol-relative URLs (`AIUISpec.vue:490-493`). This is not presented as a demonstrated security exploit. Validate expected arrays/strings and supported URL origins before rendering.
- **Actual design quality:** no live paid models, screenshot sessions, or human preference evaluations were run. Prompt intentions are not proof of good personalized output. The confirmed product mismatch is in the entry flow and available visual comparison, not a claim that every generated site looks generic.

## Tests inspected and safe checks executed

### Existing tests inspected

- `builder/ai/test_session_api.py:11-54`: lazy reads, reopening a spoken session, first-send creation with queue/model dependencies mocked. No queued concurrency, cancellation, refresh, or switch tests.
- `builder/ai/test_locks.py:7-73`: acquisition/exclusion, stale-token release, held checks, guards, key separation. These establish useful lock primitives, not request admission or turn lifecycle.
- `builder/ai/test_agent_jobs.py:20-55`: secrets stay out of job arguments, missing resume key, worker-side key resolution.
- `builder/ai/test_pending.py:39-58,61-186`: persistence of card trace/timeline, action permissions, chat privacy, and page deletion cleanup. No two-client action consumption test. Some tests intentionally create DocTypes and explicitly note that creation commits (`:32-36`), so I did not run them on the user's site.
- `builder/builder/doctype/builder_ai_message/test_builder_ai_message.py:7-8`: metadata/markup serialization regression.
- Frontend `frontend/vitest.config.mts:8-10` discovers `src/**/*.test.ts`; current tests cover plugin context/loading, registry, and settings. No checked-in `AIChatController`, `AIUISpec`, `cardAnswers`, or Bob realtime lifecycle tests were found. The Cypress landing smoke test is not coverage for these behaviors.

### Executed offline reproductions

Artifacts:

- `/tmp/bob-review-repros.cjs` — transpiles the actual controller and card script with the checkout's root TypeScript/Vue dependencies; injects mocked resources/stores/timers; no network/DOM/site writes.
- `/tmp/bob-review-repros.py` — AST-extracts selected actual source functions/methods and executes them with in-memory/mocked dependencies; it does not import Frappe or initialize a site.

Commands:

```sh
node /tmp/bob-review-repros.cjs
python3 -B /tmp/bob-review-repros.py
```

Results: **13/13 TypeScript defect reproductions and 6/6 Python source-extracted defect checks passed.** Here “passed” means the assertion reproduced the defective behavior, not that Bob's normal behavior passed regression testing.

TypeScript cases: switch/send overwrite, completion/send overwrite, refresh losing streamed text, cancel-watchdog false inactivity, foreign stream retaining offset, Unicode offset mismatch, attachment loss on failure, resumed turn in wrong chat, restore despite truncation failure, missing selected-photo URL in collected reply, multi-select dead end, upload grouped under next question, and collapsed answer losing qualification.

Python cases: queued cancellation cleared, duplicate worker clears cancellation, cancellation omits an existing snapshot pointer, error omits that pointer, two queued submissions both accepted, and history excluding the wrong “current” row.

The first TypeScript harness launch looked for dependencies in `frontend/node_modules` and failed module resolution; it was rerun successfully using the already-installed root `node_modules`. No packages were installed and no repository test files were added. No claim is made that the full suite or a browser end-to-end test passed.

## Small-first design and implementation roadmap

### 1. Close immediate recovery holes without a rewrite

Keep the existing controller, stores, resource calls, and components. Add explicit request ownership checks around session hydration, confirmation resumption, error/complete handlers, and unmount; block sends during a selected-chat transition. Restore the full failed-send envelope. Persist snapshot/steps/debug on every terminal path. Stop swallowing revert/deletion errors. Remove the false “inactive” timeout and “live page won't change” promises.

Add focused controller tests based on the reproductions, plus card tests for a usable final submit and free-text preservation. Fix the Unicode convention and add a generation identifier to stream state. These are small, separable changes with immediate user benefit.

**Acceptance:** no stale response replaces a newer turn; no control reports completion without evidence; interrupted edits keep their Revert link; user text and attachments survive failure.

### 2. Add the minimum durable turn protocol

Introduce a small persisted turn record or equivalent explicit fields, linked to session and triggering message: `turn_id`, `client_request_id`, `state`, chosen model, start/finish timestamps, result/message IDs, snapshot, and page revision. States should distinguish queued, running, waiting for user, cancellation requested, cancelled, completed, and failed. A session can still hold a normal chronological transcript; the protocol need not replace it.

Reserve a turn atomically at API admission; make retries return the original result. Workers and realtime events carry the turn ID; cancellation targets it and survives queue delay. Bind history to the triggering message instead of discarding whichever row is newest. Make pending-action consumption and continuation creation idempotent.

**Acceptance:** two-tab sends have one deliberate policy; retry cannot duplicate a run; Stop works before worker startup; every accepted request eventually has a discoverable terminal/waiting state.

### 3. Reconcile clients and make Revert trustworthy

Hydrate current turn state and page revision on load, reconnect, and foreground. Render a pending assistant consistently in every tab. Fetch authoritative state on event gaps; apply operations only to the matching page/revision and dedupe by event/operation identity. Protect full-tree user saves with revision checks.

Move Revert into one validated server operation with locking, snapshot availability, and explicit scope. Start by fixing block/history consistency and expired-handle behavior; then address shared scripts/tokens as versioned dependencies instead of implying draft isolation they do not have. Define deletion while running and notify other tabs.

**Acceptance:** close/reopen or disconnect/reconnect reaches the same transcript and page as a continuously connected client; Revert either succeeds coherently or changes nothing within its declared scope.

### 4. Make discovery feel personal before making it more autonomous

Replace fictional default briefs with intent starters and a “Guide me” default. Use the existing card atoms to collect a compact business brief, with “not sure / help me choose” and optional skip states. Persist form drafts and a small durable brief with clear user-picked versus suggested values. Show progress in user terms: identity → audience/goal → visual direction → content → build.

Maintain a fast path for users who explicitly ask to execute a complete brief, and for small edits. Do not force an onboarding questionnaire into every conversation.

**Acceptance:** a beginner can start from “a bakery” without inventing a prompt, resume half-finished answers, and recognize their actual business details in the resulting brief.

### 5. Add visual choice with cheap, deterministic previews

Build 2–3 structurally distinct, code-rendered direction thumbnails from the existing design vocabulary, populated with the user's name, sample content, chosen palette, and candidate type pairing. Reuse the card UI and existing Builder rendering where practical. No need for three full generated sites or image-model calls.

Show the tradeoff in one sentence (“editorial story first,” “product discovery first,” “local visit first”). Support changing palette or one preference without throwing away the entire direction. Show an editable summary and an explicit “Build this direction” action for guided mode.

**Acceptance:** users can point at a visual layout they prefer instead of guessing what an art-direction label means. Their choice survives refresh and reaches generation as structured brief state.

### 6. Measure output against the brief, using fixtures before paid evaluation

First create deterministic conversation/transport fixtures for the matrix above. Add product fixtures for a local business, portfolio, product launch, and a page matching an existing site. Verify that real names, offerings, audience, CTA, explicit colors, references, and selected images survive into generation inputs and through subsequent edits.

When model evaluation is separately authorized, measure first-choice satisfaction, unnecessary/repeated questions, personal-detail retention, mobile layout quality, time/cost to accepted direction, and how often users need Revert. Keep improvements driven by those outcomes rather than adding more prompt rules alone.
