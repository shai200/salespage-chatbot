## Why

Generated pages ask for the sale but have nowhere to put the yes. The common pattern is capture the buyer (name, email, phone) on the page, then send them to a booking or checkout URL. Without that, the CTA is a dead scroll and Homerun never records a lead.

## What Changes

- Every published page opens a **popup modal** when the visitor clicks the final ask: heading text, name / email / phone, one submit button.
- Submit **stores the lead in SQLite** on the studio database, keyed by the **conversation id** that built the page (plus slug and timestamps).
- After a successful capture, the page **redirects to a next URL** when the operator set one. That is the default pattern. If no next URL is set, the visitor stays on the page with a short thank-you state.
- Intake and copy gain an optional **next URL** (booking, Stripe, Calendar, WhatsApp, etc.). The copywriter writes the modal heading; it does not invent a destination.
- Studio API accepts the public lead POST from the same origin that serves `/{slug}/` (local and Civo).

## Capabilities

### New Capabilities

- `lead-capture`: Visitor modal, validation, persist-under-conversation, optional redirect, public POST on the studio host.

### Modified Capabilities

- `generation-pipeline`: Final CTA opens the lead modal instead of scrolling; page data includes conversation id, modal copy, and next URL; prerender includes the modal script.
- `studio-chat`: Operator can supply a next URL in the brief or a follow-up; that URL is stored on the conversation and published onto the page.

## Impact

- `studio/db.py` — `leads` table; optional `next_url` on `conversations`.
- `studio/app.py` — public `POST` for leads; reserved path stays under `/api`.
- `studio/intake.py`, `studio/llm.py`, `studio/graph.py`, `studio/pages.py` — next URL + modal copy through generate.
- `pagekit/src/sections.jsx`, `tokens.css`, `prerender.mjs` — modal markup, styles, submit + redirect script.
- Same SQLite file and Civo `studio-data` PVC; no new Service.
- Tests for persist-by-conversation, validation, redirect vs stay, Hebrew modal labels.
