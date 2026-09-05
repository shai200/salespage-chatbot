## 1. Identity and persistence

- [x] 1.1 Add `authlib`, `itsdangerous`, and `stripe` dependencies and verify `pip install -e ".[dev]"` succeeds
- [x] 1.2 Add `users` and `page_subscriptions` tables plus nullable `conversations.user_id` in `studio/db.py`, with upsert-by-`google_sub`, list/create scoped by `user_id`, and verify a user round-trip plus two users’ conversations do not leak
- [x] 1.3 Reserve first-path segments `auth`, `login`, and `billing` and verify an offer that slugifies to those names gets a different slug

## 2. Google session

- [x] 2.1 Add session middleware, `GET /api/me`, `GET /auth/google`, `GET /auth/google/callback`, and `POST /auth/logout`, and verify a mocked first Google consent creates one user and a second consent reuses that user
- [x] 2.2 Require a session on conversation and conversation-lead APIs (401 if anonymous, 404 if another user’s id) and verify `/health`, published `GET /{slug}/`, and `POST /api/pages/{slug}/leads` stay public
- [x] 2.3 On sign-in, attach `user_id IS NULL` conversations only when the Google email matches `HOMERUN_LEGACY_OWNER_EMAIL`, and verify any other user starts with an empty list while those slugs stay served
- [x] 2.4 Gate the studio UI: Google sign-in when `/api/me` has no user, three-pane studio plus sign-out when it does, `credentials: "include"` on studio fetches, and verify an anonymous load does not list conversations

## 3. Billing and publish

- [x] 3.1 Add `GET /api/billing/status` and `POST /api/billing/checkout` (Stripe Checkout setup mode, no charge) and verify status reports free pages used and whether a card is required
- [x] 3.2 Block `POST /api/conversations` at three owned pages without a payment method (`402` + `payment_required` + checkout URL) and verify the fourth create succeeds after a mocked card-on-file
- [x] 3.3 On first publish of an extra page (oldest three owned conversations stay free), create one Stripe Subscription with a 365-day trial and `STRIPE_PAGE_ANNUAL_PRICE_ID`, and verify free pages never get a subscription
- [x] 3.4 Handle `POST /api/billing/stripe/webhook`: unpaid extra invoice starts 7-day grace then unpublish (404 on that slug); paid/active restores the same files; free pages stay served — verify with fixture events
- [x] 3.5 On a 402 from create, send the operator through Stripe Checkout and show free-page usage from billing status, and verify the UI copy says a card is required

## 4. Deploy and coverage

- [x] 4.1 Document Google/Stripe env vars and redirect URLs in the README (and Civo secret/config notes) and verify they match `studio/config.py` names
- [x] 4.2 Add pytest coverage for anonymous 401, cross-user 404, quota 402, legacy claim, and webhook unpublish/restore, and verify `pytest` passes
