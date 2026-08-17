<p align="center">
  <img src="frontend/public/lodex-logo-home-business.webp" alt="LODEX Home & Business Services" width="760" />
</p>

# LODEX Home & Business Services

Customer-facing project intake for LODEX Home, Business, and Enterprise: a visitor chooses the right division, describes the work, uploads a photo/video, confirms the working assumptions in chat, and requests the appropriate next step.

The intake uses service-specific qualification playbooks. Required questions continue until the facts needed for that service are covered; after qualification, the assistant may ask at most two material extras. Customer side questions are answered directly and never consume that extra-question budget.

AI requests use the Responses API with a three-tier GPT-5.6 router. Luna with medium reasoning handles ordinary intake and image review. Cross-service, property-strategy, ambiguous, or unusually long cases escalate to Terra with high reasoning. Safety-sensitive and structurally consequential cases escalate to Sol with xhigh reasoning. The qualification model may also recommend an upward escalation when the initial route needs stronger judgment; routes never downgrade within a request.

## Run locally

1. Copy `.env.example` to `.env.local` and supply the server-side `OPENAI_API_KEY` from the vault. The checked-in GPT-5.6 model and reasoning defaults can be overridden there when needed.
2. `docker compose up --build`
3. Open `http://localhost:4175`.

### Assessment pricing and Stripe

LODEX uses Stripe-hosted Checkout only after the backend has resolved and persisted an assessment amount. Home pricing uses the selected project size plus route distance, Business uses a configurable default assessment, and Enterprise requires custom review. Add real credentials and any desired pricing overrides to `.env.local` (never commit this file):

```env
STRIPE_SECRET_KEY=sk_test_...
STRIPE_WEBHOOK_SECRET=whsec_...
STRIPE_CURRENCY=usd
LODEX_HOME_SMALL_VISIT_CENTS=5000
LODEX_HOME_SEVERAL_VISIT_CENTS=10000
LODEX_HOME_MAJOR_VISIT_CENTS=15000
LODEX_BUSINESS_ASSESSMENT_CENTS=30000
LODEX_INCLUDED_DISTANCE_MILES=5
LODEX_DISTANCE_RATE_CENTS_PER_MILE=250
```

Configure a Stripe webhook endpoint at `/api/payments/webhook` for `checkout.session.completed`, `checkout.session.async_payment_succeeded`, `checkout.session.async_payment_failed`, and `checkout.session.expired`. The amount is controlled by the server and is never accepted from the browser. Until a route-distance provider is configured, new Home requests safely remain under manual pricing review; the server never invents mileage.

The API intentionally never represents an AI response as a final estimate. Image uploads are passed to the server-side vision model; video uploads yield a representative frame with `ffmpeg` when available. Uploaded media is stored locally under `data/uploads`; production deployment must use protected persistent storage and a configured lead notification channel.

## Deploy

Use one edge proxy for public HTTPS. Route `lodex.giorgiy.org` to the web container and proxy `/api/` to the API container. Put `OPENAI_API_KEY` in the VPS vault / runtime environment—never in GitHub or browser code.
