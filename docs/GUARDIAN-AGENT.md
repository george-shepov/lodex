# Guardian Agent

Guardian is a repo-resident QA and CI triage layer designed to stay provider-agnostic.

## Modes

### 1. CI triage

`.github/workflows/guardian-triage.yml` listens for failed LODEX workflows and opens a GitHub issue containing the failed run, commit, branch, actor, and failed jobs. The issue is the durable handoff point for a human or coding agent.

The first production rule is intentionally conservative: Guardian may diagnose automatically, but it must not push a repair directly to `main`.

### 2. Exploratory user QA

Use Playwright as the browser driver. The QA agent should behave like a first-time customer, inspect every visible control, and record:

- what it believes the control does;
- whether the purpose is obvious from the UI;
- whether the action succeeds;
- unexpected navigation, console, network, accessibility, or validation behavior;
- questions where product intent cannot be inferred safely.

Questions should be accumulated in `docs/guardian/questions.md` rather than blocking the whole test run. Examples:

- “The Upload video control accepts media, but what user outcome is supposed to happen immediately afterward?”
- “This button says Continue. Is it intended to advance even when the estimate confidence is still low?”
- “There are two paths to scheduling. Which one is canonical?”

Confirmed answers should become durable product rules or Playwright assertions so Guardian asks fewer questions over time.

### 3. Model/CLI router

Guardian should expose one conversation while treating individual coding systems as workers. Suggested adapters:

- `codex`
- `gemini`
- `gh copilot` or Copilot-supported VS Code agent mode
- `kilo`
- optional OpenAI-compatible gateways such as Kilo Gateway or local Ollama/LM Studio

The router owns conversation state, repo context, task IDs, and worker results. Workers receive bounded tasks and return structured summaries rather than talking directly to each other.

A minimal worker result contract:

```json
{
  "worker": "kilo",
  "task": "triage-ci",
  "status": "ok|blocked|failed",
  "summary": "...",
  "evidence": ["path:line", "workflow/job URL"],
  "proposed_changes": ["..."],
  "validation": ["..."]
}
```

## Browser-tab relay

Use Playwright MCP or CDP/extension mode to connect to an existing Chrome/Edge session. The router should maintain a named registry of pages/tabs and relay commands to a specific tab, for example:

- `github` -> repository/PR tab
- `prod` -> production LODEX
- `admin` -> authenticated admin UI
- `docs` -> provider/documentation tab

The single chat should accept instructions such as “compare prod and the PR preview,” then dispatch browser actions to both tabs and merge the observations into one answer.

## Safety / permissions

1. Read-only diagnosis is automatic.
2. Browser exploration may mutate only disposable/test data unless explicitly approved.
3. Code changes go to a short-lived branch and PR.
4. Production deploy remains governed by `AGENTS.md` and the existing deploy workflow.
5. Never expose secrets, cookies, tokens, `.env.local`, customer uploads, or vault material to a model that does not need them.

## Rollout

### Phase 1 — now
- CI failure issue creation.
- Manual agent handoff from the issue.
- Product-intent question log.

### Phase 2
- Add Playwright exploratory tests and trace/video artifacts.
- Generate a button/control inventory from accessibility snapshots.
- Convert answered questions into regression tests.

### Phase 3
- Add the local router service with CLI adapters.
- Add persistent browser-tab registry.
- Allow parallel review by multiple models and majority/critic synthesis.

### Phase 4
- Promote Guardian to a reusable GitHub App or reusable workflow so one installation can watch multiple repositories.
