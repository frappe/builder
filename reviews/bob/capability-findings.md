# Bob capability and semantic review

Reviewed `/home/t3run/builder`, branch `develop`, commit `a112a3e6aea1f9e712c75cdb9aeb713009467a90` (2026-11-01). Read-only review by the requested review agent. No app code or branch changes, model calls, site/database mutations, installs, or delegated agents. Pre-existing changes in `frappe-ui`, `.scratch/`, and `CONTEXT.md` were left alone.

The target is an autonomous website designer capable of ambitious visual assets and motion, including the kind of work the user associates with motionsites.ai. This review assesses Bob's implementation against that requirement; it does not claim to have benchmarked or inspected that external service.

## Assessment

Bob has a substantial page-authoring surface: 37 registered tools, authoritative server block edits, reusable components, page JS/CSS, data scripts, public form provisioning, stock image search, reference reads, screenshot review, and editor plugin authoring. It can create rich designs with native CSS/JavaScript; absence of a named animation tool does not mean animation is impossible.

It is not yet a reliably self-verifying, fully reversible website designer. The most consequential findings are:

- Server-rejected bulk patches are still applied in the editor. A successful tool result is not a reliable statement of the resulting state.
- Permission and effects boundaries vary between tools: document reads omit document/field checks; page data scripts can reach effectful helpers; ordinary page edits can mutate shared resources.
- Client-script lifecycle hooks commit inside purportedly savepoint-protected tools and overwrite live files. The advertised transaction boundary is false.
- Generated repeater data can be invalid Python; read/write representations also lose repeaters, icon metadata, linkage, and binding types.
- Form wiring corrupts several normal input types and can overwrite another page's form handler.
- Screenshot review uses an 8,000-pixel viewport, can mislabel application render failures as missing infrastructure, and cannot verify interaction, motion, accessibility, or runtime correctness.
- Asset capability is largely stock-image URLs and existing uploads. There is no native image creation/editing pipeline or durable asset curation workflow. Plugins offer powerful editor customization, but are trusted code with site-wide rollout before validation, not a safe general-purpose capability fallback.

P1 below means address before relying on autonomous edits of real sites; P2 means a significant correctness or capability gap. “Reproduced” means an isolated, local test of real implementation code with infrastructure dependencies mocked, not an end-to-end site exploit. “Source-confirmed” distinguishes code evidence from runtime testing. Recommendations are proposals, not implemented behavior.

## Findings

### F01 — P1: rejected bulk patches are replayed on the canvas

**Fact / reproduced.** `WorkingTree.apply_update_blocks` skips rejected patches but returns a string beginning `Applied to ...` even when zero patches applied (`builder/ai/agent/tree.py:448`, `:462`, `:475`). `AgentRunner.apply_client_ops` forwards the original, unfiltered operation unless the entire result starts with `FAILED` (`builder/ai/agent/loop.py:1035`, `:1042`, `:1049`). The browser applies every patch without these server guards (`frontend/src/components/ai/toolDispatch.ts:294`). The failure log also misses a pure `REJECTED` result because it only searches for `FAILED` or `NOT FOUND` (`loop.py:1039`).

Reproduction: on a real `title` block, call:

```json
{"tool_name":"update_blocks","args":{"patches":[{"block_id":"title","inner_text":"{{ missing.title }}"}]}}
```

The server reports `Applied to 0 of 1 blocks. REJECTED ...`, retains the old text, records no tool failure, and emits the patch. The actual TypeScript dispatcher changes the canvas text to `{{ missing.title }}`. This is exactly the render-breaking content the server rejected. A subsequent canvas save can persist the divergence; this last persistence step was not exercised against a site. Autosave is suppressed during AI work (`frontend/src/stores/pageStore.ts:363`), which reduces immediate races but does not make the replay correct.

A related single-edit mismatch: `update_block(element="script")` silently preserves the server's original tag and returns success (`tree.py:303`), but the browser sets `block.element = args.element` unconditionally (`toolDispatch.ts:249`). Both sides were reproduced: server `h1`, canvas `script`.

**Proposal.** Return structured per-patch acceptance and canonical applied mutations; replay only those mutations. Reject unsupported element changes explicitly. Test the actual server-to-dispatcher boundary, not two independent implementations with similar names.

### F02 — P1: general document reads do not enforce document or field-level permissions

**Fact / reproduced with a denied fixture record.** `get_document` checks `frappe.has_permission(dt, "read")`, then calls `get_doc` and `as_dict` without `doc.check_permission("read")` or `apply_fieldlevel_read_permissions()` (`builder/ai/agent/tools/data.py:86`, `:100`, `:104`). A role able to read some documents of a DocType is not necessarily entitled to read every named document or every field. The `fields` parameter filters an already unguarded dict; it is not permission filtering.

The isolated probe supplies a record whose document check would deny access and whose field filter is observable. The tool returns a harmless restricted fixture field while both checks remain uncalled. A real test should use an owner-only role, User Permissions, and a field with elevated permlevel. No real restricted data was queried.

Other reads follow a similar coarse boundary: `read_page` resolves and loads another page by database lookup (`builder/ai/agent/tools/query.py:195`, `:210`); `preview_page` loads a named page without a document check (`builder/ai/agent/tools/preview.py:127`, `:137`).

**Proposal.** Reuse the existing stronger `run_python.guarded_get_doc` pattern, which checks the document and applies field-level read permissions (`builder/ai/agent/tools/python.py:113`). Apply it consistently to references, previews, shared scripts, and settings reads. Protecting a direct File read does not protect a private image embedded in an otherwise unauthorized page preview.

### F03 — P1: write permissions are inconsistent with the target and the resource actually changed

**Source-confirmed; production role matrix not run.** The AI entry point has a DocType-level Builder Page write decorator (`builder/ai/api.py:50`; decorator implementation `builder/utils.py:99`). It does not authorize the supplied page document. `load_page` takes an AI lock and reads the tree, without a page permission check (`builder/ai/agent/loop.py:871`). Writes go through `db.set_value` (`builder/ai/page_writer.py:521`) or `ignore_permissions=True` for scripts, extracted components, and tokens (`builder/ai/agent/tools/scripts.py:72`, `:75`, `:131`; `components.py:82`; `settings.py:133`, `:140`). This matters on sites with restricted pages or custom roles even if broad stock roles mask it.

The clearest internal inconsistency is components: `edit_component` checks component write access (`components.py:100`), while an instance's `client_script` update mirrors into the shared definition via a raw database write with no component permission check (`builder/ai/agent/tree.py:212`, `:242`, `:256`). First-time prop declarations can take the same route (`tree.py:138`).

**Proposal.** Authorize the concrete page and every shared resource at the mutation boundary, before any mutation. Do not infer shared component/token/script authorization from the existence of an editable page. Include impacted documents and publication state in a tool's effects result.

### F04 — P1: a “read-only” data script can perform effects when server scripts are enabled

**Fact / gate acceptance reproduced; effects were not executed.** `write_page_data_script` uses a substring blacklist, AST syntax parsing, an import regex, and a portability-name check (`builder/ai/agent/tools/data.py:176`, `:245`). On server-script-enabled sites the name check returns immediately (`data.py:215`). These accepted examples demonstrate that this is not an effects boundary:

```python
# No forbidden substring .save( occurs.
doc = frappe.get_doc('Builder Page', 'fixture')
doc.page_title = 'Changed'
save = doc.save
save()
```

```python
frappe.sendmail(recipients=['fixture@example.invalid'], subject='fixture', message='fixture')
```

Both return “Saved the page data script” with the database mocked. Actual page execution uses full `safe_exec(script, None, ...)`, without Bob's read-only namespace or `restrict_commit_rollback` (`builder/utils.py:634`; page execution `builder/builder/doctype/builder_page/builder_page.py:697`). In the inspected installed Frappe dependency, the exec namespace exposes `get_doc`, `sendmail`, `enqueue`, writes, and commit helpers (`/home/t3run/frappe-bench/apps/frappe/frappe/utils/safe_exec.py:668`, `:694`). This dependency is outside the reviewed Builder commit; runtime consequences depend on the installed Frappe version and user permissions. Effects can happen during editor evaluation/preview as well as visitor rendering.

Even with server scripts disabled, data reads intentionally bypass visitor permissions through `safe_get_all` and raw document dict reads (`builder/utils.py:240`, `:292`, `:304`). The tool prompt warns against publishing private records (`data.py:440`), but code does not enforce a publication allowlist. This is an explicit trusted-author design, not a secure data publication boundary.

**Proposal.** Execute page data scripts in a deliberately read-only, bounded namespace in every configuration, with explicit public-data capabilities. Remove aliases to effectful APIs rather than scanning text. Validate scripts using a dry-run fixture/visitor context with prohibited network and writes. Preserve a separate, explicit path for intended integrations.

### F05 — P1: client-script saves break the tool savepoint and update live files before success

**Fact / isolated transaction simulation reproduced with the real methods.** `AgentRunner.run_handler` establishes a savepoint and rolls back exceptions (`builder/ai/agent/loop.py:1058`). The loop claims individual tools never commit (`loop.py:1267`). However, client scripts call a full document insert/save (`builder/ai/agent/tools/scripts.py:72`, `:131`), whose `before_insert` and `on_update` hooks write public code files (`builder/builder/doctype/builder_client_script/builder_client_script.py:34`, `:40`). `update_script_file` overwrites the existing file and calls `self.db_set(..., commit=True)` (`:85`, `:95`, `:104`).

Reproduction: run the actual hook under a fake transaction, then simulate page attachment failure. There is one internal commit, the JS file remains on disk, and the runner's rollback raises `RuntimeError: savepoint no longer exists` instead of returning its intended `FAILED` result. The probe writes its dummy JS only to a temporary directory.

Impact: earlier mutations in the same transaction may commit; a script can remain unattached; an edited shared script may already be live; database rollback cannot restore overwritten file bytes. The same problem affects form-script creation and snapshot restoration, which use this document lifecycle. Existing cache-busting query strings do not make the underlying overwritten file immutable.

**Proposal.** Stage immutable code assets, defer durable activation and cache invalidation until commit, remove hidden commits from hooks, and make rollback repair both records and assets. Track external effects independently from DB rollback. Test a forced failure at every lifecycle step.

### F06 — P1: generated static repeater data can crash or silently empty the page

**Fact / reproduced.** `build_repeater_data_script` interpolates `json.dumps(items)` directly into Python assignment syntax (`builder/ai/page_writer.py:423`). JSON booleans/null are not Python literals:

```python
# Generated from items: [{enabled: true, title: null}]
data.cards = [{"enabled":true,"title":null}]
# NameError: name 'true' is not defined
```

Two more reproduced failures:

- `repeat.data: data.cards` becomes `data.data.cards = ...` in the shim, while the block's binding key is normalized to `cards` (`page_writer.py:332`, `:415`, `:426`). Execution raises on the missing intermediate dict.
- Accepted `page:`/`root:` generation wrappers are unwrapped for block conversion (`page_writer.py:472`), but collection still starts from the original wrapper and only descends through `c`/repeat items (`:407`, `:504`). The blocks contain a repeater and the data script is empty.

The generation path directly persists this shim (`page_writer.py:537`); it does not run the checks in `write_page_data_script`. An inline repeater passed to `add_block` also ignores `items`; this limitation is documented (`builder/ai/agent/tools/blocks.py:189`) but is accepted rather than diagnosed.

**Proposal.** Use a safe JSON decoder expression or valid Python literals, normalize/validate data keys once, collect from the unwrapped root, and validate every generated data script. Return warnings/errors for unsupported inline data and duplicate keys. Test booleans, null, nested repeaters, wrappers, and reserved keys.

### F07 — P2: revert is not a complete undo, and some mutations have no revert entry

**Source-confirmed.** `SNAPSHOT_TOOLS` omits `write_page_data_script`, `attach_page_script`, `set_page_settings`, `set_design_token`, and direct `edit_component` (`builder/ai/agent/loop.py:80`). Some server operations queue `set_page_blocks` and thereby trigger a snapshot, but data-script-only and attachment-only turns do not. Captured state contains blocks, page data, script links and the content of already attached scripts (`builder/ai/snapshots.py:20`); it excludes route/SEO/head/body fields, shared definitions, tokens, plugins, newly created schema/records/files, and other pages affected by component sync.

Concrete scenarios:

- Change only page data or attach a shared script: no AI snapshot is requested.
- Change route or page head HTML along with blocks, then Revert: the blocks revert but these settings do not.
- Change a shared script on page A and revert A: restoring its captured content changes page B too, potentially overwriting B's later edit (`builder/builder/doctype/builder_page/builder_page.py:514`). There is no revision-conflict check here.
- Edit a component and sync published pages (`components.py:109`; `builder_component.py:138`): restoring one page's draft does not undo the shared definition and all other pages.
- Cancel/fail after a committed mutation: cancellation/error messages omit `revertSnapshot` (`loop.py:1147`, `:1154`); it is attached in the normal finish path (`:1365`). A snapshot may exist without the same chat affordance. Terminal UI/confirmation metadata also omits it (`conversation.py:67`; `pending.py:41`).

The Revert confirmation explicitly says the live page will not change until publish, but restoring shared script content rewrites its live public file immediately (`frontend/src/components/AIChatController.ts:952`; `builder_page.py:520`). Revert also deletes the conversation first and restores the page in a separate request (`AIChatController.ts:955`); a failed restore can leave the chat erased and the page unchanged, while a failed chat truncation is swallowed. This is not an atomic rewind.

Missing/empty page state can produce no snapshot; snapshot failures are logged and ignored (`snapshots.py:24`, `:50`). These are material limitations to the prompt's “can Revert” expectation (`builder/ai/prompts.py:125`).

**Proposal.** Define undo by an operation's full effect set, record versions/conflicts, and surface partial undo explicitly. Preserve undo metadata for cancelled, failed, and terminal turns. Distinguish deleting a newly created asset from detaching it, and distinguish reverting one page from reverting a shared resource.

### F08 — P2: “full” block reads are lossy, and readback is not a safe authoring round trip

**Fact / reproduced.** `read_block` calls compression and labels it “full styles/attributes/children” (`builder/ai/agent/tools/query.py:121`). The compressed representation is a projection:

- Lucide icons return early with only icon/name/base style, losing `ref`, attributes/ARIA, classes, tablet/mobile styles, bindings, component linkage and custom SVG changes (`builder/ai/block_codec.py:57`). Probe: all four tested keys `ref`, `attrs`, `m_style`, and `classes` were absent.
- A repeater compresses as `repeat: {data: ...}` plus ordinary `c` (`block_codec.py:120`). The authoring converter only creates a repeater when `repeat.item` exists (`page_writer.py:328`). `convert_yaml_block(compress(repeater))` becomes a static container.
- Compression reduces dynamic bindings to property→key (`block_codec.py:123`), dropping binding type and fallback precedence; the converter rebuilds every non-text binding as an attribute (`page_writer.py:240`). A dynamic style such as `color` changes meaning on a copy/rebuild.
- `componentVersion`, visibility conditions and other block metadata are not represented. `of` is emitted for referenceBlockId (`block_codec.py:99`) but not reconstructed by the generation converter. `props` and `client_script` are visible on reads but omitted by `convert_yaml_block` (`page_writer.py:280` through `:344`).
- `BlockCodec.expand` consumes `id`, while compression emits `ref` (`block_codec.py:75`, `:182`). The existing round-trip test checks selected fields, not identity (`builder/ai/test_block_codec.py:104`). This is a codec defect, not evidence that the current authoritative editor replay automatically calls that expander.

Normal surgical edits preserve omitted fields; do not infer that every edit destroys the tree. The concrete risks are incomplete reasoning, extracting/copying/rebuilding a read subtree, and any future use of the codec as a round-trip format.

**Proposal.** Separate a clearly documented summary format from a complete, versioned authoring/serialization format; provide raw/effective reads, typed bindings and prop schemas. Test semantic equality after round trips, including pins, refs, styles, conditions and runtime behavior.

### F09 — P2: deletion and normalization paths report success without removing the requested state

**Fact / reproduced.** Style merging always discards null values (`builder/ai/page_writer.py:122`), so `mobile_styles: {display: null}` returns “Applied” while an existing `display: none` remains (`tree.py:91`). There is no explicit style-key removal tool. Empty-string overrides may suppress output in some paths but do not express “remove this override and inherit.”

Generated blocks put every attribute, including `id` and ARIA, into `attributes` (`page_writer.py:298`); later edits classify nonstandard attributes under `customAttributes` (`tree.py:103`). Clearing a generated `id`/`aria-label` with null removes only the custom copy, leaving the original in `attributes`. The probe verified both survived a successful update. A sequence of set then clear can reveal an older generated value.

Removing the page root similarly returns `Removed block root.` while the tree remains: `apply_remove` does not reject the root and `detach` needs a parent (`tree.py:348`, `:479`). `ComponentTree` explicitly guards its root, demonstrating the missing page counterpart (`:546`).

**Proposal.** Add explicit unset semantics; canonicalize attribute storage at creation; remove aliases from both stores; reject root removal and unsupported operations. Return changed/no-op/rejected distinctly.

### F10 — P2: component operations do not share one propagation and lifecycle contract

**Source-confirmed.** Explicit `edit_component` saves through the component lifecycle, versions/syncs it, and refreshes affected pages (`builder/ai/agent/tools/components.py:109`; `builder/builder/doctype/builder_component/builder_component.py:92`). Instance script/first-prop mirroring uses `db.set_value` directly (`builder/ai/agent/tree.py:242`), bypassing that path. Current instance overrides, existing pinned embeds, new embeds, component caches and version snapshots can therefore observe different states. This path should not promise the same “every embed” behavior as an explicit versioned sync.

Extraction is called “pixel-exact,” but it strips `position`, `top`, and `left` at every breakpoint (`components.py:65`). Extract a sticky/fixed header or an absolutely placed visual section: its layout contract changes. The new skeleton does not preserve those removed root values as page-instance overrides (`components.py:47`). Behavior in page scripts, page data dependencies, and root CSS ancestry are also not captured by subtree extraction; the prompt relies on later manual/model migration (`builder/ai/prompts.py:103`).

Capability gaps: component server data scripts, detailed prop options/types/dynamic schemas, pin/unpin/detach operations, and atomic multi-component changes do not have dedicated authoring tools. `props` values can establish inferred defaults, but this is not full prop-schema editing (`tree.py:149`, `:540`).

**Proposal.** Make component effect scope explicit; use one permissioned, versioned mutation path. Preserve layout placement as instance overrides during extraction. Validate dependencies and repeated-instance isolation after extraction and embedding elsewhere.

### F11 — P1/P2: generated form submission does not preserve normal form semantics

**Fact / JavaScript reproduction.** The generated handler reads `.value` for every input and ignores `checked`, disabled state, multi-select values, and file contents (`builder/ai/agent/pending.py:286`, `:310`). It adds a click handler to the first button and calls `preventDefault` before browser form validation, without `checkValidity`/`reportValidity` (`:304`, `:306`, `:335`). A required/invalid field can be submitted via click; the Enter/submit path can behave differently.

Reserved field names are normalized and retain `input_name` (`builder/ai/agent/tools/forms.py:128`), but that mapping is discarded when building the client script; only ordered final fieldnames are passed (`pending.py:228`). Reordering the visual form breaks positional fallback.

The fixture had a `name` field first, an invalid email, unchecked consent, and a two-option radio group where only `pro` was checked. The real generated handler sent:

```json
{"email":"invalid-email","consent":"on","plan":"basic"}
```

It omitted the name, included unchecked consent, chose the unchecked last radio, and performed zero validity checks. Wrong consent or submitted choices is data corruption, not merely an accessibility concern.

Other limitations: unsupported field types are silently coerced to Data (`forms.py:129`); required/type constraints are not propagated into the created DocType/Web Form (`pending.py:185`, `:217`); a missing selector can attach to a heuristic fallback container or do nothing (`:287`); failure is communicated only by button text, not a field/error summary or live region (`:323`). No live submission test is part of connection success.

**Proposal.** Use explicit name mappings and successful-control/FormData semantics, preserve boolean/radio/multi-value types, validate on submit, and provide accessible pending/success/error states. Test both pointer and keyboard submission as guest and signed-in user. Verify CSRF behavior too: this fetch sends no CSRF header (`pending.py:318`), and the inspected Frappe checks one for sessions with a token unless an exemption applies (`/home/t3run/frappe-bench/apps/frappe/frappe/auth.py:83`); this compatibility risk was not exercised on a site.

### F12 — P2: form reuse can break another page or misreport a connection

**Source-confirmed.** The “idempotent per (page, web_form)” function names scripts only `Save <doctype> submissions` (`builder/ai/agent/pending.py:236`). Connecting the same submission type on page B with a different selector updates the same script used on page A (`:240`, `:247`), then attaches it to B. A concrete reproduction is `#contact-a` on A followed by `#contact-b` on B; inspect A's previously attached script to see its selector replaced. No site records were created here.

The existing-form check is page-wide rather than selector-specific (`builder/ai/agent/tools/forms.py:90`). Existing Web Forms are reused by name without checking their DocType, publication/login state or field schema (`pending.py:203`). An existing custom Builder DocType is treated as a submission type based only on `custom` and `module` (`forms.py:142`). A subsequent form can therefore report success while fields are absent/ignored or it is wired to a mismatched endpoint. `apply_connect_form` even returns “Form connected” when the supplied page no longer exists, because attachment is conditional (`pending.py:227`, `:231`).

**Proposal.** Key the connection by page and form identity, validate reused schema/endpoint identity, preserve explicit mappings, and report independent provisioning/attachment/submission status. Schema creation may entail framework DDL commits; failure compensation needs testing separately from ordinary row rollback.

### F13 — P1 for verification quality: previews change viewport semantics and conceal render failures

**Fact / error masking reproduced.** Desktop/tablet/mobile choose only widths. All use height 8000 (`builder/ai/agent/tools/preview.py:21`, `:39`). This changes `100vh`/`dvh` layouts, height media queries, sticky/scroll geometry and IntersectionObserver visibility. A 100vh hero is 8000px tall in the check, not a normal desktop/mobile viewport. This is especially unsuitable for scroll-driven/motion sites.

At most three 2000px tiles are attached, cropped by a pixel-difference background heuristic (`preview.py:54`, `:67`). No actual DOM scroll-height proves coverage; background/low-contrast content can fool trimming. There is no scroll-to-region tool for reviewing the unseen tail. Two total previews per turn cannot cover desktop/tablet/mobile, both themes, and post-fix confirmation. Reference previews consume that same budget (`:124`). The older-service fallback ignores width/height entirely (`builder/html_preview_image.py:17`, `:25`), while results still label the requested variant.

Every exception in HTML generation or screenshot capture becomes “screenshot renderer not reachable ... do not retry” (`preview.py:141`). The probe injected a template/render error and got exactly that infrastructure explanation. The agent loses the actionable runtime cause and is told to finish without verification.

**Proposal.** Use realistic viewport dimensions and full-document/scroll captures independent of viewport height. Return DOM coverage, resource/console/template errors and exact effective viewport. Distinguish renderer availability, page failure, image failure and budget limits. Spend validation budget according to changed risks; never describe a skipped check as a pass.

### F14 — P2: script and motion correctness are authored, but not verified

**Source-confirmed.** Page script validation checks a few literal CSS-injection markers, not JavaScript syntax, CSS validity, imports or runtime execution (`builder/ai/agent/tree.py:270`). Component client scripts do not even pass that validator (`tree.py:212`). Minification is not a JavaScript parser/type/runtime check. `script_hook_gap_note` is a regex check on selected classes that runs when generation returns (`builder/ai/agent/loop.py:1449`, `:1454`); the recommended workflow writes scripts *after* generation (`builder/ai/prompts.py:134`), and there is no equivalent guaranteed check afterward. It misses ID/attribute/computed selectors and behavioral failures even if a class exists.

The preview tool explicitly says motion and hover are invisible in a static screenshot (`preview.py:201`). There are no registered tools to click, hover, scroll, type, inspect focus/computed layout, read console/network errors, test route requests, emulate reduced motion, measure frames/performance, or capture time samples. Generation verification is a prompt instruction (`prompts.py:135`), not a finish invariant (`loop.py:1221`, `:1343`).

Do not infer that screenshot rendering is effect-free: the inspected Frappe renderer creates Chromium content with scripts enabled and waits for load/network lifecycle (`/home/t3run/frappe-bench/apps/frappe/frappe/utils/preview.py:71`; `/home/t3run/frappe-bench/apps/frappe/frappe/utils/chromium/page.py:274`). It can run initialization code, but Bob gets only a still image. Runtime behavior and side-effect control are separate requirements.

**Proposal.** Add a bounded browser validation surface with structured assertions and isolated guest/auth fixtures. Compile/parse code, inspect its selectors against rendered DOM, exercise interactions, and verify motion at defined time/scroll points with reduced-motion alternatives. Require evidence for claims that interaction works.

### F15 — P2: plugin installation is site-wide trusted code, activated before its test result

**Fact / architecture, not a claim that unprivileged users can install plugins.** The plugin-manager gate is present (`builder/plugins/bob.py:45`; `builder/plugins/access.py:48`). After that, `write_plugin` installs for all editors, writes the files, commits, and only then asks this user's editor to import/test it (`bob.py:66`; `builder/ai/agent/tools/plugins.py:47`, `:64`). A failed load returns `FAILED: installed...`; it does not restore or disable the installed release (`plugins.py:114`). Other users can load the broken release next time. Headless writes are installed without this check (`:57`). A no-node/timeout syntax check silently skips parse validation (`bob.py:119`).

These plugins are ordinary same-origin Vue/JavaScript modules (`frontend/src/plugins/loader.ts:30`). They run with each editor user's access, including broad internal imports (`plugins.py:174`; `builder/plugins/access.py:6`). The manifest intentionally rejects `permissions` for sandboxed plugins (`builder/plugins/package.py:181`). ZIP path/size/SVG validation is valuable but is not JavaScript isolation or an effects declaration.

The hidden check mounts components using the real app context for 400ms (`frontend/src/plugins/tryPlugin.ts:146`). `setup`/`onMounted` can therefore mutate stores, write server state or issue network calls while being “tested.” It does not click actions, wait for slow failures, or prove useful behavior. The result's “components rendered without errors” should not be elevated to functional verification.

**Proposal.** Stage and test a candidate per user, then explicitly activate its site-wide release under the already established manager authorization. Make code trust and scope visible. If a restricted extension system is desired, implement it as a separate capability/runtime boundary; prompt import restrictions are not one.

### F16 — P2: plugin replacement/unload is not atomic and cannot clean up arbitrary effects

**Fact / reproduced with real loader and registry code.** `replacePlugin` imports first, then unregisters the previous items, then installs (`frontend/src/plugins/loader.ts:84`). If the new install registers one item and throws, the old UI is gone, the new partial item remains, and `runningEntries` still points to the old release. The isolated probe returned `partial` as the only item with the old running entry.

`trackPluginItems` tracks synchronous registration only and has no failed-install undo (`frontend/src/utils/createRegistry.ts:26`). An async install can register after the tracking scope ends; a probe showed such an item survived `unloadPlugin`. Unload only unregisters tracked items and updates sets (`loader.ts:90`); it does not undo listeners, intervals, styles, store mutations, requests or server writes. `openHandlers` is a separate growing map with no corresponding removal here (`frontend/src/plugins/context.ts:53`). A plugin can also overwrite an existing registry name, and unregistering does not restore the replaced item (`createRegistry.ts:101`).

**Proposal.** Use transactional registry ownership and failed-install restoration; explicitly support/reject async installation; require and run disposal hooks; namespace registry identities; clear open handlers. Treat irreversible on-install/on-mount effects separately from UI registration rollback.

## Capability coverage and remaining gaps

These are product/verification gaps, not all implementation bugs.

1. **Open-page authoring is broad; website lifecycle is narrow.** The default registry has 37 tools assembled in `builder/ai/agent/registry.py:85`. It has no model-callable create/switch/duplicate/delete-page or publish/unpublish tool. `generate_page` needs an existing open page (`loop.py:1435`); reference pages cannot be edited by `read_page` (`query.py:219`). The prompt acknowledges that output is a Builder page and packages cannot be installed (`builder/ai/prompts.py:70`). A multi-page site can be built through user navigation and shared resources, but this registry alone is not autonomous site-wide planning/execution. The Python tool is intentionally read-only, and writing an editor plugin should not be the normal escape hatch for missing page lifecycle operations.

2. **Assets lack a creation and curation pipeline.** The registered image capability is stock search (`builder/ai/agent/tools/images.py:142`) plus viewing image blocks and attaching user images. There is no bitmap generation/editing, subject consistency, background removal, upscaling, inpainting, asset import/promotion, responsive rendition generation, focal-point/crop workflow, video generation/transcoding, 3D asset creation or animation-asset inspection tool. Ordinary SVG/HTML/CSS authoring remains possible. There is no basis for claiming the quality of one kind of asset covers all these media.

3. **Stock results are lossy asset records.** Openverse's commercial filter does not make attribution/provenance unnecessary; the adapter discards license, license URL and source-page metadata (`images.py:65`). Results contain a URL, thumb, short description, credit and dimensions (`:132`). No tool downloads/pins a durable local asset or checks final page resource availability. Direct remote URLs can later change or fail. Image selection sees up to six results/provider, with first nonempty provider winning (`:15`, `:101`); stock search is not art direction validation.

4. **Private reference and public deliverable are separate.** User attachments are deliberately saved as private Files (`builder/ai/api.py:26`), and the generator can see authorized private images (`builder/ai/agent/artifact.py:87`). There is no dedicated operation to turn an approved reference into an authorized public site asset; using its private URL as an `img` source may work for the editor but fail for a visitor. This needs an explicit public-use workflow, not automatic exposure of every reference attachment.

5. **External visual references cannot be inspected as experiences.** `read_url` extracts text and strips script/style/SVG/template content (`builder/ai/agent/tools/web.py:73`). It does not render the URL, inspect layout, follow a scroll narrative or extract animation timing/assets. A user-provided screenshot can guide a static composition; it does not specify hover, mobile behavior or motion. `research` can supply information but is not an interactive browser.

6. **Motion is possible through CSS/JS, but execution and design support are thin.** No timeline/state abstraction, animation asset library, runtime visual inspection, easing/scroll progress sampling, reduced-motion emulator or performance budget exists in the tool registry. Prompt policy defaults to no unsolicited animation while allowing requested/reference motion (`builder/ai/prompts.py:132`); the user's expressed motion goal should count as opt-in. The gap is verified, intentional motion design rather than simply “add an animation tool.”

7. **A11y is not a release check.** Screenshots ask the model about contrast and overlap (`preview.py:181`), but there is no accessibility-tree audit, accessible-name verification, heading/landmark check, focus/keyboard path, touch-target/reflow test, live-region/error check or automated WCAG audit. The plugin hidden-render contrast threshold is 3:1 even for ordinary text (`tryPlugin.ts:57`, `:238`), only in a hidden dark container, and is not a whole-page accessibility check. Its color checker does not model all backgrounds/states. HTML attributes can author accessible behavior, but authoring it is not verifying it.

8. **Semantic HTML must be checked after rendering.** `inner_text` writes raw `innerHTML` (`builder/ai/agent/tree.py:299`), and the renderer parses it as HTML (`builder_page.py:1182`), so it is not a plain-text escaping contract. Published `p` blocks are converted to `div` (`builder_page.py:1072`). Bound style values exist in the underlying renderer (`:1478`) but cannot be expressed faithfully through the current `bind` schema. Do not use the model's block vocabulary as proof of final DOM semantics.

9. **Python has a useful stronger read boundary, but not a resource sandbox.** It trims dangerous helpers, scopes reads, wraps documents, blocks commit/rollback, and rolls back its savepoint (`builder/ai/agent/tools/python.py:37`, `:78`, `:113`, `:130`). Existing tests cover imports, writes, common effect helpers and row permissions (`builder/ai/test_run_python.py`). However, output is capped only after execution/serialization (`python.py:150`); loops, allocation and unbounded `count` implemented as loading all matching names (`:105`) have no per-snippet CPU/memory budget. Cancellation waits on the executing tool; the outer worker timeout is 600 seconds (`builder/ai/api.py:119`). The full feature is unavailable with server scripts disabled. Nested upstream namespace helpers and field-level Single-value reads deserve a version-specific audit; this review does not claim an additional proven escape.

10. **Tool status/effects are not typed.** `Tool` declares side/artifact/handler, not effect scope, permission requirements, verification evidence or compensating actions (`builder/ai/agent/registry.py:34`). Unknown tool names default to client and `WorkingTree.apply` defaults to `Applied.` (`registry.py:74`; `tree.py:375`). “FAILED” prefix/string matching governs mutation accounting (`loop.py:1108`); `DECLINED`, no-op and warning results are not a shared status model. `search_images` is absent from the read-only accounting set (`loop.py:123`) despite not changing site state. These are avoidable false-success and auditability paths.

11. **Concurrency protection is scoped.** Redis page/session locks protect cooperating AI turns and token-fence release (`builder/ai/locks.py:21`, `:49`). They do not provide compare-and-swap on page writes or cover other editor requests, shared component/token/script edits across pages, and every dependent page during sync. Page persistence deliberately uses unconditional `set_value` (`page_writer.py:540`). Normal canvas autosave suppression during an AI build is useful, but it is not a multi-document concurrency protocol. Race/conflict tests should include another tab and manual edits, not only two AI sessions.

12. **Recovery can silently reduce a generation.** YAML salvage drops offending lines or truncates the tail (`page_writer.py:432`), forbidden descendant elements disappear (`:277`, `:319`), and the generation tool still reports “Page generated and saved” when a root survives (`loop.py:1445`). Useful recovery should return a repair/dropped-content report. Also, generation replaces an existing data script if it emits a shim and otherwise leaves the old script intact (`page_writer.py:537`); neither case is a merge of the previous page's data dependencies. Cancelled generation intentionally keeps its valid partial prefix (`artifact.py:286`), which needs an incomplete-build status and reachable undo.

## Effects boundary inventory

- **Block edits:** usually one draft tree; exceptions include component script/first-prop mirroring. Canvas replay must use canonical server results. No model-argument schema validation is enforced by the registry itself.
- **Generation:** draft replacement, optional page data replacement, stream events/buffers, diagnostic files; salvage/cancel can persist partial content.
- **Page settings/data:** immediate record writes; route save has lifecycle behavior; page data executes later under potentially different users. Head/body HTML can carry executable behavior. These are not all draft-only or covered by AI undo.
- **Scripts:** shared records, public files, cache changes, possible exported development files and implicit commits; changes may affect already published pages without publishing their blocks again.
- **Components:** shared definition/version history, every referencing draft/live page on sync, caches, optional source export. Instance-level mirroring has a different effect path.
- **Tokens:** shared site theme; color/font update immediately affects all references. No page-local scope or AI revert of the token value.
- **Forms/schema/sample data:** confirmation required, then schema/Web Form/script/page-link/record effects. Existing document reuse, DDL and file hooks prevent treating the whole chain as a simple row transaction. Confirmation itself checks a generic Builder Settings write permission (`builder/ai/api.py:150`), which may differ from the permission the proposal checked. The check-and-apply message status sequence is not locked (`:159`, `:170`), so duplicate confirmation requests also need an idempotency test.
- **Images/web:** network fetches, provider costs for research, private attachment files, model data disclosure when images/content are attached. `read_url`'s pinned public-fetch path and private File checks are positive defenses; Chromium page subresources need their own boundary review. The inspected Chromium dependency defaults external request blocking off (`/home/t3run/frappe-bench/apps/frappe/frappe/utils/chromium/page.py:37`, `:204`); do not assume the web-read SSRF guard governs screenshot subrequests. No network exploit was attempted.
- **Preview:** evaluates server data scripts, runs page initialization in a renderer, queues thumbnail refresh, and attaches images to the model. It is read-like from a UI perspective, not necessarily side-effect-free.
- **run_python:** intended read-only DB access with rollback; resource limits and inherited namespaces still matter. Rollback cannot undo a network, log, filesystem or queued effect if an exposed helper performs one.
- **Plugins:** trusted JS installed site-wide, release files/records, early commit, real-app import/install/mount effects, later execution as other editor users. Registry unregister is not uninstalling executed JavaScript.
- **Memory:** durable site memory is another scope outside page revert (`builder/ai/agent/tools/memory.py:46`, `:60`).

## Verification performed and limitations

Executed without initializing a live site or calling providers:

- **26 existing pure tests passed:** selected `builder.ai.test_tree_apply` and `builder.ai.test_page_writer` tests. Excluded `test_add_converts_yaml_vocab` and `test_component_reference_and_attrs` because their current component resolution reaches the database despite the suite's pure-test description.
- **Python probes:** actual WorkingTree, codec/converter, data-script gate, general record reader and generated form-script functions; extracted actual runner method for replay acceptance; mocks for database, logs and permissions. Confirmed F01, F02's missing checks, F04's acceptance, F06, F08 and F09.
- **TypeScript/JS probes:** transpiled the actual dispatcher/loader/registry into memory, using fake canvas/DOM/fetch and real Vue reactivity. Confirmed server/canvas divergence, form payload/validation failures, plugin partial replacement and untracked async registration.
- **Boundary probes:** actual script-file hook plus runner handler with a simulated transaction and temporary filesystem, and mocked preview rendering. Confirmed hidden commit/rollback failure and misclassification of template errors.

Re-run commands:

```bash
PYTHONDONTWRITEBYTECODE=1 /home/t3run/frappe-bench/env/bin/python /tmp/bob-review-probes.py
node /tmp/bob-review-probes.cjs
PYTHONDONTWRITEBYTECODE=1 /home/t3run/frappe-bench/env/bin/python /tmp/bob-review-boundaries.py
```

Artifacts: `/tmp/bob-review-probes.py`, `/tmp/bob-review-probes.cjs`, `/tmp/bob-review-boundaries.py`; outputs `/tmp/bob-review-probes.json`, `/tmp/bob-review-probes-js.json`, `/tmp/bob-review-boundaries.json`. Fixtures `/tmp/bob-review-rejected-op.json` and `/tmp/bob-review-form.js` are generated by the Python probe. These are review artifacts, not proposed production tests or app changes.

Not performed: live DB permission exploitation, full Frappe integration suite, browser interaction against a running site, published-page performance/a11y measurement, paid-model quality evaluation, real image-search/network requests, real form submissions, plugin installation, or a motionsites.ai comparison. Findings about these environments are source-confirmed or explicitly proposed tests. Installed Frappe references are supplemental and version-dependent; primary citations are within the reviewed Builder tree.

## Proposed exhaustive representative scenario taxonomy

This is an exhaustive inventory of representative *scenario families*, not a claim that finite examples exhaust all HTML/JS/Python behavior. Cover each family below with deterministic fixtures. Combine risk-bearing axes pairwise by default, and use full combinations for permissions/publication/undo and stateful form/motion flows. Every scenario should state: initial serialized state, user request/tool sequence, permitted effects, expected persisted state, expected canvas state, expected visitor/runtime behavior, expected tool status, and undo/conflict outcome.

### S01 — Site and conversation state

Empty page; existing draft; published page with no draft; published page with divergent draft; user switches pages mid-turn; component canvas open; no open page; stale selected ref; multiple selected subtrees; prior chat reference image; text-only model; disconnected browser; reconnect during stream; reference-heavy turn; conflicting existing site styles. Check scope, state refresh and honest capability/verification reporting.

### S02 — Primitive block semantics

Every text/media/form/semantic container; zero/one/deep/many children; add at start/middle/end; valid/missing/wrong-parent `after_block_id`; remove leaf/subtree/root; move between parents; move into self/descendant; unknown ref; duplicate ref; forbidden tag; invalid argument type; unknown tool; empty patch; partially valid batch; all-rejected batch; overlapping patches to one block. Assert one canonical result and structural invariants on server, replay and reload.

### S03 — Styles and responsiveness

Add/change/unset base/tablet/mobile overrides; cascade back to inherited/component defaults; kebab/camel property names; CSS variables and missing fallbacks; zero/unitless/negative/calc/clamp values; font stacks; grid areas; gradient shorthands; hover/focus/active/disabled states; custom properties; logical properties for RTL; container queries; breakpoints just below/at/above thresholds. Assert computed behavior, not just serialized values.

### S04 — Generated blocks and recovery

Valid YAML; fences; one-item/multi-root lists; page/root/body wrappers; aliases/anchors; malformed interior line; truncated tail; empty/forbidden root; forbidden child; nonstring text; unsupported field; unknown icon; missing component; truncated model stream; explicit cancel; provider error before/after valid prefix. Check repair reports, required sections, data preservation, incomplete status, undo and final ID consistency.

### S05 — Serialization and read fidelity

Compress/expand and read/copy/add across every field: refs, names, originalElement, attributes/customAttributes, classes, breakpoints, SVG/icon metadata, bindings of each type/source, duplicate/fallback bindings, repeaters, dataKey, visibility, component links/pins, props/configs and scripts. Compare raw tree, effective component-resolved tree and rendered DOM. Verify changed fields and preservation of every untouched field separately.

### S06 — Components and shared design

Extract normal/sticky/fixed/absolute section; nested components; two embeds on one page; embed on a second page; pinned/unpinned versions; instance override versus shared edit; text/styles/attributes/script/props; add/reorder/delete children; recursive nesting; renamed/missing internal refs; declared/unknown/deleted props; false/zero/empty/list/object values; private component permissions; shared edit with one inaccessible referencing page. Verify page data/page-script dependencies, scoped selectors, isolated state, cache invalidation and version/undo semantics.

### S07 — Data and binding runtime

No rows, one row, many rows; live/static/nested repeaters; boolean/null/unicode/multiline/nested JSON; dotted/prefixed/reserved/duplicate keys; missing key versus explicit empty/zero/false; page/component/prop sources; attribute/text/style bindings; image/link bindings; formatted values; syntax-valid runtime failure; disabled/enabled server scripts; guest/auth/privileged data results; query size limits; dynamic route params; absent/malformed/unauthorized record ID; redirect/error route. Assert no accidental private publication and no effects during evaluation.

### S08 — Public forms and submissions

Text/email/number/date/datetime; required/optional fields; empty/whitespace/zero; checkbox checked/unchecked; radio group each selection; select/multi-select; hidden/disabled fields; file input; repeated names; reserved names and reordered fields; click versus Enter; first button is not submit; no form wrapper; missing/invalid/ambiguous selector; two forms per page; same form type on two pages; changed existing schema; existing Web Form with wrong binding/login state. Exercise success, validation error, rate limit, CSRF/session expiry, server error, timeout, double-click, retry and duplicated confirmation. Verify stored records and accessible state feedback.

### S09 — Page/client script lifecycle

Create/attach/reattach/update/detach/clear; CSS versus JS; type change; shared script on two live pages; duplicate name; dependency ordering; load before DOM; repeated initialization; thrown parse/runtime error; rejected promise; external script blocked/offline; nonexistent selectors; event delegation; script-generated classes; scoped component CSS browser support; file-write failure; cache bust; old cached URL; attachment failure after save; undo after another page edits the shared script. Check DB/file/browser consistency.

### S10 — Image and media assets

User-owned upload; private reference used as public image; library photo; unavailable provider; empty results; attribution-required image; identical/conflicting assets; broken/redirected URL; remote private address; oversized/dimension-heavy image; corrupt file; SVG; transparency; dark/light image pair; srcset/sizes; hero focal crop; CSS background; lazy loading; animated GIF/WebP; video/poster/captions; Lottie/3D/canvas asset; brand-consistent variant request. Validate provenance, allowed disclosure, durable URLs, decoding, responsive crop, quality, alt/decorative intent and transfer budget.

### S11 — External references and design intent

Text-only page versus JS-rendered page; screenshot versus live reference; reference below fold; visual-only design; moving reference with static screenshot; mobile/dark reference; multiple incompatible references; unavailable URL; user specifies exact asset/typeface/logo; user asks for a medium/tool Bob cannot create; design matches current site versus intentional new direction. Check whether available evidence supports the requested fidelity and whether limitations are stated accurately.

### S12 — Motion and interaction

Hover/focus transitions; reveal at viewport entry; stagger; pinned/scroll-scrub scene; horizontal scroll section; parallax; marquee; count-up; carousel; drag; video autoplay; cursor effect; SVG animation; canvas/WebGL; native View Transitions; route transitions; component repeated twice; resize/orientation change mid-animation; back/forward navigation; interrupted/restarted animation. Sample initial, intermediate, completed and reversed states. Assert reduced-motion behavior, no invisible content if JS fails, keyboard/touch parity, listener cleanup and frame/CPU budget.

### S13 — Accessibility and semantics

Accessible names for all controls; heading hierarchy/landmarks; link versus button; alt/decorative images; captions/transcripts; focus order/visible focus; keyboard menu/dialog/accordion/tab behavior; dialog focus trap/restore/Escape; skip navigation; live status and error associations; native validation; touch-target size; contrast on image/gradient/theme/state; reduced motion and pause controls; no flashing; 200% text and 400% zoom; reflow at narrow widths; screen-reader reading order; language/RTL; generated rich text and final DOM tag correctness. Use automated checks plus manual keyboard/screen-reader fixtures.

### S14 — Responsive visual quality

320/360/390/768/1024/1280/1440/1920 widths plus actual breakpoint edges; realistic short/tall viewports; portrait/landscape; light/dark; increased text size; long words; localization; extra/empty data; loaded/fallback fonts; loaded/missing assets; scrollbar presence; safe-area insets; sticky/fixed chrome; 100vh/dvh heroes; deeply long pages; horizontal overflow; subpixel boundaries. Check full-page and critical-region screenshots, computed geometry, content order and touch/keyboard usability.

### S15 — Runtime, navigation and delivery

Published route versus draft preview; guest versus authenticated user; direct deep link versus navigation; dynamic record route; route rename/conflict; 404; canonical/SEO/open-graph; resource status/MIME/CSP/CORS; console errors and unhandled rejections; font readiness; lazy media at scroll; network/CPU throttling; failed third-party dependencies; cache version mismatch; bfcache/back-forward; browser support including component @scope; main-thread/per-frame budget; layout shift; page weight and LCP/INP. Assert evidence on the actual delivery path, not only the editor canvas.

### S16 — Read permissions and information boundaries

Administrator; System Manager; Website Manager; ordinary page editor; read-only editor; owner-only/custom role; explicit share; User Permission restriction; field permlevels; Single versus ordinary versus child DocType; private/public File; restricted reference page; shared component/script inaccessible directly; doc name guessed correctly/incorrectly; session owned by someone else; permission revoked between request and execution. Apply the same fixtures to every read tool and each path that attaches data to the model.

### S17 — Writes and effects boundaries

Per-page versus shared script/component/token mutation; published versus draft state; settings and head/body code; data script with permitted read, alias write, network, email, enqueue, commit, logging and exception; plugin install/mount/action; preview side effects; schema creation; sample data insertion; File write and source export; disabled server-script mode; forged/unknown args; denied permission after proposal; stored pending action applied twice. Assert explicit scope, authorization, idempotency and an effects ledger.

### S18 — Failure, cancellation, concurrency and undo

Fail before first write, after row save, after file write, after internal commit, after queued event, after checkpoint and before final summary; cancel generation versus script/plugin wait; missing screenshot service; malformed model output; stale/missing lock; duplicate realtime event; dropped event; out-of-order event; second AI task on same/different page; manual edit in another tab; simultaneous shared-resource update; one dependent page refuses sync; crash/restart/reconnect; revert with newer shared edits; pruned/missing snapshot. Assert database, files, canvas, history and user-visible status agree.

### S19 — Editor plugins

All five registry surfaces; valid/no default export; invalid syntax; forbidden/unavailable import; install throw before/after registration; component render throw; delayed async error; action click failure; async registration; registry name collision; slow state fetch; unavailable browser; disabled plugin/user setting; repeated/replayed load token; replace success/failure; revert to previous release; unload/reload; listeners/timers/styles/open-handler cleanup; hot update in multiple editors; differing user privileges; light/dark themes; narrow panel; keyboard/focus. Verify functionality and allowed effects, not only “something registered.”

### S20 — Resource and orchestration limits

Very large block tree, deeply nested tree and repeater, huge code field, oversized model tool args, long source/reference read, many images, preview count exhausted, image cap exceeded, long page beyond capture, malformed image, slow network, unbounded Python query/loop/allocation, per-tool and whole-turn timeout, maximum rounds, terminal UI after partial edits, provider finishes without verification, tool returns warning/DECLINED/partial/no-op, unknown tool. Assert bounded work, truthful status and usable recovery without paid calls in deterministic CI.

## Representative end-to-end acceptance set

After repairing the deterministic failures, these twelve fixtures would test whether the product meets the user's designer goal. These are proposals; none was built in this review.

1. An editorial studio landing page with exact typography, a strong hero image, responsive art direction and usable mobile navigation.
2. A motion portfolio with a 100dvh hero, scroll narrative, hover/focus previews, reduced-motion alternative and no content hidden by failed JS.
3. A product launch page using branded transparent assets, desktop/mobile crops, dark/light variants and a licensed asset manifest.
4. A three-page site with shared sticky header/footer, active-page props, shared design tokens and one isolated instance variation.
5. A data-driven catalog and detail route with zero/one/many records, permission-scoped reads and missing-record behavior.
6. A form-heavy service page with email, required fields, consent, radio/select values, keyboard submission and visible error/retry states.
7. Two pages sharing a submission DocType but using different form selectors, plus two forms on one page.
8. A reusable interactive component extracted from an existing page, embedded twice there and once elsewhere, with isolated state and no page-only dependencies.
9. A long dark/light marketing page exceeding 8,000px with lazy media, footer checks, responsive typography and realistic viewport captures.
10. A revision request that removes styles/attributes, changes an image, preserves existing data/scripts/pins, and can be fully undone after reload.
11. An editor plugin that audits missing alt text, previews fixes, changes only authorized blocks, survives replacement and disposes all listeners.
12. A failure-injected multi-tool turn spanning page blocks, a shared script and a plugin, showing exactly what committed, what failed and what undo can restore.

For each, retain a deterministic tool transcript, before/after serialized state, structured effects/permissions results, rendered DOM/a11y/runtime evidence, visual captures for selected states, performance/resource results and an undo/conflict test. Evaluate design taste separately from tool correctness: human review of composition, typography, imagery relevance/consistency and intentional motion is still necessary. A beautiful screenshot must not conceal broken forms, inaccessible controls, failed assets or untracked live-site changes.

## Proposed implementation order

1. Fix canonical replay, document permissions, data-script execution scope, script transaction/file effects, and static repeater generation.
2. Fix form serialization/mapping/reuse; introduce complete unset operations and clearly scoped undo.
3. Unify component lifecycle/version semantics and plugin staged activation/disposal.
4. Add real browser/runtime/a11y/motion checks with realistic viewports and typed outcomes; enforce honest completion evidence.
5. Add a durable, permissioned asset pipeline and explicit multi-page lifecycle tools, then benchmark visual quality with the acceptance fixtures above.
