# Bob review and implementation evidence

Start with the [current coverage matrix](pr-1023-coverage.md), which maps the original findings and design goals to the implementation and its limits. The [2026-11-02 implementation report](implementation-2026-11-02.md) includes the public experiment, validation results and a screenshot of the real raster previews. [Machine-readable evidence](evidence-2026-11-02.json) preserves counts and boundaries.

The [UI follow-up](ui-2026-11-02.md) adds desktop-only direction cards, optional section details and tweaks, and next-step chips, with screenshots and focused validation.

The [budget and suggestion follow-up](budget-and-next-steps-2026-11-02.md) raises the cumulative turn reservation to one million tokens and replaces keyword chips with suggestions generated in the normal response. It also explains the existing automatic context compaction.

The [Flow LOC investigation](flow-loc-2026-11-02.md) measures current Bob and estimates gross deletions, replacement adapters and net savings for three migration boundaries. It distinguishes today's async runtime from the older review and includes a [file-level LOC inventory](flow-loc-2026-11-02.csv).

- Original review: [main findings](bob-review-2026-11-01.md), [runtime](runtime-findings.md), [sessions](session-findings.md), [capabilities](capability-findings.md), and [82 scenarios](bob-review-scenarios.md).
- Server execution: [Flow analysis](flow-session-review.md), [server contract](flow-server-contract.md), and [current runtime setup](../../builder/ai/RUNTIME.md).
- Experiment setup: [media providers and budgets](../../builder/ai/STOCK_ASSETS.md) and [acceptance/live evaluation commands](../../builder/ai/acceptance/README.md).
- Historical implementation: [first implementation](implementation-2026-11-01.md), [previous coverage](pr-1023-coverage-2026-11-01.md), [first deployment](public-deployment.md), and [audit probes](probes/README.md).

Historical reports describe the code at their stated revision. Passing deterministic regressions does not certify all 82 scenarios or establish design quality; the live corpus and blind human comparison remain unperformed.
