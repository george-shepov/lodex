# Yelptomate

LODEX's browser bridge for Yelp for Business messaging.

The goal is to make the Yelp inbox machine-readable and safely automatable so the lead-closing workflow can continue after Yelp's initial email notification. The harness deliberately supports **Playwright, Puppeteer, and Selenium behind one CLI** so we can test Yelp's live web UI and keep whichever engine proves most stable.

## Current phase

Phase 0 is a selector/discovery harness plus guarded reply support:

1. Open `https://biz.yelp.com/` in a persistent browser profile.
2. Log in manually the first time for each engine. No Yelp password is stored in this repo.
3. Navigate to Inbox.
4. Capture a screenshot, visible controls, current page text, and candidate conversation links.
5. Find a conversation by customer name.
6. Fill the reply composer.
7. **Do not click Send unless `--send` is explicitly supplied.**

That gives us a quick live-DOM loop without hard-coding brittle CSS before we see the authenticated Yelp inbox.

## Install

```bash
cd automation/yelptomate
npm install
npx playwright install chromium
```

Chrome/Chromium should also be installed for Selenium. Puppeteer installs its own compatible browser unless configured otherwise.

## First run: Playwright

```bash
npm run discover -- --engine playwright
```

A browser opens. Complete Yelp for Business login if requested, then return to the terminal and press Enter. The local browser profile is persisted under `profiles/playwright/`.

The command writes:

- full-page screenshot under `artifacts/`
- JSON DOM discovery snapshot under `artifacts/`
- candidate Yelp message/inbox links

## Try all three engines

```bash
npm run discover -- --engine playwright
npm run discover -- --engine puppeteer
npm run discover -- --engine selenium
```

Each engine gets its own persistent browser profile so they do not fight over Chrome's profile lock.

## Read inbox candidates

```bash
npm run inbox -- --engine playwright
```

This emits current page text and candidate conversation links as JSON. Once the authenticated DOM snapshot tells us Yelp's stable attributes, we can replace the broad heuristics with explicit selectors.

## Reply preview

```bash
npm run reply -- \
  --engine playwright \
  --lead "Elizabeth Knight" \
  --text "Hi Elizabeth, thanks for the photos. I can help with this..."
```

This opens the matching thread, fills the composer, and saves a screenshot. It **does not send**.

To send after validation:

```bash
npm run reply -- \
  --engine playwright \
  --lead "Elizabeth Knight" \
  --text "Hi Elizabeth, thanks for the photos. I can help with this..." \
  --send
```

## Why three engines?

This intentionally follows the old LinkedIn automation lesson: browser automation is mostly a battle against dynamic DOM changes, session behavior, and framework quirks. The business logic should not care whether Selenium, Puppeteer, or Playwright is driving the browser.

Default order for Yelp testing:

1. **Playwright**: primary candidate, strong locators and persistent contexts.
2. **Puppeteer**: Chromium-native comparison/fallback.
3. **Selenium**: mature fallback and useful cross-check against the older LinkedIn implementation.

## Next phases

### Phase 1: authenticated inbox model

Turn each conversation into a normalized object:

```json
{
  "leadId": "yelp-thread-id",
  "customer": "Elizabeth Knight",
  "service": "Window replacement",
  "location": "Madison, OH 44057",
  "messages": [],
  "unread": true,
  "phoneAvailable": false,
  "lastActivityAt": "..."
}
```

### Phase 2: closer loop

Feed normalized conversations to the LODEX lead-closing service, which returns one of:

- `reply`
- `ask_for_photos`
- `ask_measurement`
- `quote`
- `schedule`
- `call_required`
- `human_review`

Every outbound action gets an audit record containing the incoming message, selected action, generated response, timestamp, and browser receipt screenshot.

### Phase 3: sold-job handoff

When a lead reaches `scheduled` or `sold`, create a job packet:

- agreed scope
- exclusions and customer promises
- address / schedule
- price / deposit status
- materials and procurement
- tools
- crew skill requirements
- job hazards
- crew briefing
- job-specific training checklist
- completion photos / sign-off requirements

### Phase 4: autonomous queue

Run the browser worker on the LODEX host with:

- persistent authenticated session
- queue/retry handling
- screenshot and DOM evidence for failures
- rate limiting
- customer-level locking so two workers never reply to the same lead
- human-review gates for unusual pricing, safety, disputes, refunds, legal threats, or anything outside approved operating policy

## Security

- Browser profiles are ignored by git.
- Do not commit cookies, session files, passwords, or `.env` secrets.
- Prefer manual login/session persistence rather than storing Yelp credentials in source or config files.
- Keep outbound sending guarded until selectors are proven against the authenticated account.
