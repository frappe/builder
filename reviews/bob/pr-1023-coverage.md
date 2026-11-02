# Bob review coverage — draft PR #1023

Updated 2026-11-02 for [frappe/builder#1023](https://github.com/frappe/builder/pull/1023), based on `develop` at `a112a3e6aea1f9e712c75cdb9aeb713009467a90`. The [previous coverage audit](pr-1023-coverage-2026-11-01.md) describes the earlier `7b7cafe` implementation and is preserved as historical evidence.

This revision implements the remaining original defect fixes and the guided-design, media, verification and async-runtime experiment. It does **not** establish that every possible site or all 82 review scenarios pass end-to-end, or that generated sites match MotionSites aesthetics. The implementation, deterministic evidence and unperformed evaluations are separated below. Review sources and reproducible experiment instructions are now included in the PR.

## Original discussion

| Goal | Delivered implementation | Evidence boundary |
| --- | --- | --- |
| Token efficiency | Small stable core, lazy specialist policies/tools, result artifacts/cursors, retained brief, context/output/run reservations, repair limits, per-attempt usage/cost ledger | Static initial text ~4,748 tokens vs original ~21,719 (~78% lower). Not measured cost/time to accepted output; unknown usage/prices stay unknown. |
| Less apparent “dumbness” | Typed choices preserve qualifications; facts/decisions/assets survive history; exact selected layout promotion; stale writes rejected; strict candidate and repair boundaries | Model reasoning and aesthetic quality require the supplied live corpus and blind rubric. |
| Separation of concerns | Brief/project, artifacts, media, revision/effects, event journal, browser verification, policies and runtime modules; short-lived Frappe execution slices | One coordinator and writer remain. No graph database or autonomous agent swarm was added. |
| Personalized design | Personal-intent starters, editable Brief/Assets/Versions workspace, desktop native layout previews with optional section details/tweaks, original assets, optional recipes and selective generated art | No mandatory design style/section count. A model can still make poor choices; no blind preference study was run. |
| Real image previews | Actual WebP screenshots of editable Builder layouts, cached by brief/page/spec revision; applying a direction reuses the exact blocks | These are not SVG sketches rasterized into pictures. Optional generated concepts are separate and preview-only. |
| Central asset provider | Magnific discovery and confirmed acquisition, entitlement configuration, pending receipts/reservations/reconciliation; free libraries, contact sheets, original IDs, focal crops and attribution | No paid calls made. Account/API redistribution entitlement and actual production charges require provider validation. |
| Chat/session handling | Durable admission, retries/cancellation, cursor replay, deleted-session tombstones, search/offset history, typed cards and preserved free text, revision-checked Revert | Browser drafts remain device-local. Ambiguous external effects need reconciliation; older stream journals expire after seven days. |
| UX/hand-holding | Contextual starters and optional next-step chips; brief/facts/decisions, asset roles, versions, project pages, checks and spending in the workspace; frappe-ui dialogs/tabs | Chips prepare editable prompts without sending; their context uses lightweight reply rules. User can proceed directly or defer a decision. See the [UI follow-up](ui-2026-11-02.md). |
| Flow/server sessions | Separate async provider execution for chat, generation and research, plus async OAuth refresh; concurrent independent reads; durable events/receipts | Compatible native daemon, not a Flow dependency install. Ordinary blocking tools occupy bounded daemon threads; confirmations occupy their web request. |
| Exhaustive representative scenarios | All 82 IDs mapped to outcomes/tests/layers; deterministic runner, browser fixtures, pairwise plan generator, six-case live corpus and blind review exporter | Current trace: 70 cases have partial invariant evidence; 12 require evaluation. No whole-scenario pass is inferred. Pairwise plan and live corpus were not run. |
| Multi-page building | Durable route/dependency map, shared project brief and scoped memory; idempotent draft-page creation; evidence required to mark tasks done | Recoverable page-by-page execution, not an unattended all-pages batch. |

## Original numbered findings

These rows map the 45 findings from the three detailed reports, including overlaps. “Implemented” describes the correction; evidence and remaining boundaries follow each group.

| Source findings | Correction/status |
| --- | --- |
| Runtime F1; capability F02/F03 | Document and field permissions, target-page reads/previews, shared component/token/script write permission and permissioned save lifecycle. Implemented with restricted-user and tool tests. |
| Runtime F2/F3; capability F01 | Incomplete calls/final YAML cannot execute; empty candidates and duplicate IDs are rejected; only server-accepted canonical patches reach the editor. The semantic gate does not certify design completeness or factual quality. |
| Runtime F4; capability F06 | Valid literal/nested repeater data, preserved wrapper data and bindings. Executable deterministic regressions. |
| Runtime F5 | Bounded results with permissioned artifact cursor reads and total-context reservations. A too-large irreducible request fails explicitly. |
| Runtime F6; session F6 | Usage/timeline/recovery checkpoints retained through failure, cancellation and terminal cards. Missing provider usage is explicit. |
| Runtime F7; capability F13 | Normal viewport dimensions with separate capture height; native raster directions and checks; fallback/unverified reporting. Real Chromium evidence. |
| Runtime F8; session F3/F4 | Durable admission/claims, request deduplication, queued cancellation and active-run ownership. Mocked network waits tested against real DB/journal state. |
| Runtime F9; session F17 | Persistent brief, assets, typed facts/decisions and scoped memory; card drafts and committed answers survive recovery. Unsubmitted drafts are browser-local. |
| Runtime F10; session F14 | Selected model persists across confirmation/resume; unavailable models/capabilities fail explicitly. |
| Runtime F11 | Supplied operation order, deferred terminal remainder and bounded adjacent independent reads. No writes cross a terminal or dependency boundary. |
| Runtime F12; capability F08 | Codec/generation round trips retain IDs, component refs, props, scripts, binding extras and unknown preserved metadata. Explicit binding changes override old metadata. This is not proof for every legacy/custom field. |
| Session F1/F9/F10/F11/F12 | Stale-load/confirmation guards, run/generation identity, UTF-16 offsets and retry envelopes retaining attachments/selection. Focused controller tests. |
| Session F2 | Durable event cursor replay plus authoritative reconciliation after disconnect/refresh. Journal gaps/retirement tested. |
| Session F5/F7; capability F07 | Atomic page/chat Revert, revision checking and shared receipts. Expired/conflicting snapshots preserve history. Confirmed external/schema/plugin/global effects deliberately block automatic Revert across that range. |
| Session F8 | Confirmation ownership/consumption and reconciliation state prevent ordinary duplicate application. Cross-system effects are not exactly-once transactions. |
| Session F13 | Active deletion is refused; deleted chats are tombstoned and other clients reconcile. History supports title search/offset pagination. |
| Session F15/F16 | Usable card submit paths, stable field/option IDs, unusual labels and visible free-text qualifications. |
| Capability F04 | New Bob data scripts use the viewer-scoped read-only namespace even when general server scripts are enabled. Existing manually authored scripts retain their prior contract. |
| Capability F05 | Savepoint/file/callback/realtime cleanup and committed-effect handling. Earlier transaction review findings remain fixed. |
| Capability F09 | Explicit unsets, attribute canonicalization, root/unsupported-operation guards and changed/no-op/rejected results. |
| Capability F10 | Component mirroring uses permissioned versioned saves; extraction retains page placement overrides. Existing page-script/data dependencies still require inspection when moving a component to another page. |
| Capability F11/F12 | Exact form name mappings, required validation, successful-control semantics, per-page scripts and reuse checks. Real guest/auth delivery, CSRF, duplicate-submit prevention, failure/retry and private-read denial passed. |
| Capability F14 | Browser diagnostics and ordered click/fill/keyboard/assert steps; tested reveal/tabs/disclosure recipes; reduced-motion/footer checks. Live form delivery, full screen-reader use, complex contrast and arbitrary external integrations are not certified by this verifier. |
| Capability F15/F16 | Candidate plugin staging, inspection, explicit activation, atomic registry replacement and disposal callbacks. Trusted plugin code is not sandboxed; undeclared side effects cannot be automatically cleaned. |

## Design and product findings

| Review item | Result |
| --- | --- |
| D1: incorrect viewport | Normal viewport metrics, bounded capture height and explicit fallback/partial reporting, with real Chromium evidence. |
| D2: inaccessible color defaults | Removed low-contrast muted defaults and added contrast diagnostics. Text over images, gradients, translucency and nonstandard color spaces still needs manual review. |
| P-UX1: generic premature building | Personal-intent starters and short consequential discovery; detailed briefs and explicit quick builds can proceed. |
| P-UX2: nonvisual direction selection | One to three real desktop raster candidates from native blocks, optional section crops and preview tweaks. Cards and Versions expose them; selection promotes the chosen artifact. |
| D3/P-UX3/P-UX4: lost personalization | Versioned brief, accepted/rejected facts/decisions, asset roles, pending questions and editable workspace. |
| D4: prescribed visual style | Removed mandatory section/type/style formulas and trend blacklists; relevant recipes remain optional. |
| D5: lost original identity | Stable original IDs/renditions/provenance persisted separately from thumbnail display. |
| D6: weak art direction | Shortlists/contact sheets, selected originals, focal crops, generated artwork/editing and credit delivery. Visual ranking/coherent series still depend on model/user decisions. |
| D7: text-only references | Bounded public-only raster reference rendering, headings/type/color evidence and explicit dynamic-content limits. Real public fetch/render passed. |
| D8: screenshots treated as proof | Separate reference/verification budgets, diagnostics and interaction assertions, revision-bound reports with manual checks. |

The proposed semantic PageSpec is represented by versioned native variant specs, canonical blocks, stable IDs, asset references and completeness/revision validation. There is no second universal compiler IR. Motion recipes are a small tested starting library, not a general 3D/video/scroll-scene authoring engine. Third-party MotionSites MCP/paid recipe access was investigated but is not bundled; arbitrary provider integrations require their own account and compatibility work.

## Evidence and next experiment

- **412 backend regressions**, **74 focused frontend tests**, **eight Chromium fixture groups** passed. Native Frappe Chromium passed five ordered disclosure/keyboard assertions. Real form database evidence confirmed three correct deliveries and guest denial. Async integration observed two simultaneous mocked provider waits, zero RQ jobs and prompt cancellation of a third silent wait.
- Public editor: login, raster MIME/decoding, desktop/mobile Versions, selected preview/source link, refresh persistence and real API Revert passed. Model run requests were blocked in the smoke browser. Existing provider configuration was preserved.
- Production build, lint/format and whitespace checks passed. TypeScript reports **37 existing diagnostics outside changed files**; the project-wide check is not clean.
- The temporary origin still receives the external Builder Hub catalog CORS error. It is reported rather than suppressed.
- No paid model/image/stock call, model-driven aesthetic evaluation or blind human comparison was performed by this validation. Evidence details: [implementation report](implementation-2026-11-02.md), [machine-readable summary](evidence-2026-11-02.json), [runtime setup](../../builder/ai/RUNTIME.md), [media configuration](../../builder/ai/STOCK_ASSETS.md), [acceptance and live experiment commands](../../builder/ai/acceptance/README.md).

The next measurable product question is whether users reach a personally acceptable page with fewer corrections, less elapsed time and lower total cost. The live corpus and blind review pack make that question reproducible; passing correctness tests alone cannot answer it.
