# Bob: critical review and experimental redesign

Reviewed on 2026-11-01 against `develop` at `a112a3e6aea1f9e712c75cdb9aeb713009467a90`.

## Verdict

Bob has a useful editing engine and a surprisingly broad toolset. Its central weakness is the contract between understanding the user, choosing a design, obtaining assets, building, and proving that the result works. Much of that contract currently lives in a large prompt and short-lived conversation state.

A better asset service should help substantially, especially with cutouts, coherent image sets, illustrations, video, and generated hero art. It will not independently fix composition, generic content, lost decisions, broken interactions, or unreliable previews. Build an asset-aware design workflow around the service.

The most promising experiment is: **a persistent brief, two or three visibly different buildable directions, a selected asset set, an editable draft, and evidence-based refinement**. Keep a fast path for small edits and users who already know what they want. Do not force every user through an interview or every edit through a design process.

This is a source review with focused deterministic probes, not a statistical evaluation of generated sites. I inspected MotionSites' public gallery and its public integration page; paid templates were not accessed. No paid image/model calls were made. Findings below distinguish code defects, product limitations, and proposals. Aesthetic improvements and token savings remain hypotheses to measure.

## What deserves to survive

- **The authoritative server tree.** The server persists the accepted tree and the canvas mirrors it. Streaming YAML is provisional display, rather than the only source of truth (`page_writer.py:1`, `agent/registry.py:6`).
- **Targeted edits and bulk edits.** Bob already distinguishes a small change from full regeneration. Preserve this distinction in every redesign.
- **Real components, scripts, data, forms, tokens, and settings.** This is more capable than a static landing-page generator. The machinery for reuse and actual form submission is valuable.
- **Visual question cards.** `present_ui` already supports images, choices, uploads, and colors. Extend it with persistent typed answers and design variants; a completely new chat renderer is unnecessary.
- **Vision and reference reuse.** Image attachments, image viewing, screenshot tiling, reference geometry, and matching existing site components are sensible foundations.
- **Bounded tools and provider adapters.** There are round/read/image limits, cache markers, model selection, usage accounting, guarded URL fetching, and tests. The next step is to make the bounds task-aware and the accounting complete. Despite older fast/heavy-model comments, the coordinator and generator currently use the same selected model (`loop.py:1201`).

## Execution and session findings that take priority

These are concrete implementation problems, not aesthetic opinions. The detailed evidence and isolated reproductions are in [runtime findings](runtime-findings.md), [session findings](session-findings.md), and [capability findings](capability-findings.md). Concurrency findings describe reachable interleavings, not their frequency in production.

| Finding | Consequence and evidence | First repair |
|---|---|---|
| **Rejected edits still reach the canvas** | Bulk updates can report `Applied to 0 of 1 blocks. REJECTED...`, yet the original rejected patch is forwarded and applied by the frontend. Reproduced with render-breaking moustache text. `agent/tree.py:448`, `loop.py:1035`, `toolDispatch.ts:294`. | Return canonical accepted operations and per-patch outcomes. Replay only accepted changes. |
| **Document permission checks are incomplete** | `get_document` checks the DocType, then serializes a named record without document/field-level checks. Reproduced using a synthetic denied record. `tools/data.py:79-122`. Shared-write authorization also varies by path. | Reuse the stronger permission-aware reader; authorize each actual target at execution. |
| **Truncated model commands can execute** | Incomplete tool JSON ending midway through a text value is repaired and used as an edit; `finish_reason=length` only produces a warning. `loop.py:783-828`. | Reject incomplete mutations, validate schemas, and recover through a bounded reissue. |
| **Broken generation can replace the page** | A bare `el: div` with empty `c` is accepted; YAML salvage can drop malformed heading text without a degraded result. `page_writer.py:432-545`. | Compile into a candidate artifact with completeness diagnostics before replacing a prior draft. |
| **Generated repeater data can crash rendering** | JSON `true`/`null` are interpolated into Python; wrappers can lose the repeater data shim. `page_writer.py:407-426,490-539`. | Normalize once, emit valid data, execute the shim in a test, and preserve existing data-script behavior. |
| **Form handlers corrupt ordinary inputs** | The generated script reads `.value` without successful-control semantics, so unchecked consent and radio choices can be wrong; the click path skips browser validation. Reproduced with the actual generated handler. `agent/pending.py:286-335`. | Explicit field mappings, correct checkbox/radio/multi-value serialization, submit validation, and guest browser tests. |
| **Late history loads erase a newer visible turn** | Sending does not invalidate an earlier session load; completion/switch responses can replace optimistic messages and select the wrong chat. `AIChatController.ts:358-407,660-687,853-863`. | Bind reads and writes to session/run ownership; discard stale responses before state mutation. |
| **Stop can be erased before execution** | A queued job has no running lock, so Stop reports inactivity; the worker later clears the cancellation flag before obtaining its lock. A duplicate worker can clear another run's Stop too. `api.py:223-237`, `loop.py:1161-1179`. | Durable queued run ID, idempotent admission, cancellation scoped to that run. |
| **Revert can delete history without restoring the page** | Chat truncation occurs first; snapshot restore is a second request. Only ten AI snapshots per page survive, yet old buttons retain expired handles. `AIChatController.ts:946-964`, `api.py:241-249`, `snapshots.py:17`. | One validated server operation with snapshot availability, revision checks, locking, and explicit effect scope. |
| **Failed/stopped work loses its recovery and cost metadata** | Normal success stores usage and Revert; cancellation/error paths store only status. Cards also omit some metadata. `loop.py:1147-1159,1343-1380`. | Finalize a run record on every exit, preserving partial effects, usage, and recovery references. |
| **Two tabs can apply the same pending action twice** | The endpoint reads pending status, performs the effect, then marks it applied without atomic consumption. Sample-data insertion can therefore duplicate records. `api.py:155-175`. | Idempotent action claim/result plus unique continuation. |
| **Script side effects escape draft/transaction promises** | Client-script hooks overwrite public files and commit internally. Revert's “live page won't change until you publish” promise is false for shared scripts. `builder_client_script.py:85-104`, `AIChatController.ts:952`. | Version/stage script assets; activate after commit; expose shared/public scope and remove the false guarantee. |

Additional significant defects include missing active-run hydration on reconnect, generation offsets mixing Python code points with JavaScript UTF-16 lengths, lost image/block attachments on failed send, unreachable old sessions beyond the history picker limit, model selection reverting on confirmation, dead-end cards without a submit action, lossy block readback, and plugin activation before meaningful validation. The appendices retain reproductions and suggested tests for each rather than treating them as one generic “session handling” issue.

Data-script safety also needs a real execution boundary: on server-script-enabled installations, the current source blacklist accepts aliases to effectful methods and helper calls such as mail. The review verified gate acceptance with mocks, not a live effect. Restrict the execution namespace and explicitly allow public data access; do not rely on a text blacklist to make a script read-only.

## Why Bob can appear unintelligent, and what the token numbers show

The implementation withholds or loses information a capable model would need. The replay window is **ten message rows**, roughly five ordinary exchanges, not ten full turns (`session.py:16,184-202`). There is no durable page brief. Current tool evidence reaches the generator largely through model-written prose, selected references, and run-local assets. Across an interview or several revisions, that makes repeated questions, forgotten decisions, or an inconsistent rebuild unsurprising.

Static source measurements with `tiktoken`:

| Payload | `cl100k_base` | `o200k_base` |
|---|---:|---:|
| Expanded agent system prompt | 11,044 | 10,971 |
| All 37 tool schemas as compact JSON | 10,711 | 10,748 |
| **Static coordinator subtotal** | **21,755** | **21,719** |
| Generation system prompt, separate call | 5,606 | 5,679 |

These are token counts of text, **not exact API bills**. They exclude provider schema framing, history, page content, images, tool results, and outputs; these encodings are not authoritative for every provider. Cache hits can reduce the billed input cost, but do not remove the text from context.

An illustrative nine-tool edit/inspection subset reduces tool-schema text by 62.6%, or the complete static coordinator payload by 31.0%, under `o200k_base`. That is a sizing experiment, not a guaranteed cost reduction or a sufficient catalog for every edit. Dynamic tool discovery must remain available.

The greater risk is unbounded dynamic context. A permitted synthetic `query_records` response with 100 capped code fields reached **306,102 text tokens** by itself; 100 long paragraph matches reached 83,206. These are stress fixtures, not measurements of typical sites. The loop appends the results and resends them without a central context budget. Cap total results, provide cursors/artifact handles, and reserve output space before the request.

There are further costs that the current counter cannot faithfully compare: research and title calls discard nonstreaming usage; failed/card/stopped runs lose accumulated metadata; retries occur at more than one layer; cache-write and per-phase costs are not a complete ledger. Improve measurement before judging the effect of a model switch or promising savings.

## Design and asset findings

### D1. The visual reviewer sees a different viewport from the visitor

**Confirmed; high priority.** `builder/ai/agent/tools/preview.py:21-43` renders at a height of **8,000px**, then tiles the resulting image. That is the CSS viewport height, not merely a full-page screenshot boundary. The same prompt recommends `100vh`/`90vh` layouts (`prompts.py:185-191`).

A browser probe using the same `min-height:100vh` hero produced:

| Measurement | Normal 1280 × 900 viewport | Bob's 1280 × 8000 viewport |
|---|---:|---:|
| Hero height | 900px | 8000px |
| Headline top | 431.5px | 3981.5px |
| Footer top | 900px | 8000px |

Only three 2,000px tiles are attached (`preview.py:35-36,67-84`), so this footer falls outside what the model sees. Viewport-based typography, sticky layouts, media queries, and scroll interactions can also be misrepresented.

**Change:** render in a real desktop or mobile viewport, then capture the document or bounded regions without changing the viewport. Record viewport, page revision, theme, coverage, and whether scripts ran. Test a `100vh` hero and sticky rail against the visitor preview. The legacy preview service currently receives no requested width or height (`html_preview_image.py:25-35`); its fallback must not be presented as verified mobile rendering.

### D2. The prompt prescribes inaccessible text colors

**Confirmed; high priority.** `prompts.py:171-176` mandates muted text at black/0.36 on light backgrounds and white/0.42 on dark backgrounds. On pure white and black respectively, those yield contrast ratios of **2.516:1** and **3.946:1**, below 4.5:1 for normal text. The light caption also fails 3:1 for large text.

**Change:** replace fixed opacity prescriptions with semantic text roles and measured contrast against the actual composited background. Treat image overlays and dark mode separately. Keep visible focus states, but validate their visibility rather than merely prescribing a replacement outline.

### D3. Discovery is a one-shot form, not an evolving design conversation

**Confirmed product behavior.** `prompts.py:114-125` requires all missing questions in one card, forbids spreading them across turns, and says to build once essentials are known. It already asks for personal details and imagery, so adding “ask questions first” to the prompt would duplicate existing instructions.

The form must choose downstream questions before it knows upstream answers. It asks users to choose named layouts from descriptions instead of showing what those layouts mean for their own content. It also forbids asking about movement unless users bring it up (`prompts.py:121,132`). This is a poor fit for a novice who wants a MotionSites-like result but cannot name parallax, a cutout, or a scroll scene.

**Change:** ask the next high-information question, show a small visual result, and let that response shape the next step. Usually one to three questions at a time. A supplied brief, existing design system, or explicit “you choose” should skip unnecessary steps. Selecting a direction should start implementation without an additional repetitive approval card.

### D4. Anti-generic instructions have become another design formula

**Confirmed policy; output frequency unmeasured.** The generation prompt defaults to 4–8 sections (`prompts.py:154`), a named layout taxonomy, exactly one signature move (`:194`), mandatory photo treatments (`:217`), and a large display/body ratio (`:177`). The brief can override defaults, but these are powerful repeated priors.

Those defaults can produce a recognizable Bob style: huge headline, decorative device, prescribed image treatment, repeated section count. A calm professional site, dense catalog, restrained architecture portfolio, or single-purpose form should not have to fight those defaults. Banning a font or a gradient is not a substitute for art direction.

**Change:** separate hard correctness rules from optional design recipes. Retrieve a small relevant recipe with examples and applicability constraints. Let the brief determine density, section count, typographic hierarchy, and motion. Evaluate specificity, hierarchy, rhythm, and task fitness rather than whether a page avoided a blacklist of fashionable elements.

### D5. Image selection loses the asset's identity and original rendition

**Confirmed data path; actual selection errors depend on subsequent model behavior.** Search results contain full-size `url` and `thumb` (`tools/images.py:19-82`). The prompt puts the thumbnail in a choice (`prompts.py:86,124`). `AIUISpec.vue:405-410` returns that same `option.image` as the “chosen image.” There is no asset ID resolving the choice to its original. The search inventory is only `ctx.found_images` for the current run (`loop.py:374-376`; `images.py:122-129`), while presenting a card ends that run.

After the answer, the next run can have only the thumbnail URL and textual card replay. It may recover an original through another search, but that is extra work and no longer guarantees the selected photograph. A low-resolution hero is a plausible consequence of this contract.

**Change:** choices carry `asset_id`; display uses `preview_url`; placement resolves an approved original or responsive rendition. Persist selected assets independently of the message window. Never make the model transcribe URLs to preserve identity.

### D6. Stock search is too weak to act as an art director

**Confirmed limitation.** `tools/images.py` takes query and orientation, returns up to six results from the first provider that returns anything, and remembers at most 24 results. It does not compare providers, persist licenses, rank subject placement, identify copy space, preserve a coherent series, or visually inspect a candidate contact sheet. Search-result descriptions are not proof that the product, crop, or scene is right.

The Openverse adapter retains a creator string but drops license/source metadata. The Unsplash adapter drops asset IDs, photographer profile links, and `download_location`. That prevents the current tool result from supporting the documented selection/download and attribution workflow on its own. “Commercial” search filtering is not equivalent to “no attribution or other conditions.”

**Change:** add a small asset service with search, visual shortlist, select, acquire, transform, and resolve operations. Enforce delivery/attribution requirements per provider. Owned uploads should be the first source for products, people, and brand identity; stock or generated work must not silently impersonate a real product or testimonial.

### D7. External design references are mostly read as text

**Confirmed limitation.** `tools/web.py:29-85` strips scripts, styles, SVG, and tags to return readable text. That helps business research, but cannot communicate composition, type scale, image masks, or an interactive scene. Bob can see uploaded reference images and its own site's pages; an arbitrary reference URL does not get equivalent visual understanding.

**Change:** add a bounded reference-inspection tool: desktop/mobile screenshot, selected region, extracted colors/type, key images, and, where requested, a short interaction trace. Store observations and the user's likes/dislikes, not the entire remote page in every prompt. External content remains evidence, not instructions to the agent.

### D8. Two screenshots cannot establish that a sophisticated website works

**Confirmed limitation.** Reference screenshots and generated-page screenshots share `MAX_PREVIEWS_PER_TURN = 2` (`preview.py:21,124-178`). Two reference reads can consume the entire budget before the new draft is inspected. The tool returns screenshots and a prose rubric; it has no click, scroll, keyboard, form assertion, console-error, or network-result contract. The inspected Frappe renderer can execute initialization scripts, so a preview is not inherently effect-free; Bob still receives only a still image, not evidence that the intended interactions work.

**Change:** separate reference-inspection and verification budgets. Use deterministic checks first and visual review of the changed regions second. Verify motion at meaningful states, including reduced motion and touch. When a check cannot run, mark the relevant behavior unverified instead of turning an attempted preview into a completion claim.

## The product flow I would build

### 1. Understand the task and preserve what is already known

Classify the request into an edit, new page, continuation, site extension, bug fix, or exploration. Read the current selection and relevant existing design system. Extract facts and unknowns into a persistent brief.

For a new site, the most valuable unknowns are normally the visitor, desired action, differentiator, available proof/content, and visual references. Ask only what changes a consequential decision. “Who should book, and why choose you?” usually matters more than “which shade of beige?”

Offer useful starting actions: **Describe your idea**, **Use my existing site**, **Start from a reference**, and **Explore a direction**. Make “you choose” a first-class answer. Expert prompts should proceed directly.

### 2. Establish a visual direction with buildable previews

Show two or three genuinely different compositions using the same real content: for example, an editorial story, an object-centered showcase, and a compact information-first layout. Each card should show a hero plus one representative section, a mobile crop, the proposed asset, and a short rationale.

Render these from actual Builder-compatible blocks in temporary variants. They need not be complete pages. The selected preview becomes the starting artifact, so the subsequent build does not reinterpret an unrelated image.

Support “A's layout with B's imagery,” “less playful,” “keep this photo,” and “show me something calmer.” Store the choice and the rejected characteristics. Keep a visible recommendation so a user need not act as an art director.

### 3. Build around assets, not around empty rectangles

Define asset roles before searching: hero product, portrait, location, detail crop, proof, background loop. A role includes subject, aspect ratios, focal point, palette, negative space, truth/identity constraints, and allowed sources.

Search cheaply, assemble a contact sheet, visually rank it, then fetch high resolution for the chosen assets. Show the hero at desktop and mobile crops. When photos cannot express the intended idea, generate or commission the missing artwork rather than repeatedly trying a loosely related stock search.

Lock selected assets and approved content. A typography adjustment should not replace the image; a mobile crop fix should not regenerate the page.

### 4. Build an editable draft in coherent sections

Use a semantic page specification with persistent section IDs, layout parameters, asset IDs, content roles, component references, and interaction requirements. Compile it through the existing block writer. Start with the hero and a representative section, check them, then extend the system across the rest of the page.

Reuse existing tokens and components. Allow fine-grained escapes for custom code where necessary, but expose their purpose and editable parameters. A full-page screenshot used as the final page would sacrifice responsiveness, accessibility, searchability, and normal editing.

### 5. Verify, explain the remaining choices, and refine

Check actual rendered desktop/mobile states, links, forms, fonts, images, keyboard access, contrast, overflow, and requested motion. Show the changed region or before/after comparison. Report what was checked and what remains unverified.

Refinement should target a named property or region: “more room above the title,” “same layout, stronger image,” “keep the hero, simplify below.” Ask for another decision only when it materially changes the result. Publish remains a separate user action unless explicitly requested.

## Generated mockups: useful, with a narrow role

Generating two or three raster design concepts can help explore atmosphere, material, imagery, and unusual compositions. It is less useful for evaluating real typography, responsiveness, forms, exact copy, or interactive behavior. A compelling mockup can promise a design that the block renderer cannot reproduce.

Use this ladder:

1. Existing assets and a small native preview first.
2. A low-resolution generated image only when the missing visual concept is the main uncertainty.
3. Choose a direction, then generate/edit the actual hero asset once.
4. Compose real headings, controls, and sections in Builder.
5. Compare the implementation against the selected concept and explain material differences.

Record model, input/reference asset IDs, prompt, dimensions, applicable usage terms, cost, and output revision. Cache by content and generation settings. Deduplicate retries. Avoid generating three complete high-resolution sites before the user has chosen a direction.

## Centralized asset provider recommendation

**Start an integration spike with Freepik/Magnific for the widest single-provider coverage.** During this review, `docs.freepik.com` redirected to the current Magnific API documentation, which documents stock photos/vectors/templates, stock video, image generation/editing, and video generation. The stock API explicitly lists asset pickers for design tools as a use case.

| Provider | Useful role | Decision |
|---|---|---|
| **Freepik/Magnific API** | Stock, vector assets, video, generation/editing behind one provider | Best first breadth experiment. Validate the intended Builder/multi-user license and account plan before committing. API generations consume credits; web-app “unlimited” allowances do not mean unlimited API calls. |
| **Shutterstock API** | Search, similar assets, image/video licensing and downloads | Strong paid alternative when licensed stock quality is the main requirement. Its API subscription/licensing flow is distinct from merely browsing the website. |
| **Adobe Stock API** | Curated commercial stock, similar-image search, licensed downloads | Attractive for an existing enterprise customer. Official documentation restricts API access to Stock for Enterprise; do not assume a normal individual subscription suffices. |
| **fal** | Multiple image/video/3D generation models through one integration | A useful generation backend when one asset provider's models are limiting. Model capabilities, prices, and usage terms need individual evaluation. It does not replace a stock licensing system. |
| **Cloudinary** | Renditions, focal crops, optimization, delivery | Complements acquisition. It is a media management/delivery layer, not a source of art direction or a stock catalog. Start with Builder files if that is sufficient. |
| **Pexels / Unsplash** | Low-cost photography | Keep for appropriate scenes. Pexels is already supported via configuration; I could not reverify its current docs because the public documentation returned 403. Unsplash's official API rules require provider URLs, attribution, and a download-event request on selection. |
| **Openverse** | Openly licensed imagery and fallback search | Useful with retained source/license/attribution metadata. Avoid silently treating every result as unrestricted stock. |
| **User uploads** | Actual products, team, locations, logos, proof | The most important source for a personalized site. Preserve identity; improve crop/background/lighting only within the user's intent. |

**Also investigate MotionSites' own MCP.** Its public integration page advertises access to a paid design-prompt library. This is a separate source of design recipes, not an asset-delivery service. Bob currently has an internal tool registry, so using it would require a server adapter or a compatible MCP client and authentication. Retrieve a few relevant recipes, translate them into Builder-native concepts, and measure fidelity. Do not inject the whole library into the system prompt or assume arbitrary React/WebGL examples become editable Builder blocks. Verify terms for an embedded multi-user product.

A useful adapter interface is:

```text
search(AssetBrief) -> AssetCandidate[]
inspect(asset_ids) -> contact_sheet + visual_metadata
select(asset_id, role, variant_id) -> stable selection
acquire(asset_id, project_id, idempotency_key) -> licensed Asset
transform(asset_id, crop_or_edit_spec) -> AssetVariant
resolve(asset_id, viewport) -> delivery URL + required attribution
```

An `Asset` needs provider/source IDs, preview/original renditions, dimensions, focal/crop data, license and attribution facts, delivery rules, generation provenance where applicable, and references to the pages using it. The tool returns short IDs; binary images and long metadata live outside the ordinary transcript. Some providers require hotlinking; others permit or require local acquisition. Do not force every asset through the same download policy.

## How to reach MotionSites-style capability

The public gallery shows typography-led pages, cutouts, moving backgrounds, scroll-driven scenes, and 3D presentations. This is a combination of composition, media, interaction design, and execution quality. More photos alone will not reproduce it.

Introduce a small library of **tested interaction components**: sticky product story, image-mask reveal, before/after slider, cursor-follow decoration, scroll-linked section transition, background video, and interactive 3D stage. Each should define controls, dependencies, performance expectations, cleanup on navigation, touch behavior, keyboard semantics where relevant, and a static/reduced-motion fallback.

A `MotionSpec` can name target IDs, trigger, start/end states, timing or scroll range, fallback, and assertions. The compiler maps supported recipes to known implementation paths. Bespoke effects can still use code, but should be isolated and tested, with their editable limits clear.

For ambitious work, show the tradeoff at the design choice: **still**, **subtle**, or **cinematic**, with concrete previews and loading/interaction implications. A user choosing a cinematic reference has supplied useful intent; they should not need to discover the phrase “scroll-linked animation” themselves. Keep content visible when scripts fail. Avoid hover-only access and forced motion on reduced-motion devices.

## Architecture: separate decisions, state, effects, and evidence

Keep one coordinator and one authoritative page writer initially. Specialist stages do not require an always-on swarm of agents. Most stages can be functions, retrieved recipes, deterministic validators, or bounded model calls.

| Boundary | Responsibility | Existing base to extend |
|---|---|---|
| Conversation/UI | Intent, questions, answers, progress, user choices | `AIChatController`, `BuilderAIChatPanel`, `AIUISpec` |
| Project state | Brief, references, constraints, chosen direction, selected assets | Session persistence plus small versioned JSON documents |
| Context builder | Relevant facts, changed tree slices, tool group, token budget | `AISession`, `AgentRunner.build_messages` |
| Design planning | Content hierarchy, composition, asset roles, motion plan | Generation brief and retrieved recipes |
| Compiler/editor | Validated operations against a specific revision | `BlockCodec`, `WorkingTree`, `page_writer` |
| Asset service | Search/acquire/generate/transform/deliver | Existing `images.py` adapters |
| Verification | Rendered checks and observed results | Preview tool plus browser/runtime probes |
| Run/effect journal | Idempotency, cancellation, recovery, undo scope | Locks, pending actions, snapshots, realtime events |

Start with typed, versioned JSON stored in Frappe; do not create a graph database or distributed service layer without evidence that it is needed.

Suggested records:

```text
ProjectBrief {
  revision, scope, audience, visitor_goal,
  facts[{key, value, source, confidence}],
  constraints, unknowns, approved_decisions, rejected_directions
}
DesignVariant {
  id, brief_revision, page_revision, composition,
  design_tokens, section_specs, asset_ids, motion_spec,
  desktop_preview, mobile_preview, feasibility, verification
}
Run {
  id, session_id, target_page_id, base_revision,
  intent, phase, status, budget, context_refs, last_event_seq
}
ToolResult {
  status, changed, effects, errors, warnings,
  created_artifact_ids, verification_refs, undo_coverage
}
```

Extend tool declarations with effect scope, permission requirements, idempotency, and reversibility. “Client/server/terminal” describes transport/control flow, but is insufficient to describe whether an operation changes a draft, shared component, public behavior, plugin runtime, or paid external asset.

Chat is the interaction history. The brief and decision records are the durable design state. A remembered business fact should include scope; a preference for one client or project must not silently become a rule for every chat on a site.

## Efficient tokens and better reasoning

Do not optimize for minimum tokens per request alone. Optimize **cost and time to an accepted, functioning page**, including discarded concepts, image generation, repairs, and user correction time.

1. **Measure the actual cost path.** Track ordinary/cached/cache-write input, output/reasoning tokens where exposed, tool latency, model retries, asset charges, browser work, and accepted/discarded artifacts. Separate measured provider usage from estimates.
2. **Scope instructions and tools to intent.** A spacing edit should not carry instructions for plugin writing, form provisioning, a full page's design taxonomy, and all provider configuration. Keep tool groups stable enough for useful cache reuse; dynamic filtering that changes every round can erase that benefit.
3. **Persist decisions instead of replaying every conversation detail.** Use a short brief, current decision delta, and a bounded relevant history. Summaries need references to source facts and decisions, not just fluent prose that can silently omit a constraint.
4. **Keep tree reads proportional to the change.** Selected subtree, ancestor layout, computed style summary, and relevant tokens normally beat serializing the entire site. Return result handles plus compact summaries; fetch details on demand.
5. **Generate one selected design.** Explore cheaply with small native variants or contact sheets. A full-page generation followed by a full rewrite is often more expensive than one well-placed question.
6. **Use deterministic validation before another model call.** Invalid selectors, missing asset IDs, empty bindings, broken links, overflow, and schema errors do not need a second creative model to diagnose them.
7. **Route by task and uncertainty.** A simple deterministic edit needs little reasoning; a bespoke visual direction or difficult repair may justify more. Preserve the user's model preference and escalate only on evidence, with bounded retries.
8. **Run independent reads concurrently; serialize conflicting writes.** Parallelizing token creation and other writes without a dependency model can make failures harder to recover. Concurrency needs effect scopes, not just tool-call batches.
9. **Bound verification by risk and coverage.** Two arbitrary screenshots is a poor budget. A targeted typography edit can be cheap; a new responsive page with a form and motion needs several distinct checks.

Provider caching semantics vary. The current official OpenAI documentation describes model-dependent boundaries, TTLs, cache writes, and usage fields. Keep stable prefixes where useful, implement each provider's supported interface, and inspect actual cache hit/write counters. A comment saying a prompt “stays a cache read” is not a measured guarantee, and cached tokens still have a cost.

## UX and session behavior to aim for

- Show **Exploring → Building → Checking → Ready**, plus the current useful action. Keep raw tool traces in an expandable detail view.
- Provide a persistent **Brief / Assets / Versions** area beside chat. Users should be able to see and correct what Bob believes without hunting through messages.
- Keep the composer draft per conversation/page, including unsent uploads. Persist in-progress card answers. Stable card/answer IDs should replace parsing labels and colons as state.
- Make Stop explicit: stop further work and keep an identified partial variant, or restore the prior accepted version. Never leave ambiguous partial changes disguised as a finished page.
- Give each run and each event an identity and sequence. Reconnect asks for events after the last acknowledged sequence, and reconciles against the authoritative run and page revision.
- Page switching changes the active view, not the target of a running job. Show its target page. A delayed result must never replace the newly opened page's chat.
- Retry should identify what can be resumed or reused and what will be charged again. Do not repeat a completed paid asset purchase or a form provisioning operation.
- Revert needs an honest effect boundary. If a turn also edited shared components, tokens, forms, or plugins, explain what is restorable and handle those effects explicitly.
- Distinguish project/site design facts from user preferences. Keep exploratory client brands from contaminating each other's memory.
- For multi-page sites, use a site map and ordered tasks with shared components. Do not pretend a one-open-page agent already has a reliable site-wide build transaction.

## Experiments and order of work

| Order | Deliverable | Evidence needed before expanding |
|---|---|---|
| **P0: trustworthy execution** | Correct viewport capture; typed tool outcomes; explicit run/revision identity; safe cancellation/revert; complete usage accounting | Deterministic lifecycle and effect tests pass; no false-success reports for known failing cases |
| **P1: better design decisions** | Persistent brief, typed card answers, asset IDs, two or three native direction variants, selectable hero assets | Blind paired reviews prefer the new outputs; fewer corrections; acceptable extra time/cost |
| **P2: acquisition and verification** | One paid asset adapter, generation/editing for missing visuals, deterministic responsive/accessibility/form checks | Selection survives refresh; licenses/delivery are correct; higher asset fit without uncontrolled spend |
| **P3: advanced interaction** | A small tested motion component library, runtime checks, motion-aware references | Real desktop/touch/reduced-motion tasks pass; output remains editable and fast enough |
| **P4: site-level work** | Shared brief/design system, route map, consistent pages, scoped memory and coordinated change sets | Cross-page changes and recovery preserve unrelated work |

The smallest useful experimental slice is **blank page → short brief → three hero directions using real assets → choose one → build → desktop/mobile check**. It exercises the central product hypothesis without rewriting all of Bob.

Compare against current Bob on the same prompts, model configuration, source assets, and starting pages. Include vague requests, detailed briefs, existing-brand extensions, and later corrections. Log every paid call; run several samples for generative tasks rather than treating one attractive screenshot as proof.

Judge: brief fidelity, distinctiveness, typography/composition, asset fit, factual integrity, responsive behavior, accessibility, interaction correctness, editability, correction count, total cost, and time to acceptance. Use blind human comparisons for aesthetics. Automated or model judges can triage, but cannot substitute for user preference or a functioning form.

## Scenario coverage

The companion [82-case scenario matrix](bob-review-scenarios.md) covers creation, editing, references/assets, responsive and interactive behavior, data/forms, sessions, permissions, failures, and cost. No finite list proves “all websites.” Use representative fixtures, pairwise combinations of orthogonal conditions, and sequences of operations with invariants. Add each real regression as a fixture.

Important invariants are stronger than a pile of happy-path screenshots: a canceled run cannot start a new effect; a stale run cannot overwrite a newer revision; an asset choice resolves to the same original after refresh; a failed tool never reports a completed change; shared edits and rollback have explicit scope; unverified behavior stays visibly unverified.

## Sources and verification boundaries

All source-code findings refer to the pinned commit at the top. File/line references in this document are evidence locations, not claims that a live provider run reproduced every possible outcome.

Validation performed:

- **109 existing Python tests passed in an offline harness**, with site dependencies stubbed and network blocked. A separate capability review ran 26 selected pure tests; these selections overlap, so they are not a combined 135-test result.
- **19 session defect checks reproduced the faulty behavior**: 13 controller/card checks and six source-extracted Python checks. I independently reran these. Passing a defect probe means the bug was reproduced, not fixed.
- Separate tool/codec/form/transaction probes reproduced rejected-patch replay, permission-check omissions, invalid repeater data, incorrect form values, and hidden-commit failure. No real private records, submissions, or installed plugins were used.
- A Chromium probe confirmed the 900px versus 8000px `100vh` geometry. Standard sRGB contrast calculations confirmed the prescribed caption colors fail normal-text contrast.
- Static token counts used locally available `cl100k_base` and `o200k_base` vocabularies with documented serialization assumptions.

The [probe directory](probes/) retains environment-specific reproduction scripts; appendix reports describe their original commands, mocks, and limits. These are audit artifacts, not production tests or fixes. The full Frappe integration suite, live Bob browser lifecycle, real-model output quality, billed cost, and published-site performance were not validated. No application-code patch was made.

External sources fetched on 2026-11-01:

- [MotionSites public gallery](https://motionsites.ai/) and [MotionSites MCP](https://motionsites.ai/mcp).
- [Magnific API introduction](https://docs.magnific.com/introduction), [stock resources](https://docs.magnific.com/api-reference/resources/images-and-templates-api), [video resources](https://docs.magnific.com/api-reference/videos/videos-api), and [API pricing model](https://docs.magnific.com/pricing). `docs.freepik.com` redirected to these docs during the review.
- [Adobe Stock API access and capabilities](https://developer.adobe.com/stock/docs/getting-started/).
- [Shutterstock API reference](https://api-reference.shutterstock.com/).
- [Unsplash API guidelines](https://help.unsplash.com/en/articles/2511245-unsplash-api-guidelines) and [API documentation](https://unsplash.com/documentation).
- [Openverse API documentation](https://docs.openverse.org/api/reference/).
- [fal documentation](https://fal.ai/docs/documentation).
- [Cloudinary image transformations](https://cloudinary.com/documentation/image_transformations).
- [OpenAI Docs: prompt caching](https://developers.openai.com/api/docs/guides/prompt-caching), consulted using the OpenAI Docs skill.

Provider access, exact prices, licenses, and terms depend on the account and can change. No purchase or provider setup was performed. Pexels' public docs returned HTTP 403. The built-in collaborative browser was unavailable because of host AppArmor policy; the public gallery and deterministic viewport probe were inspected using an available local Playwright/Chromium installation.

## Checkout preservation

`develop` was fast-forwarded to upstream `a112a3e6`; its pinned `frappe-ui` submodule was updated to `6e06ba92`. The prior local `frontend/components.d.ts` edit was preserved in the named main-repository stash `pre-bob-review local component declarations 2026-11-01` (the same declaration is already removed upstream). Existing executable-bit changes in three `frappe-ui` files were stashed, then reapplied on the correct submodule commit; a backup stash remains there. Existing `.scratch/` and `CONTEXT.md` were left intact. This review adds documentation only; it does not implement the proposed Bob redesign.
