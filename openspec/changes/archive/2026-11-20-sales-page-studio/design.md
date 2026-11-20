## Context

See `proposal.md` for motivation. The repo today is a single Node process: static `public/` files plus regex `/api/chat`. OpenSpec `openspec/specs/` is empty. Constraints from exploration: everything runs on the development machine; models are remote (OpenRouter); generated pages are React prerendered to static HTML; studio UI is React in a three-pane layout; one conversation equals one sales page.

## Goals / Non-Goals

**Goals:**

- One local studio process (Python) on port 8080 serving a React SPA and the orchestration API.
- LangGraph as the pipeline runtime; SQLite as the single local memory store (app data + graph checkpoints).
- Node only as the per-page preview server on 3000+.
- Design tokens and section kit that make generated pages look like landing pages.

**Non-Goals:**

- Multi-tenant SaaS, auth, or hosting pages on GitHub Pages / Kubernetes.
- Visitor-facing FAQ bot on the generated page (runtime chat can come later).
- Local LLMs or local image models. Images go through OpenRouter (default `meta/muse-image`).
- Replacing OpenSpec with `docs/adr` as the source of truth (ADRs optional at apply).

## Decisions

### 1. Two runtimes, two port families

- **Studio:** Python FastAPI + LangGraph, `localhost:8080`. Serves built React (and Vite proxy in development).
- **Pages:** Node serves prerendered static output, `localhost:3000 + N`.

**Why not one Node app for everything:** the orchestrator is Python LangGraph; mixing that into the existing regex server would hide the product split. **Why not Next.js for the studio:** SEO does not matter on localhost; FastAPI already owns the graph.

### 2. React studio shell vs React generated pages

Studio: Vite SPA, three panes (conversation list / thread / iframe), white/black **product** chrome, body font in the chrome. Generated pages: same Tailwind-family tokens but **editorial sales** kit (display headlines, section stack). Preview iframe plus a `target=_blank` localhost URL in the thread.

**Alternatives:** chat-only with an external link (rejected: slower iteration); studio using sales-page typography (rejected: fights the preview).

### 3. Conversation identity

`conversation_id` = LangGraph `thread_id` = one row in SQLite = one `sites/<slug>/` = one port. New chat → new page. Follow-ups resume the same thread.

### 4. Orchestration: LangGraph (Python), not CrewAI

Graph state holds brief, copy, image refs, file paths, port. Nodes: copywriter, visual, page engineer, publisher. Human-in-the-loop interrupts map to chat (approve copy / visuals / publish). Conditional edges send “punchier headline” back to copywriter without a full new site.

**Alternative:** CrewAI crews (faster demo, weaker durable HITL and port/file state).

### 5. Models: OpenRouter (language and images)

Language nodes use a chat model via OpenRouter (`OPENROUTER_BASE_URL`, default `https://openrouter.ai/api/v1`; `OPENROUTER_MODEL`). `OPENROUTER_API_KEY` in `.env`. No Ollama requirement.

The **visual** LangGraph node is the image agent. It MUST call OpenRouter’s image endpoint (not the chat completions API), decode `b64_json`, and write PNGs under `sites/<slug>/` (for example `public/hero.png`). Default image model: `meta/muse-image`, overridable with `OPENROUTER_IMAGE_MODEL`. Prompt comes from the copy/brief (hero and section art). On HTTP or empty `data`, keep today’s placeholder visuals so publish still succeeds.

Example (visual node implementation):

```python
import os
import json
import base64
import requests

response = requests.post(
  url="https://openrouter.ai/api/v1/images",
  headers={
    "Authorization": f"Bearer {os.environ['OPENROUTER_API_KEY']}",
    "Content-Type": "application/json",
  },
  data=json.dumps({
    "model": os.environ.get("OPENROUTER_IMAGE_MODEL", "meta/muse-image"),
    "prompt": "A serene mountain landscape at sunset with dramatic clouds"
  })
)

result = response.json()
for i, image in enumerate(result.get("data", [])):
  image_bytes = base64.b64decode(image["b64_json"])
  with open(f"output_{i}.png", "wb") as f:
    f.write(image_bytes)
  print(f"Saved image {i + 1}")
```

In production code, write those bytes into the conversation’s `sites/<slug>/` tree and put the public paths on graph state (`visuals.hero.src`, etc.) for the page engineer. Do not commit the API key; read it from the environment as above.

### 6. Memory: one SQLite file

e.g. `data/studio.sqlite`:

- `conversations` (id, title, slug, port, site_path, status)
- `messages` (conversation_id, role, content, created_at)
- LangGraph SQLite checkpointer keyed by `thread_id`

Site assets stay on disk under `sites/<slug>/`. **Alternative:** Postgres (unnecessary on one machine).

### 7. Editorial design system for generated pages

Tailwind + tokens: background `#ffffff`, body text `#0a0a0a`, one accent, body sans, display headline face. Section primitives only: Hero, Problem, Benefits, Proof, Offer, FAQ, Final CTA, Footer. No MUI/Chakra; shadcn only if used as primitives (button, accordion), not dashboard layout.

### 8. Publisher is a local process manager

Not GitHub Pages or Kubernetes. Allocate the lowest free port ≥ 3000, write files, `npm` build/prerender, spawn Node, store pid/port in SQLite. On studio start, respawn from the registry.

### 9. Documentation source of truth

This change’s `design.md` + delta specs are the architecture record. ADR 0001 is superseded in intent; optional new files under `docs/adr/` can summarize decisions at apply without duplicating specs.

## Risks / Trade-offs

- [Two runtimes] → Document start scripts (`studio` Python, pages spawned automatically); keep Node isolated per site.
- [Port collisions] → Bind check before assign; if 3000 is taken, skip to next free port and put the real URL in chat.
- [OpenRouter cost/latency] → Stage updates in the thread; HITL before image spend.
- [Orphan Node processes] → Registry + shutdown hook; kill pid on conversation delete (delete remains cautious).
- [Iframe vs new tab] → Some browsers restrict localhost iframes; the new-tab URL is the fallback that must always work.

## Migration Plan

1. Land studio alongside the current Node prototype; do not delete `src/` until the studio can generate a page.
2. Default `npm start` can remain the old server until apply tasks switch the README to port 8080.
3. Rollback: stop Python studio and Node children; old `node src/server.js` still runs if left intact.

## Open Questions

- Concrete display font (serif vs tight sans) — does not change specs.
- Concrete OpenRouter **chat** model id — configuration (`OPENROUTER_MODEL`).
- How many images per page (hero only vs hero + section) — start with hero; extra shots can follow without changing the API.
