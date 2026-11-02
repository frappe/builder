# Offline audit probes

These reproduce findings at `a112a3e6`; they are not fixes or a replacement for the project's integration suite. Several assertions deliberately pass when the defective behavior is observed. Read the companion findings before interpreting results.

The archived probes are formatted for repository linting; their fixed local-source `exec` calls have scoped analyzer annotations. They retain their original test behavior and are not application code.

The scripts retain the audit environment's absolute checkout/dependency paths and use `/tmp` for fixtures. They are environment-specific; adjust those paths when reproducing elsewhere. The Python harnesses use mocked/stubbed Frappe dependencies and do not initialize a live site. The viewport probe uses a local Playwright installation and cached Chromium executable.

Original runs:

```sh
node reviews/bob/probes/bob-review-repros.cjs
python3 -B reviews/bob/probes/bob-review-repros.py
PYTHONDONTWRITEBYTECODE=1 /home/t3run/frappe-bench/env/bin/python reviews/bob/probes/bob-backend-experiments.py
PYTHONDONTWRITEBYTECODE=1 /home/t3run/frappe-bench/env/bin/python reviews/bob/probes/bob-review-probes.py
node reviews/bob/probes/bob-review-probes.cjs
PYTHONDONTWRITEBYTECODE=1 /home/t3run/frappe-bench/env/bin/python reviews/bob/probes/bob-review-boundaries.py
node reviews/bob/probes/viewport.cjs
```

Run the capability Python probe before its JavaScript companion: it creates the rejected-operation and form-script fixtures the latter reads. The session checks and backend tests are separate harnesses. Their test selections overlap with the capability selection; do not add their counts as unique tests.
