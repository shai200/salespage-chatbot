## Context

See `proposal.md` for motivation. Current chrome (`web/src/App.jsx`) shows `item.preview_url || item.status` and `localhost:${port}` as muted text. Preview is an iframe whose `src` is the stable preview URL, so republish often looks unchanged. New conversations get an empty thread; `index.html` never loads IBM Plex Sans even though CSS names it. Conversation API already returns `status`, `port`, and `preview_url`. `images_pending` exists on graph state and `page.json` but is not on the conversation row or `_public_conversation`.

## Goals / Non-Goals

**Goals:**

- Derive pills from conversation fields plus in-flight client progress.
- Persist `images_pending` so Images pending survives refresh.
- Cache-bust iframe reloads without changing the published port/URL.
- First-run starter is chrome copy, not a fake assistant message in SQLite.

**Non-Goals:**

- Delete/rename, search, thumbnails, elapsed-time on stages.
- Conversation-scoped concurrent generates (busy may stay window-global).
- Mobile pane tabs, Enter-to-send, edit chips.
- Changing generated page typography or the LangGraph pipeline.

## Decisions

### 1. Persist `images_pending` on the conversation

Add an `images_pending` column (integer 0/1, default 1 for new drafts is unnecessary — default 0 until a visual stage runs). `visual_node` already knows the flag; write it via `db.update_conversation`. Expose it on `_public_conversation`.

**Alternative:** Read `sites/<slug>/page.json` on every list — extra I/O and fails if the file is missing. **Alternative:** Encode pending in `status` (`published_pending`) — collides with draft/published/error.

### 2. Generating is client-only

Do not write `status=generating` to SQLite. The list/header use Generating while `busy` is true for the active conversation; after the stream ends, fall back to Live/Draft/Error from the refreshed row.

**Alternative:** Persist generating — leftover Generating after a killed tab is worse than a brief client-only pill.

### 3. Preview reload via cache-bust query, keep stored URL clean

Keep `preview_url` as `http://localhost:<port>/`. Iframe `src` is `${previewUrl}?v=${previewNonce}`. Reload and a successful generate increment the nonce. Copy/Open use the clean URL.

**Alternative:** `iframe.contentWindow.location.reload()` — blocked or ignored across localhost ports / stale documents. Query param is reliable.

### 4. Preview width is CSS, not a second server

Desktop: iframe `width: 100%`. Mobile: max-width ~390px, centered in the pane. Toggle is local React state, not persisted.

**Alternative:** Serve a mobile user-agent — out of scope; pages are already responsive enough to judge at a narrow width.

### 5. Starter is an empty-state panel, not a message

When `messages.length === 0`, render a non-bubble starter in the thread (offer / audience / CTA). Do not insert a row in `messages`. Focus the textarea on new conversation and when selecting an empty thread.

**Alternative:** Seed a system message — pollutes history and RTL/markdown paths.

### 6. Typeface via Google Fonts stylesheet on the studio HTML only

Add the IBM Plex Sans link in `web/index.html`. Page kit keeps Fraunces + Source Sans.

**Alternative:** Self-host woff2 — nicer offline, more files; local studio already needs the network for models.

## Risks / Trade-offs

- [Clipboard may fail without permission] → Copy shows a brief failure in the toolbar; do not throw into the thread.
- [Existing DBs lack `images_pending`] → `init()` runs `ALTER TABLE` if the column is missing; older live rows default 0 until the next visual stage.
- [Cache-bust may stack with page-relative assets] → Use `?v=` only on the iframe document URL; site assets stay relative.
- [App bar Open vs toolbar Open] → Same URL, two places; keep both so the bar stays useful when the preview pane is scrolled/stacked.

## Migration Plan

Rebuild `web/dist`. Restart the studio process so Python serves the new conversation field. Existing conversations stay Draft/Live/Error; Images pending appears after the next generate that runs the visual node.

## Open Questions

None that affect spec or task breakdown.
