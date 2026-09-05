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
# SESSION_SECRET=long-random-string
# GOOGLE_CLIENT_ID=...
# GOOGLE_CLIENT_SECRET=...
# STRIPE_SECRET_KEY=sk_test_...
# STRIPE_WEBHOOK_SECRET=whsec_...
# STRIPE_PAGE_ANNUAL_PRICE_ID=price_...
# optional: HOMERUN_LEGACY_OWNER_EMAIL=you@example.com
# optional: OPENROUTER_MODEL=openai/gpt-4o-mini
# optional: OPENROUTER_IMAGE_MODEL=meta/muse-image
# optional: OPENROUTER_EMBED_MODEL=google/gemini-embedding-2
# optional: COPY_MIN_WORDS=2100

python -m studio
```

Open `http://localhost:8080` and sign in with Google. After publish, the thread includes `http://localhost:8080/<slug>/` (opens in a new tab) and the right pane loads the same URL.

Google OAuth redirect URIs: `http://localhost:8080/auth/google/callback` and `https://homerun.love/auth/google/callback`. Stripe webhook: `https://homerun.love/api/billing/stripe/webhook`. The first three pages per user are free. A fourth page asks for a card (Checkout setup mode, no charge). Each extra page starts a 12-month trial, then the Stripe Price `STRIPE_PAGE_ANNUAL_PRICE_ID` bills annually.

- a page with slug `northline-briefings-85fbe9b4` → `http://localhost:8080/northline-briefings-85fbe9b4/`
- rebuilding that conversation keeps the same path
- `/`, `/api`, `/assets`, `/auth`, `/login`, `/billing`, and `/health` stay the studio
- Site files: `sites/<slug>/`. SQLite: `data/studio.sqlite`

If `OPENROUTER_API_KEY` is missing, generation fails in the thread and nothing is published.

Optional in the brief: `Next URL: https://cal.example/book`. After a visitor submits name, email, and phone in the page modal, the studio stores the lead and sends them there. Without a next URL they stay on the page with a thank-you.

```http
POST /api/pages/{slug}/leads
Content-Type: application/json

{"name":"Ada","email":"ada@example.com","phone":"+1 202 555 0147"}
```

Success returns `{ "ok": true, "id": "…", "conversation_id": "…", "next_url": "https://…" or null }`. The page redirects only using that `next_url`. `GET /api/conversations/{id}/leads` lists leads for that conversation. `javascript:` and other non-http(s) destinations are dropped.

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

**Capabilities:** `studio-chat`, `generation-pipeline`, `local-hosting`, `static-hosting`, `copy-guides`.

| Change | Status | What it captured |
|---|---|---|
| `sales-page-studio` | Implemented | Studio, LangGraph pipeline, SQLite, React pages, local preview |
| `fix-composer-and-hebrew-rtl` | Implemented | Composer pin, optimistic send, Hebrew RTL, Markdown, pipeline progress |
| `studio-status-preview-empty` | Implemented | Status pills, preview toolbar, first-run empty state, IBM Plex |
| `deploy-homerun-civo` | In progress | Path publish on Civo at `homerun.love/<slug>/`; cluster apply not done |
| `copywriter-rag` | Specified | PDF copy guides → sqlite-vec; craft notes at copy time (not applied) |

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
      +-- SQLite  data/rag.sqlite   (specified)
      |     copy guides, chunks, sqlite-vec KNN
      +-- OpenRouter
            chat completions (copy / intake)
            embeddings (guide ingest / retrieve)
            /images (hero PNG)
```

One process, one origin. Reserved paths stay the studio; every other first segment is a published page (or 404).

### Why these choices

**Operator studio, not a visitor bot.** `src/server.js` + `public/` answered FAQs on one hardcoded page. The product is the tool that *builds* pages.

**Python FastAPI + LangGraph for orchestration.** The pipeline is a durable graph (state, checkpoints, conditional edges). LangGraph is the runtime; LangChain’s OpenAI-compatible client talks to OpenRouter for chat. CrewAI was rejected: weaker durable thread state for “one conversation = one page.”

**React for two different UIs.** Studio: compact Vite SPA (pages / thread / preview), tool chrome, IBM Plex. Generated pages: separate React tree in `pagekit/`, prerendered to static HTML, editorial type (Fraunces + Source Sans).

**Remote models, local everything else.** `OPENROUTER_API_KEY` in gitignored `.env`. Defaults: `openai/gpt-4o-mini` (chat), `meta/muse-image` (hero). No Ollama, no in-cluster GPU.

**SQLite as the only database.** Conversations are owned by a Google user (`users` + `conversations.user_id`). Messages, leads, page subscriptions, and LangGraph checkpoints stay in `data/studio.sqlite`. Copywriting-guide RAG uses a **second** file, `data/rag.sqlite`, with **sqlite-vec** for KNN — wipe and re-ingest without touching threads. Postgres / pgvector are out of scope. Site bytes stay under `sites/<slug>/`. Operator PDFs live in `guides/` (gitignored); ingest is a command, not a chat turn.

**Path publish, not a process per page.** Early design spawned Node on `3000, 3001, …`. Publish is now: write `sites/.staging/<slug>/`, replace `sites/<slug>/`, serve `{origin}/{slug}/`. Same contract locally and on Civo (`https://homerun.love/<slug>/`).

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
| **intake** | Merge offer, audience, CTA, and optional Next URL (`https://…` only). Incomplete brief still only requires the first three. |
| **copywriter** | System prompt (craft rules, thin vs dense examples, `{COPY_MIN_WORDS}` minimum — default 2100). OpenRouter chat → JSON sales copy. Guide RAG (specified) injects notes when the index exists. |
| **visual** | OpenRouter `/images` → `hero.png`, `dream.png` (won outcome), `risk.png` (if they wait), `value.png` (easy start, small price vs the win). Failure keeps placeholders (`images_pending`). Copy-only edits skip this node. |
| **page_engineer** | Write React + `page.json`, prerender (`pagekit/prerender.mjs`). Hebrew gets `lang="he"` `dir="rtl"`. Close includes a value stack, a 24-hour discount countdown, and a lead modal on the final ask. |
| **publisher** | Promote staging → live `sites/<slug>/`, return `{origin}/{slug}/`. No Node spawn. |

The UI streams stage labels over SSE so the thread shows “Writing the page copy” instead of a blank wait.

Follow-ups keep the existing images unless the operator asks for images, photos, visuals, or placeholders. Those words always rerun the visual node. Old PNGs are overwritten in place on the same slug; they are not archived.

### Memory

**SQLite** (`data/studio.sqlite`, gitignored):

- `users` — Google subject, email, name, Stripe customer id, payment-method flag.
- `conversations` — id, `user_id`, title, slug, site_path, status (`draft` / `built` / `published` / `unpublished` / `error`), offer / audience / cta, optional `next_url`, `images_pending`. `port` / `pid` are leftover columns; pages no longer bind 3000+.
- `messages` — user and assistant rows. The first-run starter is chrome, not a stored message.
- `leads` — visitor name, email, phone, slug, created_at, keyed by `conversation_id`.
- `page_subscriptions` — one Stripe subscription per extra page (trial + grace).
- LangGraph `SqliteSaver` checkpoints — same file, keyed by conversation id.

**RAG SQLite** (`data/rag.sqlite`, gitignored, specified): file registry, chunk text, sqlite-vec embeddings. Same `studio-data` PVC on Civo. No extra Service. Load sqlite-vec only on this connection.

**Filesystem** (`sites/<slug>/`, gitignored): prerendered `index.html`, page PNGs (`hero.png`, `dream.png`, `risk.png`, `value.png`), `page.json`, React source. Staging: `sites/.staging/<slug>/` until promote.

**Guides** (`guides/*.pdf`, gitignored): operator copywriting PDFs. Ingest hashes, chunks (~500–800 tokens), embeds via OpenRouter (`OPENROUTER_EMBED_MODEL`, default `google/gemini-embedding-2`). Unchanged files skip re-embed. Retrieval failure never blocks generate.

Restart restores the list and thread from SQLite. Live HTML is already on disk. Re-ingest rebuilds `rag.sqlite` only.

### Studio UI

`web/` — Vite + React, built into `web/dist`, served by FastAPI.

- Sign-in with Google when there is no session; Sign out in the page list
- App bar: Homerun + status pills + Open
- List: Draft / Generating / Live / Error / Images pending, plus free-page usage
- Thread: Markdown, Hebrew RTL per bubble, optimistic send, pipeline steps
- Preview: iframe with reload, copy link, open, desktop/mobile width

Studio chrome stays LTR. Hebrew RTL is only on the generated page.

### Generated page design

White background, `#0a0a0a` text, one accent. Sections only: Hero, Problem, Benefits, Proof, Offer, FAQ, Final CTA, Footer. Tokens in `pagekit/`.

### Hosting: local now, Civo next

**Local (`python -m studio`).** FastAPI on `127.0.0.1:8080`. Serves the SPA and `sites/<slug>/`. Unknown slugs are 404.

**Docker rehearsal.** `Dockerfile` + `docker-compose.yml` + `deploy/nginx-edge.conf`: studio writes a `sites` volume; nginx serves reserved paths to the studio and `/<slug>/` from the volume. Host port **8081** so it does not collide with a studio on 8080.

**Civo.** Same write: studio promotes onto the `studio-sites` PVC (`/app/sites/<slug>/`). Ingress sends `homerun.love/` to that Service. FastAPI serves reserved paths as the studio and `/<slug>/` as pages (`SERVE_SITES=true`). `PUBLIC_BASE_URL=https://homerun.love`. TLS for that host. `civo-love-kubeconfig` is gitignored. `./deploy/deploy.sh` also copies this machine’s `data/studio.sqlite` (and WAL) plus `sites/` onto the PVCs so local conversations and pages match the server. `--skip-sync` leaves cluster data alone.

Copying HTML to a cheap VPS is later, not this slice.

### Out of scope

- Email/password, teams, or local LLMs
- Visitor chat on the generated page
- Postgres / pgvector for guide search
- OCR for scanned guide PDFs
- Per-page Kubernetes pods or sequential preview ports
- Archiving OpenSpec deltas into `openspec/specs/`
- Applying cluster manifests

### Code map

| Path | What |
|---|---|
| `studio/` | FastAPI, graph, DB, publisher, page writer, OpenRouter client |
| `guides/` | Operator copywriting PDFs (gitignored; ingest → `data/rag.sqlite`) |
| `web/` | Studio SPA |
| `pagekit/` | Sales-page kit + prerender |
| `openspec/changes/` | Proposals, specs, designs, tasks |
| `docs/adr/0001-static-node-chatbot.md` | Superseded prototype ADR |
| `docs/archive/prototype-sdd.md` | Archived visitor-bot SDD |

## Deploy to Civo (`homerun.love`)

Repeatable rollout (build → push → apply → wait):

```bash
cp deploy/civo.env.example deploy/civo.env   # once: set IMAGE_REPO
# docker login to that registry
# kubectl via civo-love-kubeconfig (gitignored)
./deploy/deploy.sh
```

Later versions: commit, then `./deploy/deploy.sh` again. Same command updates the image tag (git SHA), rolls the `studio` Deployment, and **replaces** cluster SQLite + `sites/` with your local `data/` and `sites/` (except `.staging`). Pages and conversations you generated here show up at `https://homerun.love/<slug>/`.

`--skip-build` only reapplies manifests. `--skip-sync` keeps whatever is already on the PVCs. `--dry-run` server-validates YAML.

This Ingress **claims `homerun.love`**. The host currently serves a Next.js app; the first deploy replaces that apex. Studio + `/<slug>/` are one Service (FastAPI). TLS expects Traefik / a `homerun-love-tls` secret.

`./deploy/deploy.sh` also writes a `studio-app` secret from `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `SESSION_SECRET`, `STRIPE_SECRET_KEY`, `STRIPE_WEBHOOK_SECRET`, `STRIPE_PAGE_ANNUAL_PRICE_ID`, and optional `HOMERUN_LEGACY_OWNER_EMAIL` (env or `.env`). Those names match `studio/config.py`.

## Old prototype (port 3000)

```bash
npm start
```

Then open `http://localhost:3000`. Studio pages no longer use 3000; they live under `http://localhost:8080/<slug>/`.

```bash
npm test
```
