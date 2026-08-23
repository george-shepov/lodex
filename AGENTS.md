# LODEX Codex Instructions

These instructions apply to the entire repository.

## Source of truth

- GitHub `origin/main` is the production source of truth.
- Never infer deploy state from an old local checkout. Compare the local commit with `origin/main` first.
- Production source lives in `/home/shepov/deployments/lodex` on the VPS, but source changes must be authored and committed outside the VPS, pushed to GitHub, and deployed from `main`.
- Preserve existing user changes. Do not use `git reset --hard`, `git checkout --`, forced pushes, or broad file deletion.
- Do not commit `.env.local`, vault output, API keys, tokens, customer uploads, database files, or files under `data/`.

## Branch and release policy

- `main` is production and must remain deployable.
- Create short-lived branches from current `origin/main` for nontrivial work. Use names such as `work/<topic>` or `fix/<topic>`.
- Use `develop` only when a change genuinely needs an integration branch. Do not leave completed work parked on miscellaneous branches.
- Treat LKGC as a release tag or deliberately maintained recovery ref, not as a place for day-to-day edits.
- Before merging, update from `origin/main`, resolve conflicts deliberately, run the relevant checks, and preserve a fast-forward or reviewable PR history.

## Required start-of-work checks

Run these before editing:

```bash
git status --short --branch
git remote -v
git fetch origin --prune
git rev-parse HEAD
git rev-parse origin/main
```

If the worktree is dirty, identify ownership of every change. Do not discard it. If the checkout is stale, create a fresh branch/worktree from `origin/main` and transplant only the intended change.

## Validation

For backend changes:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r backend/requirements.txt
python -m pytest -q backend/tests
```

For frontend changes:

```bash
cd frontend
npm ci
npm run test:intake
npm run build
```

For integration validation:

```bash
docker network inspect shepov_edge >/dev/null 2>&1 || docker network create shepov_edge
docker compose up --build
```

Report checks that could not run. Never describe unexecuted tests as passing.

## Intake product rule

LODEX is a lead-closing assistant, not a two-question form. It should ask one focused question at a time for as long as an answer materially improves scope, pricing, materials, access, safety, sequencing, scheduling, or customer confidence. It should not repeat answered questions, prolong simple jobs, or force scheduling before a complex lead is truly ready. The goal is a well-qualified closed job and a happy customer.

## Deployment

- A push to `main` that changes `frontend/**`, `backend/**`, `docker-compose.yml`, or the deploy workflow triggers `.github/workflows/deploy.yml`.
- Prefer the GitHub Actions deployment. Do not SSH into production for routine source edits.
- The workflow must refuse to deploy over VPS-only source changes, fast-forward the clean VPS checkout to `origin/main`, materialize allowlisted secrets, rebuild `api` and `web`, restart them, and verify the public site.
- Never print `.env.local`, vault material, GitHub secrets, private keys, or container environments.
- Roll back with a GitHub revert commit and a normal deployment. Do not rewrite production history.

## VPS operating boundary

On the VPS, default to read-only diagnostics:

```bash
cd /home/shepov/deployments/lodex
git status --short --branch
git fetch origin main
git rev-parse HEAD
git rev-parse origin/main
docker compose ps
docker compose logs --tail=200 api web
```

Do not manually edit tracked source, `.env.local`, vault policy, generated secret files, or customer data. A manual deploy is permitted only when explicitly requested and must follow the same clean-checkout, fast-forward-only, vault, build, restart, and verification sequence as `.github/workflows/deploy.yml`.

See `docs/CODEX-OPERATIONS.md` for copy/paste local and VPS prompts and the full runbook.
