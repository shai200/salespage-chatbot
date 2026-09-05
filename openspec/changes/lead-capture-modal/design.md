## Context

See `proposal.md` for motivation. Pages are prerendered static HTML served by the studio at `/{slug}/` (local and Civo). The final CTA is currently an in-page `#offer` / `#cta` jump. Conversations and messages already live in `data/studio.sqlite` (`studio/db.py`). Intake today is offer / audience / CTA only. Civo uses the same process and the `studio-data` PVC for that SQLite file.

## Goals / Non-Goals

**Goals:**

- Same-origin lead POST from the published page into SQLite, keyed by the conversation that owns the slug.
- Modal close: heading, three fields, one button; then redirect or thank-you per specs.
- Next URL is operator-owned, optional, http(s) only.

**Non-Goals:**

- Operator inbox UI or email/Slack notify (API read-by-conversation is enough to prove storage).
- Third-party form hosts, CRM sync, or payments.
- Changing the copy floor, image slots, value stack, or countdown.
- Auto-opening the modal on page load.

## Decisions

### 1. Resolve the conversation from slug, not from a client id

The page embeds `slug` (already public in the URL). `POST /api/pages/{slug}/leads` looks up the published conversation by slug and writes `leads.conversation_id` from that row. The HTML may also include `conversation_id` for debugging; the server ignores it for authorization.

Alternatives: trust a hidden conversation id (spoofable across pages); per-page token (more moving parts than this product needs).

### 2. `leads` table in the existing studio SQLite

```
leads(id, conversation_id, slug, name, email, phone, created_at)
```

`conversations.next_url` is a nullable column (migrate with `ALTER TABLE` like `images_pending`). Same file, same PVC. No new Service.

Alternative: a second SQLite file — rejected; one studio DB is the memory model.

### 3. Modal is prerendered HTML plus a small page script

Match the countdown pattern in `pagekit/prerender.mjs`: static markup in `sections.jsx`, CSS in `tokens.css`, submit/redirect script in the prerendered `index.html`. No extra JS bundle.

Final CTA `href` becomes `#lead` / `button` that opens the dialog. Submit `fetch`es `POST /api/pages/{slug}/leads` with JSON `{ name, email, phone }`. On 2xx, if `nextUrl` is in page data **and** echoed/confirmed by the response, `window.location` assign; else swap the modal body to thank-you text.

Redirect URL used by the browser MUST be the server’s stored `next_url` (returned on success), not a client-editable hidden field, so a visitor cannot rewrite the destination.

### 4. Next URL is intake, not copywriter invention

Extend labeled intake with `Next URL:` / `next_url`. Incomplete brief still only requires offer, audience, CTA. Copywriter JSON may include `leadModal: { heading, buttonLabel, thanks }` in the page language; `next_url` is passed in from conversation state and never taken from the model.

Unsafe schemes (`javascript:`, `data:`) are dropped at intake and again at publish.

### 5. Validation is server-authoritative

Client checks keep the modal from a wasted trip. The studio rejects blank/invalid fields with 400 and no insert. Phone: trimmed, at least 7 digits after stripping formatting characters.

### 6. Operator read path is API-only

`GET /api/conversations/{id}/leads` returns that conversation’s leads (studio session, same as other conversation APIs). No new pane in this change.

## Risks / Trade-offs

- [Public unauthenticated POST] → Bound to a published slug; validate fields; no file upload. Rate limiting can wait unless abuse shows up.
- [PII in SQLite on the PVC] → Same trust boundary as conversation text. Do not log raw phone/email in studio request logs.
- [Static HTML + API] → If `SERVE_SITES` is off and the page is opened as a file, submit fails. Pages are always meant to be served by the studio origin.
- [Existing live pages] → Old `index.html` has no modal until the operator regenerates.

## Migration Plan

- Deploy studio with the new column/table; `db.init()` migrates on boot.
- Old conversations: `next_url` null → thank-you, no redirect, until the operator sets one.
- Rollback: new HTML posts to a missing route (modal error); SQLite extras are unused. Safe to leave the column.

## Open Questions

None that block the specs or task breakdown. Operator lead inbox UI can be a later change.
