## 1. Persistence and intake

- [ ] 1.1 Add `leads` table and nullable `conversations.next_url` (create + `ALTER TABLE` migrate) in `studio/db.py`, with insert/list-by-conversation helpers, and verify a round-trip test stores a lead under a conversation id
- [ ] 1.2 Parse optional `Next URL:` in intake, persist http(s) only on the conversation, and verify `javascript:` is dropped while offer/audience/CTA completeness is unchanged
- [ ] 1.3 Keep `next_url` across copy-only follow-ups and verify a headline-only rebuild still publishes the same next URL

## 2. Public and operator APIs

- [ ] 2.1 Add `POST /api/pages/{slug}/leads` that resolves the published conversation by slug, validates name/email/phone, inserts the lead, and returns the stored `next_url` (or null), and verify unknown slugs and missing phone do not write a row
- [ ] 2.2 Add `GET /api/conversations/{id}/leads` and verify it returns only that conversation’s leads
- [ ] 2.3 Confirm two published pages isolate leads (POST each slug, GET each conversation) and that a client-supplied conversation id cannot attach a lead to another conversation

## 3. Page kit and generate

- [ ] 3.1 Add the lead modal section (heading, three inputs, button, hidden-by-default) and bind the final CTA to open it, and verify prerendered sample HTML includes the modal and does not show it on first paint
- [ ] 3.2 Add prerender script that POSTs to `/api/pages/{slug}/leads` and redirects using the response `next_url` or shows thank-you, and verify a generate with a next URL includes that script and slug
- [ ] 3.3 Pass conversation-owned `next_url` and copywriter `leadModal` text through `page_data_from_copy` (never from model-invented URLs) and verify Hebrew pages get Hebrew modal labels
- [ ] 3.4 Style the modal to the editorial kit (white, dark text, one accent) and verify it matches existing page tokens

## 4. Coverage and docs

- [ ] 4.1 Add pytest coverage for persist-by-conversation, validation 400s, redirect vs thank-you payloads, and unsafe next URL, and verify `pytest` passes
- [ ] 4.2 Document Next URL intake and lead storage in the README and verify the documented `POST /api/pages/{slug}/leads` shape matches the implementation
