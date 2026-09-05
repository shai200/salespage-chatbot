## 1. Conversation status API

- [x] 1.1 Add `images_pending` to SQLite (`init` create + migrate) and `db.update_conversation`, and verify existing tests still pass
- [x] 1.2 Persist `images_pending` from the visual stage and expose it on `_public_conversation`, and verify a generate/list response includes the boolean

## 2. Status pills and app bar

- [x] 2.1 Derive Draft / Generating / Live / Error / Images pending pills for list, thread header, and app bar, and verify raw `draft` / `localhost:port` are no longer the only status
- [x] 2.2 Replace the app-bar title with status plus Open when live, and verify the page title is not repeated in the bar

## 3. Preview toolbar

- [x] 3.1 Add reload (cache-bust nonce), copy link, open in new tab, and desktop/mobile width toggle, and verify no-page state disables reload/copy/open and does not load an iframe
- [x] 3.2 Increment the iframe nonce after a successful generate and on Reload, and verify Copy uses the clean preview URL

## 4. Empty states and typeface

- [x] 4.1 Replace the empty list copy and add a non-message offer/audience/CTA starter that focuses the composer on new/empty conversations, and verify no starter row is stored in `messages`
- [x] 4.2 Load IBM Plex Sans in studio `index.html` and rebuild `web/dist`, and verify the built HTML includes the font stylesheet

## 5. Tests and studio reload

- [x] 5.1 Add or extend pytest coverage for `images_pending` on the conversation payload, and verify `pytest` passes
- [x] 5.2 Restart the studio on 8080 so the new API and `web/dist` are served, and verify `/` and `/api/conversations` respond
