## Why

Three UI bugs make the studio and generated pages harder to use: the chat composer sits at the top of the thread instead of the bottom, sending a message leaves the text in the box until generate finishes, and Hebrew sales pages are prerendered as LTR English (`lang="en"`), so Hebrew copy does not read right-to-left.

## What Changes

- Pin the studio thread composer to the **bottom** of the center pane; messages scroll in the space above it.
- On send, show the operator message in the thread immediately and clear the composer (do not wait for generate to finish).
- When a generated sales page is in **Hebrew**, emit `dir="rtl"` and `lang="he"` (and matching layout) so the page reads as a Hebrew landing page.
- Non-Hebrew pages stay LTR. The studio chrome stays LTR even when the preview is RTL.

## Capabilities

### New Capabilities

- None.

### Modified Capabilities

- `studio-chat`: Chat composer MUST be at the bottom of the thread pane. Sending MUST append the user message to the thread and clear the input immediately.
- `generation-pipeline`: Hebrew-language sales pages MUST be RTL.

## Impact

- Studio: `web/src/styles.css` (thread pane flex) and `web/src/App.jsx` (send waits for `/messages` before clearing the draft). Observed: `.thread` is not `flex: 1`, so `.composer` sits under a short message list near the top of the pane.
- Generated pages: `pagekit/prerender.mjs` hardcodes `<html lang="en">` with no `dir`; `pagekit/src/tokens.css` is LTR-only; page data from `studio/pages.py` / copy stage must carry a language (or Hebrew-script detection) into prerender.
