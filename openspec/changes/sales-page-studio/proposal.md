## Why

The repo is a visitor-facing regex chatbot on a static sales page. The product we want is different: a **local studio chatbot that builds sales pages**. That needs a documented operator experience, a generation pipeline, and local preview/publish — none of which the current MVP specifies.

## What Changes

- Replace the product intent: operator studio (build pages) instead of a visitor FAQ bot on one hardcoded offer.
- Add a Python studio app on `localhost:8080` (FastAPI + LangGraph) with a **React** three-pane UI.
- Each conversation is one sales page; SQLite stores conversations, messages, and graph checkpoints.
- Orchestrate copy, visuals, page engineering, and local publish via **LangGraph** and **OpenRouter** (not local models).
- Generate pages as **React**, prerendered to static HTML, using an editorial design system (white background, black body text, display headlines with accent color).
- **Publisher** runs each page with Node on `localhost:3000`, `3001`, … (not GitHub Pages or Kubernetes).
- Chat messages include a clickable preview URL that opens in a **new tab**, in addition to the in-app iframe.
- **BREAKING** relative to ADR 0001 / the current Node-only regex bot: UI stack, runtime split, dependencies, and chatbot role all change. The existing prototype remains until this change is applied; it is not the target architecture.

## Capabilities

### New Capabilities

- `studio-chat`: Operator chatbot UI and conversation model (three-pane React shell, one conversation per sales page, streaming chat, preview iframe, new-tab page URL).
- `generation-pipeline`: LangGraph orchestration (copywriter, visual, page engineer, publisher) over OpenRouter, producing React sales pages that follow the editorial design system.
- `local-hosting`: Per-page site folders, Node preview processes, and port assignment starting at 3000.

### Modified Capabilities

- None. `openspec/specs/` has no existing capabilities.

## Impact

- New Python service (FastAPI, LangGraph, OpenRouter client, SQLite) and a React studio frontend served on port 8080.
- Generated sites under `sites/<slug>/`, served by Node on 3000+.
- `.env` holds `OPENROUTER_API_KEY` (already gitignored).
- Current `src/server.js` / `public/` regex chatbot is superseded as the product; keep or retire during apply.
- ADR 0001 is superseded by this change’s design. The old visitor-bot SDD lives in `docs/archive/prototype-sdd.md`. `docs/openspec/` was removed (it was an OpenAPI file for the prototype, not OpenSpec).
