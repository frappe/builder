# Bob runtime and recovery

Bob supports the existing RQ path and an opt-in async daemon. The daemon awaits coordinator, page-generation and research model streams outside Frappe web/RQ workers. Short Frappe execution slices close their database connection before awaiting a provider.

This adopts the execution boundary studied in Frappe Flow without installing Flow or raising Builder's baseline. Reviewed Flow 0.1.20 required Python 3.14/LiteLLM 1.103.2; Builder declares Python 3.10+ and pins LiteLLM 1.95.1. See the dated [Flow review](../../reviews/bob/flow-session-review.md).

## Enable and supervise

Migrate and build first, then configure:

```sh
bench --site SITE migrate
bench --site SITE set-config builder_ai_runtime async
/path/to/bench/env/bin/python -m builder.ai.runtime \
  --site SITE --sites-path /path/to/bench/sites --concurrency 8 --threads 4
```

Run one supervised process per site with the bench's OS user/environment. The command resolves and enters the sites directory before initializing Frappe logging. Use the deployment's supervisor/systemd/container mechanism. Example systemd fields, adapted to the actual host:

```ini
[Service]
User=frappe
WorkingDirectory=/path/to/bench/sites
ExecStart=/path/to/bench/env/bin/python -m builder.ai.runtime --site SITE --sites-path /path/to/bench/sites --concurrency 8 --threads 4
Restart=on-failure
RestartSec=3
TimeoutStopSec=240
```

Keep normal Frappe scheduler, web and realtime processes running. The daemon polls durable queued rows every second. Async configuration without a running daemon leaves work queued: monitor process health and queue age. The scheduled dispatch job is `builder.ai.runs.dispatch_queued_runs`; journal pruning runs daily. To return to RQ, stop the daemon and set `builder_ai_runtime` to `rq`. Queued work uses normal dispatch. `builder_ai_queue` can select a dedicated RQ queue, which needs a worker.

## Capacity boundary

Model waits and OAuth refreshes are async. Batches flush even when the next token is delayed; silent streams can be cancelled without another token. Ordinary browser/image/search/plugin tools use the daemon's bounded thread pool and can hold a Frappe context while running. Paid-action confirmations still occupy their web request. Async orchestration does not make every tool nonblocking.

Only adjacent allowlisted independent reads overlap, up to four: document/schema reads, DocType listing, record queries and page-script listing. Each uses a separate permission-checked slice. Writes retain order. Terminal questions/confirmations preserve the remaining operations for continuation. RQ executes the same workflow serially.

## Durable state

- `Builder AI Run` owns admission, user/model identity, queued payload, cancellation, heartbeat, final metadata and event sequence. Duplicate request IDs reuse admission. Start/mutation recheck access.
- `Builder AI Event` journals committed socket events. Clients replay missing events by cursor and reconcile authoritative page/chat state. Stream retention is seven days; transcripts and effect records remain.
- `Builder AI Artifact` stores native design candidates, large results, verification, effect receipts, media requests, plugin candidates and evaluation records outside ordinary transcripts.
- Revision checks refuse stale writes and undo that would erase newer work. Shared documents have conflict-checked receipts. Confirmed external/schema/plugin/global actions prevent automatic page/chat Revert across their boundary; history stays intact with an explanation.
- Ambiguous external actions require reconciliation from the actual result before retry. Purchases, DDL and arbitrary external effects cannot be undone as one database transaction.
- Graceful shutdown persists cancellation. Synchronous slices must settle. Crash recovery uses committed state and marks stale runs interrupted; it does not restore a Python stack or interrupted provider stream. Retry continues from saved page/chat state.

The runtime enforces a ten-minute run limit and defaults to a 300,000-token conservative reservation budget (`bob_run_token_budget`). Models declare context/output limits and vision/tool/streaming capabilities. `bob_model_prices` maps model IDs to `input_per_million`/`output_per_million` rates for estimates. Unknown prices or usage remain unknown. Images use separate [media budgets](STOCK_ASSETS.md).

The daemon adds no public port or unauthenticated mutation callback. Protect normal site configuration/backups and use run IDs rather than credentials/full transcripts in operational logs.
