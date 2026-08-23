# Running Codex for LODEX

This runbook keeps local development, GitHub, and the production VPS from drifting apart.

## Local Codex prompt

Start Codex from the repository root and give it this prompt, replacing the final task line:

```text
Read AGENTS.md and docs/CODEX-OPERATIONS.md completely before acting.
Treat origin/main as the source of truth. Begin with read-only Git status, remote, fetch, and commit comparisons. Preserve every existing local change and do not use reset --hard, checkout-based file discards, forced pushes, or broad deletion.
If this checkout is stale or dirty, create a fresh worktree or branch from origin/main and bring over only the intended change.
Implement the requested change, run the relevant backend/frontend tests and build, show any validation that could not run, commit the result, and stop before publishing unless I explicitly ask you to push or deploy.

Task: <describe the LODEX change here>
```

Recommended shell start:

```bash
cd /path/to/lodex
git status --short --branch
git fetch origin --prune
codex
```

## Local application

Create local configuration without overwriting an existing one:

```bash
cd /path/to/lodex
test -f .env.local || cp .env.example .env.local
docker network inspect shepov_edge >/dev/null 2>&1 || docker network create shepov_edge
docker compose up --build
```

Open `http://localhost:4175`. The API binds locally on `127.0.0.1:8015`.

Run checks independently when diagnosing a failure:

```bash
cd /path/to/lodex
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r backend/requirements.txt
python -m pytest -q backend/tests

cd frontend
npm ci
npm run test:intake
npm run build
```

Never paste real secrets into a Codex prompt. Configure them through `.env.local` locally and the approved vault path in production.

## Normal production deployment

The normal release path is:

1. Update a short-lived branch from current `origin/main`.
2. Run backend tests, frontend intake tests, and the frontend build as applicable.
3. Merge the reviewed change to `main` without rewriting history.
4. Let `.github/workflows/deploy.yml` fast-forward and rebuild the VPS checkout.
5. Confirm the workflow succeeded and verify `https://lodex.giorgiy.org/`.

Useful verification:

```bash
curl --fail --silent --show-error --max-time 20 https://lodex.giorgiy.org/ >/dev/null
curl --fail --silent --show-error --max-time 20 \
  -D - -o /dev/null https://lodex.giorgiy.org/lodex-logo.png
```

## VPS Codex prompt

Start Codex only after connecting to the VPS and changing into the production repository:

```bash
ssh <your-configured-vps-alias>
cd /home/shepov/deployments/lodex
codex
```

Use this prompt for production diagnostics:

```text
You are operating in the LODEX production checkout on the VPS.
Read AGENTS.md and docs/CODEX-OPERATIONS.md completely. Begin read-only: show the current branch, concise Git status, HEAD, origin/main, Docker Compose status, and the last 200 lines of api/web logs.
Do not edit tracked source, do not expose or modify .env.local or vault material, do not print container environments, do not delete customer data, and do not use reset --hard, checkout-based discards, forced Git operations, or Docker volume deletion.
GitHub main is authoritative. For routine changes, diagnose here and implement in a normal local branch instead.
If I explicitly request a manual deployment, first prove that the checkout is on main and has no non-runtime changes, then use fetch plus a fast-forward-only merge, follow the vault and Docker sequence in .github/workflows/deploy.yml, and verify the public site. Stop on any dirty checkout, secret materialization failure, failed build, unhealthy container, or failed public check.

Task: <describe the production diagnosis here>
```

## Read-only VPS diagnosis

```bash
cd /home/shepov/deployments/lodex
git status --short --branch
git fetch origin main
printf 'HEAD        '; git rev-parse HEAD
printf 'origin/main '; git rev-parse origin/main
docker compose ps
docker compose logs --tail=200 api web
curl --fail --silent --show-error --max-time 20 https://lodex.giorgiy.org/ >/dev/null
```

The one known legacy runtime file, `.lodex-db.env`, may be present as an untracked VPS-only file. Codex must not read, print, commit, delete, or repurpose it. The deploy workflow already excludes only that named runtime file from its source-drift check.

## Emergency manual deployment

Use this only when an authorized operator explicitly requests it and GitHub Actions cannot complete the normal deployment. Read `.github/workflows/deploy.yml` immediately before proceeding because it is authoritative.

Minimum safety gates:

```bash
cd /home/shepov/deployments/lodex
test "$(git branch --show-current)" = main
vps_changes="$(git status --porcelain --untracked-files=all | grep -v '^?? \.lodex-db\.env$' || true)"
test -z "$vps_changes"
git fetch origin main
git merge --ff-only origin/main
test "$(git rev-parse HEAD)" = "$(git rev-parse origin/main)"
```

After those gates, follow the checked-in workflow for vault materialization, `docker compose build api web`, `docker compose up -d api web`, container checks, and public HTTP verification. Do not improvise around a failed gate.

## Recovery

- Prefer `git revert <bad-commit>` in GitHub, merge the revert to `main`, and allow the normal workflow to redeploy.
- Preserve `data/` and Docker volumes. Never use `docker compose down -v` during ordinary recovery.
- If production contains tracked or untracked source drift, stop and inventory it. Do not overwrite or delete it merely to make deployment pass.
- Record the failing commit, workflow run, container status, and relevant redacted logs before changing anything.
