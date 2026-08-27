# LODEX intake confidence demo

This Playwright package has two deliberately separate modes:

- `npm test`: deterministic CI smoke test. The API stays frozen at 0%, proving the browser-visible recovery introduced in PR #29.
- `npm run demo`: a paced 1920×1080 recording with the same deterministic responses.
- `LODEX_DEMO_LIVE=1 LODEX_DEMO_URL=https://lodex.giorgiy.org npm run demo`: optional recording against the live site.

## Record the master take

```bash
cd frontend
npm ci
cd e2e
npm install
npx playwright install chromium
npm run demo
```

The WebM master is written under `frontend/e2e/artifacts/`. Keep the raw master out of git.

## 30-second narration

**0–4 seconds**

“Most service forms collect words. LODEX builds understanding.”

**4–11 seconds**

“Tell it what you want—in plain language. Here, we’re planning a twelve-by-sixteen shed.”

**11–19 seconds**

“LODEX asks one useful question at a time, turning dimensions, access, timing, and priorities into a clear project scope.”

**19–25 seconds**

“Watch the confidence rise as real details are captured. No repetitive forms. No fake certainty.”

**25–30 seconds**

“LODEX Home and Business Services. Clear scope. Thoughtful work. No surprises.”

## Edit notes

- Add the narration after recording so browser timing remains deterministic.
- Duck licensed instrumental music 12–16 dB beneath the voice; do not commit copyrighted music.
- Start with a two-second logo/title card and finish on the LODEX tagline and project URL.
- Use gentle punch-ins around the customer message, assistant question, and confidence meter.
- Export H.264 MP4, 1920×1080, 30 fps; retain the WebM as the source master.
- For a public promotional clip, use a fictional project and never show customer names, addresses, phone numbers, uploads, project codes, admin pages, or notifications.
