# Bob acceptance and design experiments

`scenarios.json` traces all 82 [review cases](../../../reviews/bob/bob-review-scenarios.md) to required outcomes, test patterns and browser/frontend evidence. A passing invariant is **not a full scenario pass**.

## Deterministic gate

Use a disposable migrated site with `allow_tests` enabled. Stop its Bob daemon while running tests: some fixtures commit queued rows, and process-local patches cannot protect another process. Prefer recreating the disposable site afterward.

```sh
BOB_PLAYWRIGHT_MODULE=/path/to/playwright \
BOB_CHROMIUM=/path/to/chrome \
node frontend/scripts/verify-bob-browser.mjs /tmp/bob-browser.json

bench --site SITE execute builder.ai.acceptance.run \
  --kwargs '{"output_path":"/tmp/bob-acceptance.json","browser_path":"/tmp/bob-browser.json"}'
```

The runner discovers `builder.ai.test_*.py` and guards live LiteLLM/image/stock transports. Browser fixtures cover progressive enhancement, keyboard/RTL/vertical tabs, disposal/reinstall, reduced motion, disclosure, a footer beyond 6000px, reflow, known diagnostic defects and declarative interaction assertions. The 640px viewport is equivalent 200% reflow, not browser-chrome zoom. Screen-reader reading order, complex contrast, font glyph coverage and live service delivery remain separate checks.

`bench --site SITE execute builder.ai.acceptance.pairwise_plan` produces a deterministic covering plan over page/session/viewport/asset/provider/editor dimensions. Each row starts `not_run`; producing the plan does not execute it. Exercise failure sequences from the review and retain run/event/effect IDs. Do not sum overlapping historical test counts.

## Live corpus and blind comparison

`corpus.json` supplies six repeatable prompts: vague discovery, a complete studio brief, dense professional content, Arabic RTL, expressive motion and direction exploration. They are fictional evaluation fixtures. Add owned assets/references for media experiments; never present fixtures as real customer proof.

The next command **starts one live model turn and may incur charges**. It is separate from regression tests. Compare baseline/candidate deployments using the same model, budgets and content, ideally at least three samples per case:

```sh
bench --site SITE execute builder.ai.evaluation.start \
  --kwargs '{"case_id":"complete-studio","model":"YOUR_MODEL_ID","implementation":"COMMIT_SHA","sample":1}'
```

Continue questions, direction selection and corrections in the returned editor chat. The harness never fabricates user answers, auto-accepts confirmations or publishes pages. Supply the same factual answers across samples. Capture completed candidates:

```sh
bench --site SITE execute builder.ai.evaluation.capture --kwargs '{"page_id":"PAGE_ID"}'
bench --site SITE execute builder.ai.evaluation.blind_pack \
  --kwargs '{"page_ids":["BASELINE_PAGE","CANDIDATE_PAGE"],"output_directory":"/tmp/bob-blind-review","seed":42}'
```

The pack labels actual desktop/mobile images A/B/etc. Candidates must share a corpus case and current captured revisions. Give reviewers `index.html` and images; keep `identity.json` separate until scoring. Capture stores exact revisions, run statuses/timestamps and metadata/usage. Missing usage stays missing. Images cover the first 1800px: test full pages/interactions separately.

Score six dimensions 1–5: brief fit, factual fidelity, specificity, hierarchy, responsive use and interaction use. Anchors: 1 fails the task, 3 usable with corrections, 5 fits the intent with no material defect observed. Record explicit acceptance separately:

```sh
bench --site SITE execute builder.ai.evaluation.rate \
  --kwargs '{"page_id":"PAGE_ID","ratings":{"brief_fit":3,"factual_fidelity":5,"specificity":3,"hierarchy":4,"responsive_use":3,"interaction_use":3},"accepted":false,"corrections":2,"notes":"Describe observed issues"}'
```

Compare medians/spread for quality, elapsed time, actual usage/cost where known, repairs and corrections to acceptance. Include failures/abandonment. Do not turn unknown bills into zero, completed streams into acceptance, or a few screenshots into a MotionSites-level claim. No live corpus or blind human comparison was run during implementation.
