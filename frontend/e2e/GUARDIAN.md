# Guardian exploratory QA

Guardian complements the deterministic Playwright smoke tests in this directory.

## Mission

Act as a first-time LODEX customer. Explore the product button by button and flow by flow. Do not assume a control is correct merely because it is clickable.

For every interactive control encountered:

1. Record its accessible role/name and current page/route.
2. Infer its likely purpose from visible context.
3. Exercise it using safe/disposable data.
4. Observe the resulting UI, URL, network/console errors, validation, and focus state.
5. Classify the result as `clear`, `works-but-ambiguous`, `broken`, or `intent-unknown`.
6. If intent is unknown, append one concise product question to `docs/guardian/questions.md` instead of inventing behavior.

## Question discipline

Ask about product intent only when the expected outcome cannot be established from the UI, existing tests, `AGENTS.md`, or other repo documentation. Once the owner answers a question, turn that answer into either:

- a durable rule in repo documentation; or
- a Playwright assertion/regression test.

Do not repeatedly ask settled questions.

## Evidence

On failure or ambiguity, preserve enough evidence to reproduce the observation: route, control name, steps, screenshot/trace when available, and relevant console/network error. Never capture secrets or customer data.

## Mutation boundary

Do not submit payments, send real customer communications, delete production data, change production configuration, or perform other irreversible actions during exploratory QA without explicit approval.
