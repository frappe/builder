# Bob implementation and public experiment

Historical first implementation. See the [2026-11-02 implementation](implementation-2026-11-02.md) and [current coverage](pr-1023-coverage.md) for the subsequent raster, media, verification and async-runtime work. The statements below about untracked reviews, SVG previews and synchronous-only execution describe the earlier commit.

Implemented on `feat/bob-design-workflow`, based on updated `develop` at
`a112a3e6aea1f9e712c75cdb9aeb713009467a90`. Subsequently committed as
`7b7cafe794df09d1f2fc58597ccd80c7d9f622f8` and opened as draft
[PR #1023](https://github.com/frappe/builder/pull/1023).

The later [coverage audit](pr-1023-coverage.md) maps the original findings and
proposals to this PR, including unresolved defects and unimplemented work.
The review documents themselves remain local and are not included in the PR.

This delivers the first implementation of the audit's reliability, context,
visual-choice and asset recommendations. It does not claim the entire scenario
roadmap, Flow daemon migration, or demonstrated motionsites.ai-level output quality.

## Public test instance

- [Open Builder](https://slight-max-printed-worthy.trycloudflare.com/builder/).
- [Sign in](https://slight-max-printed-worthy.trycloudflare.com/login?redirect-to=%2Fbuilder)
  as `Administrator`.
- Private password location: `/home/t3run/bob-test-deploy/secrets/administrator-password`.
  Alternatively choose a password privately with
  `/home/t3run/bob-test-deploy/bench/env/bin/python /home/t3run/bob-test-deploy/scripts/set-password.py`.
  Do not paste credentials into chat.
- Configure an AI provider and model in Builder Settings before submitting real
  AI work. No model/provider credentials were copied or configured, and no paid
  model or paid stock API calls were made.
- Isolated database, Redis, web/realtime services and dedicated `builder_ai`
  worker. Existing `/home/t3run/frappe-bench/apps/builder` still points at the
  unrelated `builder-extensions` checkout.
- Cloudflare Quick Tunnel is temporary. Its hostname lasts while that tunnel
  process runs; services survive terminal disconnect, but are not supervised
  across host reboot. This is an experiment, not a production deployment.
- Schema migrated; recovery scheduler enabled after backend fixtures were removed.
  Final deployment evidence: [public-deployment.md](public-deployment.md).
  Service controls: `/tmp/bob-test-site-setup.md`.

## What changed

| Area | Implemented behavior |
| --- | --- |
| Durable runs | Request IDs deduplicate retries, including concurrent first sends. Queued/running state lives in a run row. An outbox retries dispatch after queue outages. Workers claim once and recheck user/page access. |
| Stop and recovery | Cancellation is run-scoped and survives the queued interval. Reconnect/polling reconcile authoritative messages/page state. Interrupted runs retain checkpoint usage, timeline and Revert metadata. Startup errors become visible chat messages. |
| Chat UX | Stale reads/events cannot replace a later turn. Failed sends preserve attachments and the original request envelope. Tab-local drafts and card answers survive reload. Generation buffers carry run/generation identity and UTF-16 offsets. |
| Revert | One endpoint restores the page and truncates chat together, committing while holding page ownership. Expired snapshots preserve both page and history. |
| Tool correctness | Only accepted canonical edits reach the editor. Null unsets agree across server/client. Repeater literals and nested data are valid. Forms preserve field names, required controls, checkbox/radio/multiple values and per-page connections. |
| Failure boundaries | Truncated calls and malformed final YAML cannot become executable edits. Provisional YAML never persists from the browser. Failed tools roll back new script files, pending operations, callbacks and realtime events. Explicitly committed plugin failures remain actionable. |
| Permissions | Document reads apply document and field permissions. New Bob-installed data scripts use a read-only, viewer-scoped namespace without network access, even with general server scripts enabled. Existing scripts keep their original execution path. |
| Persistent brief | Page-specific audience, goal, voice, content, constraints, selected direction, stage and bounded asset inventory survive rolling chat history and model changes. |
| Visual decisions | Prompts ask a few consequential questions, respect detailed briefs/quick-build requests, and offer two or three structural directions. Cards render sanitized static SVG compositions, photo choices, palettes and upload controls. These are design studies, not generated finished-page screenshots. |
| Assets | Original IDs/URLs/provenance survive selection and later searches. Opt-in Magnific discovery marks paid stock as preview-only; licensing/import is manual. Selected Unsplash use records its required download event. Known unacquired preview URLs are rejected from page mutations/generation. |
| Context cost | Ten initial tools plus a group loader replace the entire up-front catalog. Tool results and history are bounded; recent complete tool rounds remain paired. Brief facts survive compaction. Session titles no longer require another model call. |
| Visual checking | Normal desktop/tablet/mobile viewport geometry is separated from document screenshot height. Missing native support falls back honestly with geometry marked unverified. Screenshot tiles explicitly report partial coverage. |

Detailed implementation evidence:
[frontend](frontend-implementation.md), [tools/data](tool-implementation.md),
[stock configuration and provider contracts](../../builder/ai/STOCK_ASSETS.md),
[initial integration review](implementation-review-r1.md), and
[final transaction review](transaction-review-r2.md).

## Flow finding and architectural decision

The user's inference was correct: Frappe Flow performs provider waits in a
separate asynchronous daemon using `litellm.acompletion`. Frappe's submission and
callback requests stay short, and human-input pauses do not leave a running task
waiting. Tools still use web/RQ capacity when executed there. Restart restores
journal/paused state, not an interrupted provider stream or Python stack.

Bob in this implementation remains synchronous RQ. The public instance has a
dedicated AI worker, so its model waits do not occupy the general job worker;
each AI run still occupies that AI worker. Embedding Flow's Agent in RQ would not
change that. The Flow package reviewed requires Python >=3.14/LiteLLM 1.103.2,
while Builder supports Python >=3.10 and pins LiteLLM 1.95.1; no incompatible
dependency migration was made. A daemon adapter is a separate next change.

[Flow analysis](flow-session-review.md) and [proposed server contract](flow-server-contract.md).

## Validation

- **91 actual-site Python tests passed** against the isolated MariaDB/Redis bench:
  lifecycle, runtime boundaries, session API, jobs, artifacts, locks, LLM helpers,
  real permission/form setup and eleven integration regressions. Provider calls
  were replaced with a failing guard. `/tmp/bob-final-backend-tests.log`.
- **99 offline tool/data tests passed**, including generated form JavaScript in
  jsdom and repeater scripts under RestrictedPython. `/tmp/bob-tool-validation-final.log`.
- **25 offline asset tests passed**, including original identity, preview-only
  results, selection/acquisition preservation and no accidental network calls.
- **53 frontend tests passed**: controller races/recovery, card persistence,
  SVG sanitization, asset selection and authoritative operation replay.
- Real concurrent first-send probe: two requests produced one session, one run,
  and one user message. Real Chromium screenshot probe verified a 900px `100vh`
  hero plus a 400px footer captured at 1300px without stretching the viewport.
- Ruff lint/format, Python compilation and whitespace checks passed. Final
  isolated Vite production build passed. Whole-project TypeScript still reports
  **38 diagnostics in existing unowned files**, none in changed frontend files.
- Independent review found and drove fixes for Revert ownership, startup errors,
  stale recovery and transaction callbacks. The final narrow review found no
  remaining concrete defect in the two transaction fixes; eight isolated probes
  passed. This is scoped review, not a claim of exhaustive certification.
- Public browser checks verified password login, authenticated WebSocket,
  persisted SVG/asset cards, card answers surviving refresh, and Revert through
  the real API restoring both blocks and data script. To inspect cards without a
  model, the test intercepted only the browser's setup-ready flag; it did not
  configure a provider or call the run endpoint. [Deployment evidence](public-deployment.md).

The source-derived initial static context is approximately **14.7k text tokens**
versus the audit's **21.7k**, about **32% lower**, using `o200k_base` and compact
JSON tool schemas. This excludes dynamic page/history/image context and provider
serialization/caching. Loading more tool groups increases later calls. It is not
a measured billing reduction or proof of better generated design.

## Remaining experiment limits

- Live design quality, provider billing and complete model-driven builds need
  evaluation after configuring a provider. The scenario matrix remains an eval
  backlog; deterministic tests do not establish every website-building scenario.
- Discovery and direction choice are guided by prompts and a saved brief, not a
  rigid state machine. Generated raster design alternatives are not implemented.
- Paid inventory is discovery/manual import only. API account entitlement was
  not verified; no automatic license purchase or budget system is implemented.
- Browser draft storage is best-effort and tab/device-local. Live text lost
  before persistence cannot be replayed as a durable event stream.
- Cancellation is cooperative. A stalled provider call can still hold its AI
  worker until timeout; this is the primary reason to consider the Flow daemon.
- DDL-backed confirmations cannot be rolled back atomically. Consuming a
  confirmation prevents double application; a process crash during
  `action_applying` still requires inspection before retrying.
- Revert covers its captured page/script state, not all site-wide side effects.
  Shared scripts can affect other pages. Obsolete immutable script-file cleanup
  and automatic migration of old form/data scripts remain separate work.
- The compact codec is not a fully lossless serializer for every legacy/custom
  field. Older-Frappe fallback capture cannot certify requested viewport geometry;
  screenshot limits do not verify motion, keyboard use, or an entire very tall page.
- The external Builder plugin catalog rejects the temporary site's origin with
  a CORS error. Its fetch error remains visible in the browser; the Bob checks
  passed despite it. The full editor smoke is therefore not error-free.
