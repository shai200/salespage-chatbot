## Context

See `proposal.md`. Studio thread pane is a column flex: header, `.thread`, `.composer`. Observed in `web/src/styles.css`: `.thread` scrolls but does not grow (`flex: 1` is missing), so the composer sits under the messages near the top. Generated HTML from `pagekit/prerender.mjs` is always `<html lang="en">` with no `dir`. Page kit CSS is LTR.

## Goals / Non-Goals

**Goals:**

- Composer pinned to the bottom of the thread pane at all message lengths.
- Send is optimistic: the user bubble appears and the composer clears before the pipeline returns.
- Hebrew generated pages get `lang="he"` `dir="rtl"` and RTL-friendly section alignment.
- Detect Hebrew without a separate language settings UI.

**Non-Goals:**

- Full i18n for every language (Arabic, etc. can follow the same `dir` pattern later).
- RTL studio chrome or Hebrew UI strings in the operator tool.
- Changing the editorial token colors.

## Decisions

### 1. Pin composer with flex, not by reordering DOM

DOM order is already header → thread → composer (correct). Give `.thread` `flex: 1` and `min-height: 0` so it fills leftover pane height and the composer stays at the bottom. Do not move the form above the messages.

**Alternative:** `position: sticky/fixed` on the composer (unnecessary if the pane is a flex column).

### 2. Hebrew detection

Set page language to Hebrew when either:

- intake/copy metadata says `language: he`, or
- a substantial share of generated text contains Hebrew letters (`\u0590-\u05FF`).

Prefer explicit language from the copywriter/intake when present. Persist `language` and `dir` on `page.json` so prerender does not guess twice.

### 3. Prerender root attributes

`pagekit/prerender.mjs` MUST take `lang` and `dir` from page data instead of hardcoding `en`. Example: `<html lang="he" dir="rtl">`. CSS: for `[dir="rtl"]` (or `html[dir="rtl"] .page`), use logical properties or `text-align: start` so display headlines and body align to the start edge. Grids can stay; do not `direction: ltr` on the whole page.

**Alternative:** CSS `dir` only on `<main>` — weaker for the document and accessibility; set it on `<html>`.

### 4. Optimistic send

On submit, append a local user message to the thread, clear the textarea, and keep a pending assistant state (“Working”) until `/messages` returns. Then replace local messages with the persisted thread. Do not leave the typed text in the composer while generate runs.

**Alternative:** disable the composer until generate finishes (rejected: looks stuck; the box must clear).

### 5. Studio vs page

Studio `html` stays LTR. Iframe content is a separate document, so Hebrew RTL in preview does not flip the chrome.

## Risks / Trade-offs

- [Hebrew mixed with English brand names] → RTL with Unicode bidi on the document is enough; do not force every Latin word to LTR spans unless we see breakage.
- [False positive Hebrew detection on a few letters] → Require a threshold (e.g. several Hebrew letters in headline or body), or explicit `he` from the model JSON.
- [Composer flex vs mobile stacked panes] → Keep `flex: 1` on `.thread` in the stacked layout too so the input stays at the bottom of the middle pane.

## Migration Plan

Ship CSS + prerender together. Rebuild existing Hebrew sites by sending a follow-up in that conversation (or republish); old `index.html` stays LTR until rebuilt.

## Open Questions

- Default display font for Hebrew (Fraunces may lack Hebrew glyphs). If missing, fall back to a system Hebrew-capable family in RTL pages only — does not change the RTL requirement.
