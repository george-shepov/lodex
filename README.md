# LODEX Construction Maintenance and Repair

Customer-facing handyman intake: a visitor describes what needs to be built or fixed, uploads a photo/video, confirms the working assumptions in chat, and requests an in-person meet-and-greet before a final price is set.

## Run locally

1. Copy `.env.example` to `.env.local` and supply the server-side `OPENAI_API_KEY` from the vault.
2. `docker compose up --build`
3. Open `http://localhost:4175`.

The API intentionally never represents an AI response as a final estimate. Image uploads are passed to the server-side vision model; video uploads yield a representative frame with `ffmpeg` when available.

## Lead storage and owner alerts

LODEX runs its own isolated Postgres database in the Compose deployment. Every appointment and support request is stored in `lodex_leads`, and existing local requests are imported on startup. The local JSONL files in `data/` remain as a fallback. Storage alone does **not** send an email or SMS.

To alert the owner, configure SMTP (email), Twilio (SMS), or both using the variables in `.env.example`. Notifications are best-effort and never prevent a lead from being stored.

## Deploy

Use one edge proxy for public HTTPS. Route `lodex.giorgiy.org` to the web container and proxy `/api/` to the API container. Put `OPENAI_API_KEY` in the VPS vault / runtime environment—never in GitHub or browser code.
