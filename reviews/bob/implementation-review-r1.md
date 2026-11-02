# Bob backend implementation review — integration recheck

**At the final recheck, the Revert, startup-error, stale-reaping, checkpoint-metadata, and strict-YAML findings are fixed. Two P2 findings remain below, both in the newly introduced ToolSavepoint boundary. Older-Frappe preview fallback is now restored. No remaining P1 finding was confirmed.**

Read-only review of `/home/t3run/builder`, branch `feat/bob-design-workflow`, HEAD `a112a3e6aea1f9e712c75cdb9aeb713009467a90`. Read `AGENTS.md` and `reviews/bob/flow-server-contract.md`. No app edits, commits, spawned agents, site initialization, DB/Redis mutations, provider calls, or public-instance actions.

## Remaining actionable findings

### 1. P2 — A plugin load failure now rolls back a savepoint destroyed by its own commit

**Evidence:** integration snapshot `builder/ai/agent/loop.py:1097–1109`; `builder/ai/transactions.py:17–18`; unchanged `builder/ai/agent/tools/plugins.py:63–78, 117–130`.

`load_in_editor()` explicitly commits the plugin before asking the browser to load it. `describe_report()` legitimately returns a string beginning `FAILED` when the browser reports an exception, problems, or no registered surfaces. The new `run_handler()` treats that result as an uncommitted failure and invokes `ToolSavepoint.rollback()`. The SQL savepoint no longer exists after commit. That exception enters the generic handler exception branch, which calls rollback on the same nonexistent savepoint again. The entire model turn fails instead of receiving the plugin error and repairing it; the plugin has already been installed.

**Reproduction:** the final mock probe implements the documented database rule that commit destroys a savepoint. A handler that commits and returns the actual `FAILED: installed, but it did not load in the editor.` prefix produces `SAVEPOINT does not exist`, with **two rollback attempts**. This is a simulated SQL boundary, not a live MariaDB reproduction.

**Fix:** make ToolSavepoint aware of transaction settlement; skip rollback and stale callback restoration after an explicit commit. Preserve the tool's diagnostic result so the model can repair the installed plugin. A broader alternative is removing the early commit and moving editor confirmation to a separately persisted continuation, but that is not required for this scoped fix. Add an explicit-commit-plus-FAILED regression case; successful plugin loading does not exercise this path.

### 2. P2 — Savepoint cleanup leaves failed events in an already-existing realtime buffer

**Evidence:** `builder/ai/transactions.py:10–29`; supplied bench `frappe/realtime/__init__.py:80–103`; `frappe/model/document.py:1943–1963`.

Frappe registers one `flush_realtime_log`/`clear_realtime_log` callback pair when the transaction's first after-commit event is queued. Later events append to the same mutable `frappe.local._realtime_log`. If this log already exists when a tool starts, ToolSavepoint sees the existing callbacks as prior callbacks and retains them during rollback, but it never restores the log's contents. A failed document save/tool can therefore contribute events that are published when the surrounding round commits, despite that tool's database effects having rolled back. The preexisting log is normal here: a prior tool or the pre-tool Revert snapshot can already have queued document notifications.

**Reproduction:** initialize the log with a prior successful event and its flush/clear callbacks; take ToolSavepoint; append a failed event; rollback. Both events remain in the buffer. The final probe records `['prior successful event', 'rolled-back document update']`.

**Fix:** snapshot and restore the transaction-local realtime log along with callback state, while preserving events from before the savepoint and respecting explicit transaction settlement. Add a test where the log and its callbacks predate the failed tool; testing only newly added callbacks misses this case. Ordinary callback/client-op cleanup passes the mock recheck.

## Resolved findings verified during integration

- **Older-Frappe preview compatibility: fixed on final reread.** `tools/preview.py:140–151` now catches missing native APIs via ImportError, calls the existing renderer/service fallback, and explicitly labels requested geometry unverified. `complete` is also false for that fallback. This closes the reproduced missing-module failure. This last change was checked statically; no old-Frappe browser/service was run.

- **Revert ownership (original P1): fixed.** Current `api.revert_to_message()` commits restore plus history truncation inside the page guard, or rolls back inside it on failure. The mock order is `acquire → restore → truncate → commit → release`; the failure order is `acquire → restore → rollback → release`. This addresses the previously identified cross-session handoff window. No real two-connection Revert test was run by this reviewer.
- **Worker startup failure projection: fixed.** `run_agent_job` now persists a status message to the run's stored session with `status:error` and its exact `runId`, then commits. Mocked missing credentials confirm the failed row and run-scoped assistant message. This closes the case where normal hydration removed the queued spinner without showing why it failed.
- **Stale reaping versus a new claim: fixed.** `AIRun.active()` now rereads the run with `for_update=True`, rechecks status, and recomputes heartbeat expiry before marking interrupted. Mock stale queued observations followed by either a fresh running row or a completed row cause no interrupted write. Real MariaDB snapshot-conflict/retry behavior was not rerun.
- **Crash checkpoint metadata: already fixed before the captured baseline.** The initial interim note was based on an earlier live read and is withdrawn. The 06:35:17 snapshot already merges saved run metadata into the interruption message. A mock reaper preserves `revertSnapshot`, operations and token/debug metadata in both the run and message.
- **Strict authoritative YAML: fixed.** `persist_page()` now calls `expand_page_yaml(..., strict=True)`; malformed YAML raises before persistence. Mocked persistence confirms the strict flag; the actual PyYAML parser rejects malformed input while the preview parser retains its lenient default. This is separate from the generator's cancellation/finish-reason gate.
- **Uncommitted handler rollback: partially verified.** Both an exception and a returned FAILED result remove added callbacks, execute new rollback cleanup, and discard newly queued client operations in mocks. The two remaining boundary gaps are findings 1–2 above.

## Other reviewed boundaries and limits

- `lock_request`, user-scoped request IDs, queued admission, row claiming, durable outbox payload, dispatch deduplication, run-scoped cancellation, owner/page checks at admission/startup, and request-ID hydration were inspected. No additional actionable finding is asserted for these paths; this is not a substitute for the owner's live concurrency test.
- Current frontend `RunEvents` uses a set of seen sequence numbers rather than a monotonically increasing high-water mark, so a lower-sequence after-commit batch is not rejected merely because higher-sequence live text arrived first. This is deliberate and appropriate. There is no claim of durable event replay or a fully ordered event journal; events remain notifications with database reconciliation.
- A mock compaction exercise with **12 rounds, two tool calls per round, screenshot messages, and repeated compaction** retained three complete tool rounds and no orphan tool results. Existing tests cover simpler pairs. No paid provider request validated the compacted transcript.
- Generation now requires `finish_reason == 'stop'` and a post-stream cancellation check before persistence. Cancellation remains cooperative between stream chunks/tools; this does not prove a blocked provider call aborts immediately.
- The runtime remains **synchronous RQ**, with configured `builder_ai_queue` or `default`, a 600-second job timeout, and 40-round loop cap. The worker remains occupied during model, image, research and preview waits. A provisioned dedicated queue isolates that occupancy; the code alone does not adopt Flow's async daemon or guarantee normal-worker availability.
- BuilderClientScript's immutable file versions and removal of `commit=True` were inspected. Savepoint callback cleanup matters for rollback of newly created script files. Real filesystem/SQL rollback and screenshot capture were not exercised here.
- The implementation owner reports the new AI-script prefix routes only AI-installed scripts through a smaller read-only, user-scoped, network-free execution namespace; existing scripts retain their original path. The dispatch and new integration-test coverage were inspected, but this reviewer did not exhaustively audit the new sandbox or independently certify the public deployment.

## Exact source and test evidence

The checkout changed during review. Two immutable copies disambiguate evidence:

1. `/tmp/bob-implementation-reviewed-snapshot/manifest.json`: **2026-11-01T06:35:17.328067Z**, full source copies/SHA-256 hashes for the requested backend files, Run doctype, tests, frontend controller and event helper. `tracked.diff` records the inspected tracked changes; untracked implementation files are copied separately.
2. `/tmp/bob-implementation-reviewed-final/manifest.json`: **2026-11-01T06:39:41.059728Z**, integration recheck copies of runs, API, loop, new transactions helper, page writer, plugins, screenshot renderer, brief/artifact/conversation/images. Remaining-findings references use this snapshot unless stated otherwise. At 06:40:32, API and loop had changed again; the original open findings were still present on reread. A final reread then verified the preview fallback and narrowed the remaining list to the two ToolSavepoint findings. Transactions.py and the plugin commit/FAILED path were unchanged at that check. Subsequent edits are outside this report until explicitly rechecked.

Executed from `/home/t3run/bob-test-deploy/bench/sites` with `/home/t3run/bob-test-deploy/bench/env/bin/python`:

- `/tmp/bob-implementation-review-probes.py` → `/tmp/bob-implementation-review-probes.json`.
- `/tmp/bob-implementation-review-final-probes.py` → `/tmp/bob-implementation-review-final-probes.json`.

These compile the named **actual source bodies via AST** and supply isolated Frappe/transaction/provider doubles. They do not import/initialize a site or open DB/Redis/network connections. The final probe additionally uses the installed PyYAML parser. Assertions passed; several assertions deliberately confirm the reported defects, so successful execution is not a clean implementation verdict.

`test_run_lifecycle.py`, `test_runtime_boundaries.py`, related test/diff sections, and the bench transaction/realtime implementation were read. The owner reports **88 actual-site tests passed**, including eight new integration-boundary tests covering real script-file/callback cleanup, Revert locking, crash metadata, startup failure, read-only data-script alias mutation, and assets. The new integration test source was read; its callback test verifies newly added callbacks and pending client ops, but does not test an already-existing realtime buffer or a tool that explicitly commits before returning FAILED. Those reported suite passes and `/tmp/bob-concurrency.py` success were not independently rerun. No app changes or commits were made by this reviewer.

Last source check: 2026-11-01T06:42:51.529311+00:00; exact preview/test/transaction/plugin copies recorded in `/tmp/bob-implementation-reviewed-final/last-check-manifest.json`.
