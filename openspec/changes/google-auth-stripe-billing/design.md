## Context

See `proposal.md` for why. Today `studio/app.py` exposes `/api/conversations*` with no identity. `conversations` in `data/studio.sqlite` has no `user_id`. `web/src/api.js` uses `fetch` without cookies. FastAPI already serves the SPA at `/` and public slugs at `/{slug}/`. Civo is one replica, one SQLite file. Auth and Stripe secrets must not land in git or the image.

Quota in the specs is **conversations the user owns** (each conversation is one sales page), not “published only.” Create is the gate.

## Goals / Non-Goals

**Goals:**

- Session-backed Google identity on the existing FastAPI process (no second auth service).
- Enforce owner checks on studio APIs; keep visitor page GET and lead POST public.
- Stripe Customer per user; card via Checkout in setup mode; one Subscription per extra page with a 365-day trial from first publish.
- Claim unowned rows only for `HOMERUN_LEGACY_OWNER_EMAIL`.

**Non-Goals:**

- Email/password, magic links, Apple, or teams / shared pages.
- Hard-coding a dollar amount (Stripe Price ID only).
- Stripe Tax, invoices in the studio UI, or a full billing portal beyond Checkout + optional Customer Portal to update the card.
- Multi-replica session stores or moving off SQLite.
- Charging the first three pages, or charging at card-collect time.
- Changing generate/copywriter behavior.

## Decisions

### 1. Signed session cookie, not a SPA JWT

Use Starlette `SessionMiddleware` (HMAC cookie, `SESSION_SECRET`, `Secure` + `SameSite=Lax` on `homerun.love`). Studio `fetch` calls send `credentials: "include"`. `/api/me` returns the user or `{ user: null }`.

**Rejected:** JWT in `localStorage` (XSS can steal it; more client code). **Rejected:** Auth0/Clerk (second vendor and redirect maze for a single FastAPI app).

### 2. Google OAuth on the studio origin

`GET /auth/google` starts the consent screen. `GET /auth/google/callback` verifies the Google user, upserts `users` on `google_sub`, sets the session, optionally claims legacy rows, redirects to `/`. `POST /auth/logout` clears the session.

Redirect URIs: `http://localhost:8080/auth/google/callback` and `https://homerun.love/auth/google/callback`. If `GOOGLE_CLIENT_ID` / `GOOGLE_CLIENT_SECRET` are missing, the studio refuses to serve authenticated APIs (fail closed on Civo). Tests inject a signed session or a test-only user header.

**Rejected:** GIS one-tap only (harder to test, still need a server session).

### 3. Ownership in SQLite

```
users(
  id, google_sub UNIQUE, email, name, stripe_customer_id,
  created_at, updated_at
)
conversations.user_id  -- nullable for pre-auth rows
page_subscriptions(
  id, user_id, conversation_id UNIQUE, stripe_subscription_id,
  status, trial_end, created_at
)
```

Studio handlers load the session user, then filter `list_conversations(user_id=…)` and require `conversation.user_id == user.id` (else 404). Create sets `user_id`. Visitor lead POST stays slug-based and public.

**Rejected:** Postgres for this slice (one replica already).

### 4. Quota = owned conversations, extra pages get their own Stripe subscription

`FREE_PAGE_LIMIT = 3`. `POST /api/conversations` counts the user’s conversations. If `count >= 3` and the Stripe customer has no default payment method → `402` with `{ code: "payment_required" }` and a Checkout URL from `POST /api/billing/checkout`.

After a card is on file, create succeeds. On **first successful publish** of an extra page (owned count at publish time > 3, in created-at order: the oldest three are free), create a Stripe Subscription on `STRIPE_PAGE_ANNUAL_PRICE_ID` with `trial_end` = now + 365 days and `metadata.conversation_id`. Do not create a subscription for the three free pages.

Webhook `/api/billing/stripe/webhook` (raw body, `STRIPE_WEBHOOK_SECRET`):

- `invoice.payment_failed` → start grace; after 7 days set conversation status `unpublished` and stop serving the slug.
- `invoice.paid` / `customer.subscription.updated` (active) → restore `published` if files still exist.
- Ignore events for unknown subscriptions.

Checkout: `mode=setup` (or setup+redirect) so collecting a card does not invoice. Optional Customer Portal link to replace the card.

**Rejected:** One subscription with `quantity` (trials would share one clock). **Rejected:** Charging immediately and “crediting a year” (spec forbids a charge at card time).

### 5. Public vs reserved routes

Unauthenticated: `/health`, `/auth/*`, `/api/me`, `/api/pages/{slug}/leads`, `/api/billing/stripe/webhook`, `/assets/*`, published `/{slug}/`.

Authenticated: `/api/conversations*`, `/api/billing/checkout`, `/api/billing/status`.

Add reserved first segments: `auth`, `login`, `billing` (plus existing `api`, `assets`, `health`, `static`). Unpublished slugs → 404 like unknown slugs.

### 6. Studio UI

On load, call `/api/me`. If no user, render a single Google button (`/auth/google`). If user, load conversations with cookies. New-page `402` opens Stripe Checkout (same tab). Show “2 / 3 free pages” from `/api/billing/status`. Sign out in the list chrome.

### 7. Legacy rows

`HOMERUN_LEGACY_OWNER_EMAIL` (optional). On that email’s first (or each) login, `UPDATE conversations SET user_id = ? WHERE user_id IS NULL`. Other users never see those rows. Slugs stay public.

## Risks / Trade-offs

- [Google or Stripe misconfig takes down create] → Fail with a clear studio error; health stays up; already-published pages stay public.
- [Webhook delayed → extra page published without a subscription] → Also create the subscription in the publish path; webhook is the source of truth for paid/unpaid.
- [SQLite + webhook + generate] → One replica already; keep webhook handlers short.
- [OAuth on localhost] → Document both redirect URIs; local `.env` holds client secret.
- [User deletes a page later] → Out of scope; if added, cancel that extra page’s subscription. Until then, abandoned extra pages can still bill — note in Open Questions if we add delete.
- [Cookie on HTTP local] → `Secure` only when the public origin is HTTPS.

## Migration Plan

1. Add columns/tables; existing conversations stay `user_id NULL`.
2. Deploy secrets and Google/Stripe dashboard URLs before rolling the image.
3. Set `HOMERUN_LEGACY_OWNER_EMAIL` to the operator who should inherit today’s pages, then sign in once.
4. Rollback: previous image serves the studio without auth again; new tables/columns are unused. Stripe subscriptions already created stay in Stripe and must be canceled by hand if rolling back after extra pages existed.

## Open Questions

- Exact annual amount and currency (set in the Stripe Price; not required to implement).
- Whether we later add conversation delete and subscription cancel (not in this slice).
