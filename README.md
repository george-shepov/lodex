<p align="center">
  <img src="frontend/public/LODEX-Residential-and-Commercial-Services-logo.png" alt="LODEX Residential & Commercial Services" width="760" />
</p>

# LODEX Residential & Commercial Services

Customer-facing handyman intake: a visitor describes what needs to be built or fixed, uploads a photo/video, confirms the working assumptions in chat, and requests an in-person meet-and-greet before a final price is set.

The intake uses service-specific qualification playbooks. Required questions continue until the facts needed for that service are covered; after qualification, the assistant may ask at most two material extras. Customer side questions are answered directly and never consume that extra-question budget.

AI requests use the Responses API with a three-tier GPT-5.6 router. Luna with medium reasoning handles ordinary intake and image review. Cross-service, property-strategy, ambiguous, or unusually long cases escalate to Terra with high reasoning. Safety-sensitive and structurally consequential cases escalate to Sol with xhigh reasoning. The qualification model may also recommend an upward escalation when the initial route needs stronger judgment; routes never downgrade within a request.

## Run locally

1. Copy `.env.example` to `.env.local` and supply the server-side `OPENAI_API_KEY` from the vault. The checked-in GPT-5.6 model and reasoning defaults can be overridden there when needed.
2. `docker compose up --build`
3. Open `http://localhost:4175`.

### Stripe deposits

LODEX uses Stripe-hosted Checkout for a server-configured one-time project deposit. Add the following to the root `.env.local` (never commit this file):

```env
STRIPE_SECRET_KEY=sk_test_...
STRIPE_WEBHOOK_SECRET=whsec_...
STRIPE_CURRENCY=usd
LODEX_DEPOSIT_AMOUNT_CENTS=5000
```

Configure a Stripe webhook endpoint at `/api/payments/webhook` for `checkout.session.completed`, `checkout.session.async_payment_succeeded`, `checkout.session.async_payment_failed`, and `checkout.session.expired`. The deposit amount is controlled by the server and is never accepted from the browser.

The API intentionally never represents an AI response as a final estimate. Image uploads are passed to the server-side vision model; video uploads yield a representative frame with `ffmpeg` when available. Uploaded media is stored locally under `data/uploads`; production deployment must use protected persistent storage and a configured lead notification channel.

## Deploy

Use one edge proxy for public HTTPS. Route `lodex.giorgiy.org` to the web container and proxy `/api/` to the API container. Put `OPENAI_API_KEY` in the VPS vault / runtime environment—never in GitHub or browser code.
