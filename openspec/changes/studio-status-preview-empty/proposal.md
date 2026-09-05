## Why

The studio is usable but still reads like a prototype: page state is a raw `draft` or `localhost:3003` string, the preview iframe goes stale after generate, and a new conversation is an empty thread plus a generic placeholder. Operators need to see page state, trust the preview, and know what to type first.

## What Changes

- Show compact status pills on the page list, thread header, and app bar: Draft, Generating, Live, Error. When a live page still uses image placeholders, also show Images pending.
- Replace the preview pane’s bare URL with a toolbar: reload (cache-bust the iframe), copy link, open in a new tab, and a desktop/mobile width toggle.
- First-run / empty conversation: focus the composer and show a short starter (offer, audience, CTA) instead of a blank thread. Empty list copy tells the operator to create a page.
- Load IBM Plex Sans for studio chrome so the declared typeface actually appears.
- App bar shows status (and Open when live) instead of repeating the page title already in the thread header.

## Capabilities

### New Capabilities

- None.

### Modified Capabilities

- `studio-chat`: Operator chrome must present page status, a working preview viewer, and a first-run empty state. Studio remains a compact tool, not a marketing shell.

## Impact

- `web/src/App.jsx`, `web/src/styles.css`, `web/index.html`, and `web/src/api.js`.
- Conversation API may expose `images_pending` (and keep existing `status` / `preview_url`) so pills survive refresh. No new ports or pipeline stages.
- Tests for public conversation shape and, where practical, UI-facing API fields. Generated sales-page design system is unchanged.
