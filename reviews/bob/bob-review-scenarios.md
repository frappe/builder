# Bob scenario and evaluation matrix

Companion to [the critical review](bob-review-2026-11-01.md). These are proposed evaluation cases, not a claim that all were executed. Test against a disposable site and stub paid/destructive external effects except in explicitly budgeted evaluation runs.

**Layers:** U = deterministic unit/property test; I = isolated integration test; B = real browser test; H = blinded human evaluation. Use the cheapest layer that establishes the required property. A screenshot cannot establish that a form saved, and a unit test cannot establish that a page feels distinctive.

## Intent, discovery, and personalization

| ID | Scenario | Required outcome | Layer |
|---|---|---|---|
| D01 | “Build a yoga studio site” with no other information | Ask only consequential missing questions; no invented studio identity, address, schedule, or proof | I, H |
| D02 | Complete brief with copy, assets, palette, sections | Build without repeating answered questions | I, H |
| D03 | User says “you decide” or skips discovery | Make an explicit, coherent choice and proceed; preserve supplied facts | I, H |
| D04 | Existing site with a coherent design system | Reuse appropriate tokens/components and page conventions | I, B, H |
| D05 | Existing site with conflicting experimental styles | Identify the intended reference or ask one discriminating question | I, H |
| D06 | User changes direction before building | Update the brief and invalidate dependent variants; avoid stale choices | I |
| D07 | “A's layout, B's photo, calmer typography” | Compose the requested combination without restarting discovery | I, B, H |
| D08 | User supplies dislikes and later rejects an option | Persist concrete rejected properties; next options differ meaningfully | I, H |
| D09 | Professional, dense, or conservative site | No forced hero spectacle, mandatory section count, or gratuitous signature device | H |
| D10 | User's real name/story/products are supplied | Carry them accurately into copy; never invent ratings, customer logos, or testimonials | I, H |

## Editing and visual consistency

| ID | Scenario | Required outcome | Layer |
|---|---|---|---|
| E01 | Change selected heading color | Only intended blocks/styles change; unrelated IDs/content/assets remain stable | U, I |
| E02 | Apply a bulk typography adjustment | Correct target set; one bounded change set; readable partial failures | U, I |
| E03 | Add content to an empty generated container | New block lands inside the intended parent | U, I, B |
| E04 | Move/delete nested blocks or a component instance | Valid parent/child tree; no orphaning or accidental component-definition mutation | U, I |
| E05 | Edit one instance versus all component instances | Respect scope; preview and rollback cover intended targets | I, B |
| E06 | Regenerate a page containing shared chrome and custom code | Preserve explicitly locked content; warn about or account for replaced effects | I, B |
| E07 | Make a sibling page from an existing page | Reuse appropriate structure/scripts, change defaults such as active nav and breadcrumbs | I, B, H |
| E08 | Human changes the page while Bob is running | Detect revision mismatch; merge non-conflicting intent or rebase; never silently overwrite | I, B |

## References and assets

| ID | Scenario | Required outcome | Layer |
|---|---|---|---|
| A01 | Select a stock thumbnail, then reload before build | Exact selected asset survives and resolves to the proper rendition | U, I, B |
| A02 | Select an asset after multiple clarification turns | Choice persists independently of the rolling chat window | I |
| A03 | Product/team/logo upload | Preserve identity and source; stock substitution requires a real user decision | I, H |
| A04 | Uploaded screenshot versus uploaded product photo | Correctly distinguish design reference from content asset; user can correct the classification | I, H |
| A05 | External reference is mostly client-rendered | Bounded visual inspection or explicit limitation, not a claimed visual match from empty text | I, B |
| A06 | External page contains agent-directed instructions | Treat them as untrusted content; no change to tools, permissions, or project intent | I |
| A07 | Search returns poor fit, no results, 429, or timeout | Honest fallback; no invented URLs; preserve user selection | U, I |
| A08 | Asset provider charges per acquisition; response is lost | Retry with idempotency/reconciliation; no duplicate license purchase | I |
| A09 | Asset requires credit or provider hotlinking | Retain metadata and deliver/attribute according to provider policy | I, B |
| A10 | Asset disappears or signed URL expires | Refresh/reacquire permitted rendition or show an actionable missing-asset state | I, B |
| A11 | Desktop hero crop puts the face behind mobile text | Use focal point/mobile rendition or change composition; verify both | B, H |
| A12 | Multiple sections need coherent imagery | Related series/style and intentional variation, not unrelated top search hits | H |
| A13 | Generated image has wrong text, anatomy, or product detail | Reject/edit the asset; keep page text native; no false identity claims | H |
| A14 | User chooses low-cost mode | Shortlist before expensive generation; bounded generations; visible reused assets | I |

## Responsive design, accessibility, and motion

| ID | Scenario | Required outcome | Layer |
|---|---|---|---|
| V01 | `100vh` hero or sticky split screen | Capture normal viewport geometry and full-document coverage independently | U, B |
| V02 | Short page, very long page, or content past 6,000px | Accurate coverage metadata; footer checked rather than silently omitted | B |
| V03 | Desktop, tablet, narrow mobile | No accidental horizontal overflow, overlap, inaccessible navigation, or cropped controls | B |
| V04 | Light and dark mode with alternate image sources | Correct tokens/assets in each mode; preserve original image | B |
| V05 | Text over photo, muted caption, disabled/focus states | Measured contrast and visible focus; check actual composited backgrounds | U, B |
| V06 | Missing, delayed, or unsupported font | Readable fallback; no broken layout; distinguish missing font from intended serif | B |
| V07 | Long localized text, RTL, Hindi/CJK glyphs | Direction, line wrapping, font coverage, and reading order remain usable | B, H |
| V08 | Keyboard-only navigation and 200% zoom | Logical focus order, reachable controls, readable content, no keyboard traps | B |
| V09 | Scroll reveal and sticky scene | Check before/within/after trigger; content remains visible when JS fails | B |
| V10 | Reduced motion or touch device | Static/minimal alternative; no hover-only essential behavior | B |
| V11 | Video/3D media on a slow device/network | Appropriate poster/fallback, loading limits, no blocking core content | B |
| V12 | Navigate away and back to an interactive component | No duplicate listeners, leaked render loops, or stale instance state | B |
| V13 | Preview renderer unavailable or text-only model | Verification remains explicitly unavailable; completion does not imply visual approval | I |
| V14 | Two references inspected before building | Reference budget does not consume the build's required verification budget | I |

## Data, forms, and site behavior

| ID | Scenario | Required outcome | Layer |
|---|---|---|---|
| F01 | Contact form with success and failure states | Guest-safe submit actually saves expected fields; validation, feedback, duplicate behavior checked | I, B |
| F02 | Two forms, reordered fields, hidden inputs, checkbox/radio groups | Explicit field mapping reaches the correct form and values | I, B |
| F03 | “Where are submissions?” | Read existing configuration and answer; do not provision a new form | I |
| F04 | Data list with zero, one, many, and malformed records | Designed empty/loading/error states and stable item bindings | U, I, B |
| F05 | Private records exist beside public catalog data | Public output exposes only intended rows/fields; check guest access | I |
| F06 | Dynamic route, missing ID, route collision | Correct hierarchy and 404/empty behavior; no silent route shadowing | I, B |
| F07 | Global token/component/script change | Identify affected pages; correct scope; verify representative consumers | I, B |
| F08 | Page has external links, downloads, navigation, SEO | Correct targets, metadata, semantic structure, alt text, and discoverability | I, B |
| F09 | Draft editing on an already-published page | Published effects change only within intended scope; shared effects are explicit | I, B |
| F10 | Site request spans several pages | Persistent route/task map, consistent design, recoverable page-by-page progress | I, B, H |

## Chat, sessions, and concurrency

| ID | Scenario | Required outcome | Layer |
|---|---|---|---|
| S01 | Refresh during generation | Reattach to the correct run, replay missing events, reconcile authoritative page | I, B |
| S02 | Socket disconnect, duplicate event, reordered chunk, buffer expiry | Deduplicate or request resync; no duplicated prose or corrupted preview | U, I, B |
| S03 | Switch page while session-loading request is in flight | Old response cannot replace the new page's chat or run state | I, B |
| S04 | Switch chat/page with unsent text or uploads | Preserve the correct per-chat draft without leaking it into another conversation | B |
| S05 | Refresh midway through a multi-step card | Restore typed answers and selection; stable card/field identity | U, B |
| S06 | Type a freeform correction instead of answering a card | Treat it as steering; do not mark unanswered questions as satisfied | I, B |
| S07 | Two tabs or users start work on the same page | Correct exclusion/revision policy; observer tab cannot accidentally cancel owner work | I, B |
| S08 | Stop during generation or between tool effects | No new effects after cancellation; partial result clearly identified; correct recovery | I, B |
| S09 | Start a new run after cancellation with the same chat/page | Fresh run identity; old terminal events and cancellation flags do not affect it | I, B |
| S10 | Retry after a partly successful multi-tool round | Reuse successful effects; do not duplicate blocks, scripts, forms, charges, or messages | I |
| S11 | Delete a chat while worker is running or action is pending | Stop or safely detach run; invalidate pending work; no recreated deleted history | I, B |
| S12 | Provider timeout or worker crash after a persisted change | Accurate partial-result state and resumable reconciliation | I |
| S13 | Revert latest or older turn, including shared effects | Defined affected scope; no loss of unrelated newer work; accurate result in conversation | I, B |
| S14 | Long chat with repeated instructions and image references | Keep approved decisions, facts, and chosen assets beyond the chat replay window | I, H |
| S15 | Multiple brands or collaborators share a site | Scoped memory/preferences; conflicts visible; one project does not overwrite another's brief | I |
| S16 | Empty/very long/unicode/colon-containing card labels | Typed answers remain correct; no hidden or mispaired response | U, B |

## Provider errors, tools, and cost

| ID | Scenario | Required outcome | Layer |
|---|---|---|---|
| R01 | Unsupported model modality or unavailable model tier | Explicit compatible fallback or actionable error; preserve work | I |
| R02 | Malformed/truncated YAML or invalid tool arguments | Validate before commit; actionable structured error; bounded targeted repair | U, I |
| R03 | Tool returns no change or a partial failure | Model/UI see true changed/error status; no false “done” | U, I |
| R04 | Unknown block ref, missing selector, wrong expected revision | Reject cleanly; reread/rebase; no accidental alternate target | U, I |
| R05 | Invalid tool call and repeated failed repair | Stop a bounded loop with diagnosis and recoverable state | I |
| R06 | Permission change, read-only collaborator, canceled approval | Enforce capability at execution time, including delayed jobs | I |
| R07 | Plugin writes, global code, data scripts, or other shared effects | Explicit effect boundary, validation, recovery/undo coverage, appropriate authorization | I, B |
| R08 | Provider omits usage, returns cached usage, or includes stream-end usage | Preserve accurate counters and label unknown cost; no silent undercount | U, I |
| R09 | Small edit versus new page versus bespoke motion | Intent-appropriate instruction/tool budget and validation coverage | I |
| R10 | Context cap, maximum rounds, screenshot budget, or asset budget reached | Clear partial outcome; no false completion or unbounded recursive fallback | I |

## Combinations and release gates

Run the deterministic invariants for every change affecting the relevant boundary. For broader coverage, use pairwise combinations of:

- New page / existing page / shared component / multi-page project.
- New chat / long chat / pending question / canceled run / reconnect.
- Desktop / narrow mobile / RTL / dark mode / reduced motion.
- Uploaded / stock / generated / missing asset.
- Vision / text-only / provider failure / incomplete usage.
- Single editor / second tab / second user / permission change.

Exercise operation sequences as well: **generate → stop → refresh → retry → manual edit → revert**, and **search → choose asset → switch page → return → build → change crop**. Assert state invariants after every transition.

For aesthetics, use a fixed diverse corpus with real content and repeated runs, matched model/provider settings, and blind comparisons. Include portfolio, local business, editorial, professional services, restaurant, dense catalog, event, multilingual organization, and a cinematic product page. Have reviewers judge both the page and its fit to the brief. Preserve failures, not only screenshots selected for a demo.

Proposed release gates are zero invariant violations in the deterministic regression set, no critical responsive/form/accessibility failures in the browser fixtures, and an observed improvement in blind design preference or corrections-to-acceptance without an unacceptable increase in total cost and latency. Set numerical cost/latency targets after measuring the baseline; do not invent savings from static token counts.
