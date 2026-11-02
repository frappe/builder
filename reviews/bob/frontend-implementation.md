# Bob frontend implementation handoff

Implemented in shared `/home/t3run/builder`, branch `feat/bob-design-workflow`, 2026-11-01. Read AGENTS.md and reviews/bob/session-findings.md, plus /tmp/bob-tool-implementation.md and /tmp/bob-assets-contract.md as requested. No backend or other owners' source files edited. No subagents, commits, paid calls, installs, site changes, build, or deployment. Final build/deployment remains root-owned.

## Implemented

### Session/run lifecycle

- Sending invalidates pending session reads before creating the optimistic turn. Explicit session switches disable submission; late history/terminal reads cannot erase a later send. Reads and asynchronous confirmation/cancellation/revert/send callbacks are bound to page/session intent and disposal.
- Each send retains an immutable envelope and stable UUID across retries with unchanged payload. The envelope includes model, theme, card display text, block attachments, image data/preview/name, prompt, page and session. Failed saves and failed/ambiguous admission restore the complete composer. An ambiguous retry skips saving the old canvas again before reusing the same admission UUID.
- Integrated root's optional get_ai_session(request_id): an accepted first request can be recovered without resubmitting api.run. A nonexistent request cannot select an unrelated latest chat. Recovery preserves a subsequently edited composer, including when the newly created session gets bound.
- Tab-local composer, retry envelope and selected-session persistence via sessionStorage. A deliberately selected blank chat stays blank during polling. Storage errors/quota failures leave in-memory state usable.
- Hydration constructs a pending assistant from active_run. Reconciliation retains the pending assistant ID, live text, reasoning/timeline and cancelling state when the same run remains active.
- Single in-flight reconciliation; activity polling every 5 seconds, idle polling every 15 seconds, failure backoff capped at 30 seconds. Mount, socket connect, browser online and returning to foreground reconcile. Session reload plus authoritative page reload recovers missed terminal/tool events. A read in flight does not overlap another polling read. Page refresh is deferred while editing a component.
- Realtime events require matching run IDs. Individual (run_id, seq) deduplication deliberately does NOT use a global high-water mark, so lower-numbered after-commit tool batches arriving after live text still apply exactly once. Old runs cannot finish or alter a newer turn. Foreign-session canvas events validate their active run separately from current chat state.
- Generation buffers are scoped by run_id + generation_id, with UTF-16 offsets, gap recovery, retired-generation protection, and guards against late get_active_build responses reviving a completed/replaced generation. Foreign-session generations reset offsets too. Quiet time triggers reconciliation rather than declaring a run finished.
- Cancellation sends session_id + run_id and hydrates server status even when queued cancellation has no realtime terminal event. Removed timeout-driven false "no longer active" claims. Cancellation failures are surfaced and permit retry.
- Confirmation responses remain bound to their originating session. No invented resumed placeholder: durable active_run determines whether the continuation still runs.
- Chat revert makes exactly one api.revert_to_message request, uses returned messages, and only reloads the page. It never calls restoreSnapshot. Expired-snapshot/server errors are shown and propagated; chat/page stay intact. Confirmation wording no longer promises that shared scripts cannot affect live pages.
- Unmount invalidates reads and sends, removes reconnect/foreground listeners, stops watchers and timers, clears stream rendering, and releases canvas suppression.

### Cards and assets

- Photo replies use asset_url before image and retain the description, inventory identity and provenance in single, multi, and multistep replies. Concise display labels remain separate.
- Exact selection marker: `[asset: <asset_id>]`. Page-ready URLs use `[image: <original-url>]`. Preview-only / requires-acquisition / explicitly empty asset_url choices instead include `[preview only; license/download and upload original]` and their source URL; they never relay the preview URL as a chosen image.
- Preview-only choices show **Preview only** plus **Open original library page**, with the external link separate from the selection button. Backend owns selection persistence and acquisition policy; no new endpoint args or purchase/download calls were added.
- Multistep card drafts persist in localStorage by message ID: step, selected indices (bound to the persisted card), inputs, uploaded URLs, chosen colors and touched/default-color provenance. Selected assets are recovered from the same stored card options and sent by stable asset_id.
- Cards lacking a usable action now get a fallback submit on the final step, including multi-select-only cards and empty action rows.
- Existing DOMPurify pattern reused for static SVG option previews. Only geometry/text and limited attributes survive; scripts, links, remote resources, CSS, event handlers, animation, embedded HTML and remote fill/stroke paint are removed.

### Tool dispatcher integration

- normalizeStyles preserves normalized null keys. applyStylePatch deletes explicitly unset properties in base/mobile/tablet maps, including state-prefixed and custom CSS properties.
- Each canonical attribute patch clears both attributes and customAttributes first; only non-null values are assigned to the correct store.
- Existing per-operation update_block dispatch applies the backend's accepted canonical patches in order.
- Removed YAML-final persistence fallback and deleted the client JSON-as-Python repeater compiler. YAML now only renders a temporary preview. Canonical generate_page uses server-expanded blocks; data_script is mirrored locally and page data is re-evaluated without a second persistence request. No chat/generation caller remains for pageStore.applyRepeaterDataScript.
- YAML preview reconstruction honors explicit icon default unsets, responsive styles, attributes and compact references.

## Focused validation

From `/home/t3run/builder/frontend`:

```sh
node ../node_modules/vitest/vitest.mjs run \
  src/components/AIChatController.test.ts \
  src/components/ai/cardDraft.test.ts \
  src/components/ai/cardPreview.test.ts \
  src/components/ai/AIUISpec.test.ts \
  src/components/ai/toolDispatch.test.ts
```

**53/53 tests passed across 5 files.** Uses installed root Vitest 3.2.7, Vue, TypeScript and jsdom; no installation. Controller tests execute the actual class with mocked resource/store/transport boundaries, controlled promises and fake timers. Card tests execute actual compiled SFC handlers; SVG tests run the actual sanitizer in jsdom. Tool tests execute the actual dispatcher, normalizer and YAML converter with minimal block/store doubles.

Covered: switch/send and completion/send races; refresh and reconnect rehydration; live-text retention during a read; missed terminal recovery; exact-event dedupe with reordered lower-sequence tool batches; stale run terminal/tool rejection; first-send held events; stable retry identity and full attachments; failed save; first-send request lookup/remount; cancellation before acceptance/queued/no-terminal and still-running timeout; confirmation after switching/after completion; atomic revert and expired snapshot; foreign generations and UTF-16 gap recovery; post-terminal buffer rejection; explicit blank-chat selection and edited-draft preservation; asset markers/original-vs-preview URLs; persisted card choices; SVG sanitization; style/attribute unsets; canonical generation-only persistence; icon unsets; run-scoped affected-item metadata persistence.

- `@vue/compiler-sfc` script + template compilation passed for BuilderAIChatPanel.vue and AIUISpec.vue.
- `git diff --check` passed for all owned changes.
- Owned files formatted with existing Prettier config. Installed Prettier reports the existing `tailwindConfig` option as unknown; formatting succeeds.
- Whole-project `tsc --noEmit --pretty false` remains red with **38 diagnostics in unowned existing files** (frappe-ui .ts import-extension config, block.ts/editor typing and related files). **Zero diagnostics in changed/added frontend files.** Log: `/tmp/bob-frontend-tsc.log`. This is not a claim that the whole project's typecheck passes.
- No final bundle build or real-browser/site integration was performed, per root ownership.

## Integration notes / limits

- Frontend work is complete and ready for root's final build/browser smoke. No blocker or pending frontend step remains. Root's get_ai_session(request_id), active_run, run_id/seq, cancellation, atomic revert and generation identity contracts are used directly.
- Root's final metadata contract is integrated: update_session_message_metadata receives explicit session_id + run_id, and affected-item metadata is overlaid by persisted metadata.runId while the write completes. A dedicated regression verifies that the write targets the completed run, not the last assistant. No optional API follow-up remains.
- Realtime text lost before hydration is not reconstructible from the current active_run API; hydration supplies a pending assistant and preserves text already received. Terminal persisted messages converge on reload.
- Browser storage is best-effort; large pasted-image data can exceed sessionStorage quota. Such attachments remain preserved in memory for failed-send retry. Cross-device draft recovery is not implemented.
- These tests establish deterministic frontend logic and contract handling, not live database/socket/provider/browser deployment behavior.
