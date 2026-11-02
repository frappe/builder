# Bob transaction review — round 2

**Verdict: no remaining concrete defect found in the scoped fixes. Both prior P2 findings are resolved in the reviewed source.**

Read-only review under `/home/t3run/builder/AGENTS.md`, limited to `ToolSavepoint`, `AgentRunner.run_handler`, and the relevant integration regressions. No source edits, site initialization, database/Redis mutations, model calls, or spawned agents.

Evidence:

- `builder/ai/transactions.py:18–28` registers settlement callbacks after creating the savepoint. An explicit commit or full rollback marks it settled; subsequent cleanup returns without touching the destroyed savepoint or restoring stale callbacks/events. This covers the actual plugin commit followed by `FAILED` in `builder/ai/agent/tools/plugins.py:64–78, 114–128`.
- `builder/ai/agent/loop.py:1108–1131` keeps returned-FAILED rollback outside the handler exception block. The exception, cancellation, and returned-FAILED paths each make one rollback call; no second rollback is attempted by another exception branch.
- `builder/ai/transactions.py:10–11, 29–43` preserves earlier callbacks and snapshots the realtime buffer. Failed-tool events are removed while earlier events survive. If the buffer did not exist before the tool, cleanup restores absence, allowing Frappe's next event to register fresh flush/clear callbacks.
- `builder/ai/test_integration_boundaries.py:59–100` directly exercises committed-write-plus-FAILED, preservation of a preexisting event buffer through commit, and successful delivery after a failed first event. The existing test at lines 26–51 covers real script-file cleanup, callback filtering, and pending client operations. These test bodies match the reported regressions; I did not execute the site suite.

Independent verification: **eight isolated mock scenarios passed**, compiling the current ToolSavepoint/run_handler and supplied bench's actual Frappe CallbackManager, commit/rollback, and realtime function bodies via AST. SQL/savepoint validity and external emission were mocked; no Frappe/site imports were executed. Cases: commit followed by FAILED, exception, or cancellation (zero stale rollback attempts); uncommitted FAILED, exception, or cancellation (one rollback, earlier event preserved, failed event removed, cleanup and pending operations correct); failed first event followed by successful later event; explicit full rollback without event resurrection.

Limits: this is a focused code/probe review, not independent actual-site, filesystem, or deployment validation. The parent task owns those checks. Previously resolved broad-review findings were not reopened.

Reviewed SHA-256:

- transactions.py: `2b25eab5d603eea25e69e6946f1121b964487c4ad014894bbc5e7995e9c77c36`
- agent/loop.py: `7d23e3a1dd3dd2d76cb66b2dbe08b980d34085949341ac153d9434b42564bed1`
- test_integration_boundaries.py: `a527d1bbb20588b77fb8e1c000a798a16e9ce9ae4847c2cab90ce82ce7223f12`
