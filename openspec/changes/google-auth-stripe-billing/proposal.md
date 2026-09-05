## Why

Homerun is a shared studio at `https://homerun.love`. Anyone who can open it can see every conversation and publish more pages. We need each operator to sign in, own only their pages, and pay for pages beyond a small free set so the hosted product can grow without an unbounded OpenRouter bill.

## What Changes

- **BREAKING:** Studio chat and conversation APIs require a signed-in Google account. The unauthenticated three-pane studio is gone on Civo and in local runs that have Google OAuth configured.
- Operators register and log in with Google (no email/password). First Google consent creates the user.
- Each conversation / sales page belongs to exactly one user. Lists, chat, leads inbox, and generate only operate on that user’s pages.
- A user may publish **3 pages without a card**. Creating a **4th** page requires a Stripe payment method first.
- The first 3 pages stay free. Each extra page is free for **12 months after its first publish**, then billed **annually per extra page** (Stripe). Amount lives in a Stripe Price, not in application code.
- Published sales pages stay public for visitors (lead form included). Failed renewal after a grace period unpublishes that extra page until payment succeeds.
- Pages already on the instance with no owner stay live at their URLs but do not appear in any Google user’s studio unless a configured legacy owner email claims them.

## Capabilities

### New Capabilities

- `user-auth`: Google OAuth sign-in/register, session cookie, current-user API, logout. Studio UI is gated until signed in.
- `page-billing`: Free-page quota (3), Stripe Setup / Checkout to store a card, annual subscription per extra page after a 12-month trial, webhooks, billing-required errors in the studio.

### Modified Capabilities

- `studio-chat`: Conversation list, create, messages, and leads are scoped to the signed-in user. New conversation is blocked when the free quota is exhausted and no card is on file.
- `static-hosting`: Visitor `GET /{slug}/` stays public while the page is published. An extra page whose renewal fails is unpublished (not served) after grace. Reserved path prefixes include auth and Stripe webhook routes.

## Impact

- `studio/app.py`, `studio/db.py`, `studio/config.py`, `web/src/*`: session middleware, OAuth routes, ownership checks, login chrome, billing gate.
- New modules for Google OAuth, Stripe customers/subscriptions/webhooks.
- SQLite: `users`, `user_id` on conversations, billing columns / `subscriptions` table.
- Secrets (not committed): `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `SESSION_SECRET`, `STRIPE_SECRET_KEY`, `STRIPE_WEBHOOK_SECRET`, `STRIPE_PAGE_ANNUAL_PRICE_ID`. Optional `HOMERUN_LEGACY_OWNER_EMAIL`.
- Civo ConfigMap/Secret + Ingress: OAuth redirect `https://homerun.love/auth/google/callback`, webhook `https://homerun.love/api/billing/stripe/webhook`.
- Dependencies: Google OAuth library, Stripe Python SDK, session signing.
- Tests: unauthenticated 401, isolation between users, quota, webhook state transitions.
- Visitor lead `POST /api/pages/{slug}/leads` remains unauthenticated.
