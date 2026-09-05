## Context

See `proposal.md`. `llm.write_page_copy` is a single OpenRouter prompt (offer, audience, CTA, operator text, previous JSON). `data/studio.sqlite` holds conversations, messages, and LangGraph `SqliteSaver` checkpoints. Civo already mounts that file on the `studio-data` PVC. There is no vector index and no Postgres.

## Goals / Non-Goals

**Goals:**

- Keep conversation memory and the ANN index in SQLite, in **two files**, so the index can be wiped without touching threads.
- Load **sqlite-vec** only on the RAG connection.
- Hook retrieval at the copywriter node; degrade to today’s prompt on any miss.

**Non-Goals:**

- Postgres / pgvector.
- Visitor-facing RAG on the published page.
- OCR for scanned PDFs (skip image-only pages).
- Committing copyrighted guides.
- Changing the sales-page JSON schema or page kit.

## Decisions

### 1. Two SQLite files

`data/studio.sqlite` — unchanged. `data/rag.sqlite` — files, chunks, sqlite-vec `vec0` rows. Same PVC on Civo.

**Alternative rejected:** one file for both (extension + checkpoints share a connection). **Alternative rejected:** Postgres sidecar for a handful of PDFs.

### 2. Ingest is a command, not a chat turn

`python -m studio.ingest_guides` (or equivalent) walks `guides/*.pdf`, hashes bytes, extracts text, chunks ~500–800 tokens with ~80 overlap, embeds via OpenRouter, upserts. Unchanged hashes skip embed.

Embeddings use the existing `OPENROUTER_API_KEY` and `OPENROUTER_EMBED_MODEL`. **Default: `google/gemini-embedding-2`** (8k context, Matryoshka dims — store 768 in sqlite-vec). `liquid/lfm-2.5-embedding-350m:free` is an override only: 512-token cap (would force smaller chunks), no Hebrew in its 11 languages, free-tier rate limits, and OpenRouter may retain inputs for Liquid training. Fake/test ingest writes fixed vectors.

**Alternative rejected:** embed on every generate (cost and latency). **Alternative rejected:** commit real PDFs.

### 3. Retrieve then copy

Query text = offer + audience + operator message. Top 4–6 chunks, ~1.5k token cap, passed into `write_page_copy` as craft notes. Copy-only follow-ups retrieve too.

If `rag.sqlite` is missing, empty, or sqlite-vec fails to load: empty notes, no operator error.

### 4. Dependencies

- `sqlite-vec` (Python loader on the RAG connection only).
- A text PDF library (pypdf or pymupdf).
- OpenRouter embeddings.

Dockerfile / Civo image must include the extension so ingest and retrieve work in the pod. Guides volume: optional mount or copy into the PVC; not in the image.

## Risks / Trade-offs

- [Copyrighted guides in git] → gitignore `guides/*.pdf` except `tests/fixtures/`.
- [Prompt dump / quoting] → notes labeled as craft guidance; schema unchanged.
- [sqlite-vec load on some platforms] → degrade; copywriter still works.
- [Hebrew pages, English guides] → retrieve principles; model writes Hebrew (already specified).
- [Embedding cost on re-ingest] → hash skip.

## Migration Plan

1. Add deps and `data/rag.sqlite` path; leave ingest unused → behavior unchanged.
2. Wire retrieve into copywriter with empty-index tests.
3. Add fixture PDF + mocked embeddings.
4. Operator drops real PDFs and runs ingest locally or in the pod.

## Open Questions

None. Embed default is `google/gemini-embedding-2`.
