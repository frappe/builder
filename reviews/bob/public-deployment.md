# Bob final public deployment and bounded browser smoke

Historical deployment report from 2026-11-01. See the [2026-11-02 implementation and evidence](implementation-2026-11-02.md) for the current raster previews, user-configured models and async service. The SVG/no-provider statements below describe the earlier deployment.

The thumbnail route added in this deployment also intercepted dynamic token stylesheets. The [2026-11-02 stylesheet correction](published-tokens-2026-11-02.md) restores published fonts and colours; use the corrected image-only route below.

Live URL: https://slight-max-printed-worthy.trycloudflare.com/

Login: https://slight-max-printed-worthy.trycloudflare.com/login?redirect-to=%2Fbuilder

Isolated deployment: `/home/t3run/bob-test-deploy`; bench site `bob-test.localhost`.
Source: shared `/home/t3run/builder`, branch `feat/bob-design-workflow`, including uncommitted frontend work.

## Scope and deployment

- Read repository `AGENTS.md`, `/tmp/bob-test-site-setup.md`, and `/tmp/bob-frontend-implementation.md`.
- No application code edits, commits, subagents, provider configuration, new credentials, or model calls.
- `/home/t3run/frappe-bench/apps/builder` still resolves to `/home/t3run/builder-extensions`; never repointed.
- Frontend build completed successfully with isolated Vite 8.3.5 (`built in 4.61s`). No additional schema migration was needed or run.
- Cache cleared and `web`, `worker`, `worker-ai`, and `realtime` restarted after build. They were restarted again after root confirmed backend implementation and fixture cleanup were complete, before the final card smoke, and once more after this task's fixture cleanup. Final restart PIDs: web 413169, worker 413175, worker-ai 413180, realtime 413182.
- Scheduler remained paused throughout root's backend tests. Root subsequently enabled/resumed it and started its process after cleaning backend fixtures; this task preserved that final state. No scheduler activation was performed by this task.

Exact deployment commands:

```bash
bash /home/t3run/bob-test-deploy/scripts/build.sh > /home/t3run/bob-test-deploy/logs/build.log 2>&1
cd /home/t3run/bob-test-deploy/bench/sites
PYTHONDONTWRITEBYTECODE=1 /home/t3run/bob-test-deploy/bench/env/bin/python -m frappe.utils.bench_helper frappe --site bob-test.localhost clear-cache
python3 /home/t3run/bob-test-deploy/scripts/control.py restart web worker worker-ai realtime
python3 /home/t3run/bob-test-deploy/scripts/control.py status
```

The initial cache-clear command used `../env/bin/python` from the same sites directory and succeeded with Python prefix-path warnings; the final command used the absolute path above without those warnings.

## Deployment issue fixed

The editor initially requested 21 distinct standard block thumbnails under `/builder_assets/`, all returning 404. Files already existed under the deployment app's `www/builder_assets`; nginx had no static route for them. The original broad static alias also served the Jinja source of `tokens.css` and `variables.css`, which was missed by the thumbnail smoke. Corrected on 2026-11-02 in `/home/t3run/bob-test-deploy/nginx.conf`:

```nginx
# CSS in builder_assets is rendered by Frappe; only images are static.
location ~* ^/builder_assets/.*\.(?:png|jpe?g|webp|svg|gif|avif|ico)$ {
    root /home/t3run/bob-test-deploy/bench/apps/builder/builder/www;
    expires 1h;
}
```

The existing denial for `.map`, `.py`, and `.json` files also covers this route. Existing dotfile denial remains effective.

```bash
/usr/sbin/nginx -t -c /home/t3run/bob-test-deploy/nginx.conf -p /home/t3run/bob-test-deploy
/usr/sbin/nginx -c /home/t3run/bob-test-deploy/nginx.conf -p /home/t3run/bob-test-deploy -s reload
curl --silent --show-error --output /dev/null --write-out 'Public thumbnail HTTP %{http_code}\n' 'https://slight-max-printed-worthy.trycloudflare.com/builder_assets/Button/button.png'
```

nginx config test and reload succeeded; public thumbnail returned HTTP 200. Subsequent full editor smoke had no HTTP 4xx/5xx responses.

## Browser method and coverage

Called T3 `preview_status` (unavailable), then `preview_open`. Exact error:

> Preview automation open failed: This host blocks the sandbox T3's browser runs in (AppArmor on Ubuntu 23.10+). Run `sudo env "PATH=$PATH" t3 browser setup` on the host once to allow it, then try again.

Used existing local Playwright/Chromium fallback. No browser security settings were changed. Existing private Administrator password was read internally for normal login, never printed.

```bash
node /home/t3run/bob-test-deploy/scripts/verify-browser.cjs > /home/t3run/bob-test-deploy/logs/browser-verification.log 2>&1
cd /home/t3run/bob-test-deploy/bench/sites
PYTHONDONTWRITEBYTECODE=1 /home/t3run/bob-test-deploy/bench/env/bin/python /home/t3run/bob-test-deploy/scripts/bob-smoke-fixture.py > /home/t3run/bob-test-deploy/logs/bob-smoke-fixture-create.log 2>&1
timeout 180 node /home/t3run/bob-test-deploy/scripts/verify-bob-smoke.cjs > /home/t3run/bob-test-deploy/logs/bob-smoke-browser.log 2>&1
```

Verified:

- Public HTTPS landing renders `Bob test site`; anonymous `/builder` redirects to `/login`.
- Normal Administrator login loads the authenticated dashboard. Session cookie: Secure, HttpOnly, SameSite=Lax.
- Authenticated Socket.IO connects and upgrades to `websocket`.
- Temporary page opens in the actual editor; Bob panel opens by its registered keyboard shortcut.
- Live setup API reports `configured: false`, `models: 0`, `providers: 0`; live UI shows `Connect a model`.
- Persisted assistant card loads through the real session API with two SVG layout choices.
- Preview-only asset option renders its label and separate `Open original library page` link, with no library navigation/download or submission.
- Multistep direction/asset selections, business-name input, and current step survive an actual page refresh. Fallback submit button renders; it was not submitted.
- UI Revert confirmation makes one actual `builder.ai.api.revert_to_message` request, HTTP 200. Snapshot restores blocks from `After deterministic Bob edit` to `Before deterministic Bob edit` and restores the page data script. Returned and freshly fetched conversation messages are empty; visible editor reflects the restored blocks.

To render cards while no models are configured, the smoke helper changes only `ai_setup_state.message.configured` to true in that browser's intercepted response, after verifying the real setup screen. Models/providers remain zero in the database; history, snapshots, editor, and Revert use real APIs. This is deterministic UI/integration coverage, not live AI generation or provider execution. The run endpoint is guarded in the helper; no run requests occurred.

## Outstanding external browser error

The external plugin catalog at:

`https://preview.frappe.cloud/api/method/builder_hub.plugins.api.get_catalog?page=1&protocol_version=1`

fails on each editor load with `net::ERR_FAILED`. Chromium reports:

> Access to fetch ... from origin 'https://slight-max-printed-worthy.trycloudflare.com' has been blocked by CORS policy: The 'Access-Control-Allow-Origin' header has a value 'https://preview.frappe.cloud' that is not equal to the supplied origin.

The plugin resource leaves an unhandled `TypeError: Failed to fetch` in `plugins~76-CSwWU8K6.js`. This external catalog/CORS issue remains visible and recorded; it was not suppressed, proxied, mocked, or disabled. It did not prevent the bounded Bob checks. Consequently this is not a completely error-free editor smoke.

## Evidence and cleanup

All evidence is under `/home/t3run/bob-test-deploy/logs/`:

- `build.log`: final frontend build.
- `browser-verification.log`, `authenticated-editor.png`: public landing/login/dashboard/WebSocket smoke; no page errors or failed responses in that baseline.
- `bob-smoke-browser.log`, `bob-smoke-results.json`: final card/refresh/Revert run, full errors and failed-request URLs.
- `bob-unconfigured.png`: real no-model setup screen.
- `bob-svg-directions.png`: persisted SVG layout card.
- `bob-preview-asset.png`: preview-only asset control and separate source link.
- `bob-refresh-retained.png`: restored card draft after refresh.
- `bob-reverted.png`: actual restored canvas and rewound conversation.
- `bob-smoke-fixture.json`: exact fixture identifiers for scoped cleanup.
- `bob-smoke-initial-results.json` / `bob-smoke-initial-browser.log`: initial 404 evidence and extra-Next harness error.
- `bob-smoke-second-results.json` / `bob-smoke-second-browser.log`: successful real Revert followed by a helper request-count suffix assertion error (`/revert_to_message` instead of `.revert_to_message`); fixed in the final helper.

Smoke scripts created only under deployment `scripts/`: `bob-smoke-fixture.py`, `verify-bob-smoke.cjs`. Existing `verify-browser.cjs` was reused unchanged. The fixture title is exactly `Bob bounded browser smoke 2026-11-01`, distinct from root's backend fixtures. The first fixture and all its session/messages/snapshot were deleted before the final rerun; final fixture cleanup/status is recorded below.

Deployment processes are detached but not supervised/reboot-persistent. The Quick Tunnel hostname lasts for its current process. No paid infrastructure was created.

## Final result (2026-11-01, approximately 06:50 UTC)

Final bounded Bob helper exited 0: `passed: true`, `cleanEditor: false`. All seven recorded checks passed, including exactly one successful real Revert request and zero model run requests. There were zero failed HTTP responses. Three failed requests and three page errors correspond exactly to the external Hub CORS problem above, one per editor load.

Final temporary page `page-02ba2668`, session `hd673rg27q`, assistant `hd6rutiimb`, user message `hd67alkqdo`, and snapshot `hd6l3264p2` were deleted. Cleanup rechecked each exact identifier and returned false for every existence check. No backend/root fixtures were deleted by this task.

Exact final commands:

```bash
cd /home/t3run/bob-test-deploy/bench/sites
PYTHONDONTWRITEBYTECODE=1 /home/t3run/bob-test-deploy/bench/env/bin/python /home/t3run/bob-test-deploy/scripts/bob-smoke-fixture.py cleanup > /home/t3run/bob-test-deploy/logs/bob-smoke-cleanup.log 2>&1
python3 /home/t3run/bob-test-deploy/scripts/control.py restart web worker worker-ai realtime > /home/t3run/bob-test-deploy/logs/final-restart.log 2>&1
python3 /home/t3run/bob-test-deploy/scripts/control.py status >> /home/t3run/bob-test-deploy/logs/final-restart.log
node /home/t3run/bob-test-deploy/scripts/verify-browser.cjs > /home/t3run/bob-test-deploy/logs/browser-verification-final.log 2>&1
```

Final restart/status and post-restart public/login/dashboard/WebSocket helper exited 0. All ten services, including root's scheduler, were running. Final browser baseline again reported no page errors or failed HTTP responses and connected via WebSocket. `bob-smoke-cleanup.log`, `final-restart.log`, and `browser-verification-final.log` preserve the results. Source symlink isolation rechecked unchanged.

Root retains ownership of final backend lint/test/report. No comprehensive browser suite or further backend tests were added or run by this task.
