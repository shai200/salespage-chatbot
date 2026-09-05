# Homerun Sales Page Builder

A **local studio chatbot that writes sales pages**. The operator talks to the studio; each conversation becomes one static sales page at `http://localhost:8080/<slug>/`.

This is an **OpenSpec** project. Orchestration is **LangGraph** (LangChain chat client → OpenRouter). Memory is **SQLite** plus files on disk.

The older visitor FAQ prototype (`src/server.js`) is still runnable. The product is the studio on port 8080.

## Run the studio

Requires Python 3.9+, Node.js, and an [OpenRouter](https://openrouter.ai/) API key.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

cd web && npm install && npm run build && cd ..
cd pagekit && npm install && cd ..

# .env is gitignored — do not commit it
# OPENROUTER_API_KEY=sk-or-...
# optional: OPENROUTER_MODEL=openai/gpt-4o-mini
# optional: OPENROUTER_IMAGE_MODEL=meta/muse-image

python -m studio
```

Open `http://localhost:8080`. After publish, the thread includes `http://localhost:8080/<slug>/` (opens in a new tab) and the right pane loads the same URL.

- a page with slug `northline-briefings-85fbe9b4` → `http://localhost:8080/northline-briefings-85fbe9b4/`
- rebuilding that conversation keeps the same path
- `/`, `/api`, `/assets`, and `/health` stay the studio
- Site files: `sites/<slug>/`. SQLite: `data/studio.sqlite`

If `OPENROUTER_API_KEY` is missing, generation fails in the thread and nothing is published.

```bash
source .venv/bin/activate
pytest
```

## How we work: OpenSpec

Product work goes through an OpenSpec **change** (`openspec/changes/<name>/`):

| Artifact | Role |
|---|---|
| `proposal.md` | Why and what |
| `specs/<capability>/spec.md` | Observable requirements (SHALL / WHEN / THEN) |
| `design.md` | How and why of technical choices |
| `tasks.md` | Implementation checklist |

Cursor skills under `.cursor/skills/openspec-*` drive propose → apply → archive. Schema: `spec-driven` (`openspec/config.yaml`).

**Capabilities:** `studio-chat`, `generation-pipeline`, `local-hosting`, `static-hosting`.

| Change | Status | What it captured |
|---|---|---|
| `sales-page-studio` | Implemented | Studio, LangGraph pipeline, SQLite, React pages, local preview |
| `fix-composer-and-hebrew-rtl` | Implemented | Composer pin, optimistic send, Hebrew RTL, Markdown, pipeline progress |
| `studio-status-preview-empty` | Implemented | Status pills, preview toolbar, first-run empty state, IBM Plex |
| `deploy-homerun-civo` | In progress | Path publish, Docker rehearsal; Civo apply not done |

Canonical specs are **not** archived into `openspec/specs/` yet. Until `/opsx-archive` + sync, the change folders are the source of truth. [ADR 0001](docs/adr/0001-static-node-chatbot.md) describes the old Node regex prototype and is **superseded**.

## Architecture

```
Operator browser
      |
      v
http://localhost:8080          studio (FastAPI)
 /  /api  /assets  /health  -->  React SPA (web/dist)
 /<slug>/               -->  static files from sites/<slug>/
      |
      +-- LangGraph (thread_id = conversation id)
      |     intake -> copywriter -> visual -> page_engineer -> publisher
      +-- SQLite  data/studio.sqlite
      |     conversations, messages, LangGraph checkpoints
      +-- OpenRouter
            chat completions (copy / intake)
            /images (hero PNG)
```

One process, one origin. Reserved paths stay the studio; every other first segment is a published page (or 404).

### Why these choices

**Operator studio, not a visitor bot.** `src/server.js` + `public/` answered FAQs on one hardcoded page. The product is the tool that *builds* pages.

**Python FastAPI + LangGraph for orchestration.** The pipeline is a durable graph (state, checkpoints, conditional edges). LangGraph is the runtime; LangChain’s OpenAI-compatible client talks to OpenRouter for chat. CrewAI was rejected: weaker durable thread state for “one conversation = one page.”

**React for two different UIs.** Studio: compact Vite SPA (pages / thread / preview), tool chrome, IBM Plex. Generated pages: separate React tree in `pagekit/`, prerendered to static HTML, editorial type (Fraunces + Source Sans).

**Remote models, local everything else.** `OPENROUTER_API_KEY` in gitignored `.env`. Defaults: `openai/gpt-4o-mini` (chat), `meta/muse-image` (hero). No Ollama, no in-cluster GPU.

**SQLite as the only database.** One machine, one operator. Conversations, messages, and LangGraph checkpoints share `data/studio.sqlite`. Site bytes stay under `sites/<slug>/`.

**Path publish, not a process per page.** Early design spawned Node on `3000, 3001, …`. Publish is now: write `sites/.staging/<slug>/`, replace `sites/<slug>/`, serve `{origin}/{slug}/`. Same contract locally and later on Civo (`https://homerun.love/<slug>/`).

### LangGraph pipeline

`studio/graph.py`. `conversation_id` is the LangGraph `thread_id`. Follow-ups resume the same checkpoint (copy, visuals, slug).

```
START --> intake --> copywriter --> visual --> page_engineer --> publisher --> END
              |            |
              v            v
             END          END
         (missing brief   (copy/key error)
          or error)
```

| Node | Job |
|---|---|
| **intake** | Merge offer, audience, CTA. Incomplete brief asks for what’s missing and stops. |
| **copywriter** | OpenRouter chat → JSON sales copy (headline, sections, CTA, language). |
| **visual** | OpenRouter `/images` → `hero.png`. Failure keeps placeholders (`images_pending`). Copy-only edits skip this node. |
| **page_engineer** | Write React + `page.json`, prerender (`pagekit/prerender.mjs`). Hebrew gets `lang="he"` `dir="rtl"`. |
| **publisher** | Promote staging → live `sites/<slug>/`, return `{origin}/{slug}/`. No Node spawn. |

The UI streams stage labels over SSE so the thread shows “Writing the page copy” instead of a blank wait.

Copy-only follow-ups use word-boundary matching. Image words never skip the visual node.

### Memory

**SQLite** (`data/studio.sqlite`, gitignored):

- `conversations` — id, title, slug, site_path, status (`draft` / `built` / `published` / `error`), offer / audience / cta, `images_pending`. `port` / `pid` are leftover columns; pages no longer bind 3000+.
- `messages` — user and assistant rows. The first-run starter is chrome, not a stored message.
- LangGraph `SqliteSaver` checkpoints — same file, keyed by conversation id.

**Filesystem** (`sites/<slug>/`, gitignored): prerendered `index.html`, `hero.png`, `page.json`, React source. Staging: `sites/.staging/<slug>/` until promote.

Restart restores the list and thread from SQLite. Live HTML is already on disk.

### Studio UI

`web/` — Vite + React, built into `web/dist`, served by FastAPI.

- App bar: Homerun + status pills + Open
- List: Draft / Generating / Live / Error / Images pending
- Thread: Markdown, Hebrew RTL per bubble, optimistic send, pipeline steps
- Preview: iframe with reload, copy link, open, desktop/mobile width

Studio chrome stays LTR. Hebrew RTL is only on the generated page.

### Generated page design

White background, `#0a0a0a` text, one accent. Sections only: Hero, Problem, Benefits, Proof, Offer, FAQ, Final CTA, Footer. Tokens in `pagekit/`.

### Hosting: local now, Civo next

**Local (`python -m studio`).** FastAPI on `127.0.0.1:8080`. Serves the SPA and `sites/<slug>/`. Unknown slugs are 404.

**Docker rehearsal.** `Dockerfile` + `docker-compose.yml` + `deploy/nginx-edge.conf`: studio writes a `sites` volume; nginx serves reserved paths to the studio and `/<slug>/` from the volume. Host port **8081** so it does not collide with a studio on 8080.

**Civo (specified, not applied).** Same volume contract: studio writes `sites`, pages pod reads them, Ingress splits reserved paths vs slugs. TLS for `homerun.love`. `civo-love-kubeconfig` is gitignored. The write *is* the deploy — no `kubectl cp`.

`PUBLIC_BASE_URL` overrides link origin (`https://homerun.love` in cluster). Unset, links are `http://localhost:8080/<slug>/`.

### Out of scope

- Auth, multi-tenant SaaS, local LLMs
- Visitor chat on the generated page
- Per-page Kubernetes pods or sequential preview ports
- Archiving OpenSpec deltas into `openspec/specs/`
- Applying cluster manifests

### Code map

| Path | What |
|---|---|
| `studio/` | FastAPI, graph, DB, publisher, page writer, OpenRouter client |
| `web/` | Studio SPA |
| `pagekit/` | Sales-page kit + prerender |
| `openspec/changes/` | Proposals, specs, designs, tasks |
| `docs/adr/0001-static-node-chatbot.md` | Superseded prototype ADR |
| `docs/archive/prototype-sdd.md` | Archived visitor-bot SDD |

## Old prototype (port 3000)

```bash
npm start
```

Then open `http://localhost:3000`. Studio pages no longer use 3000; they live under `http://localhost:8080/<slug>/`.

```bash
npm test
```
