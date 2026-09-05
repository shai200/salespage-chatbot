## Why

The copywriter writes sales-page JSON from the brief alone. A small set of operator-owned copywriting PDFs would improve structure, objections, and CTA sharpness without changing the page kit or adding a second database server.

## What Changes

- Ingest PDFs from `guides/` into a **separate** SQLite file (`data/rag.sqlite`) using **sqlite-vec** for KNN.
- Conversations and LangGraph checkpoints stay in `data/studio.sqlite`. Postgres / pgvector are out of scope.
- At copy time, retrieve a few passages (offer + audience + operator message) and inject them as craft notes — not quotes to paste onto the page.
- Empty index, ingest miss, or embedding failure MUST NOT block generate; today’s prompt still runs.
- First slice ships the pipeline plus a fixture PDF in tests. Real guides stay gitignored.
- Document the split in `README.md`.

## Capabilities

### New Capabilities

- `copy-guides`: Ingest copywriting PDFs into sqlite-vec; retrieve top passages for the copywriter.

### Modified Capabilities

- `generation-pipeline`: The copy stage MAY receive retrieved craft notes; it still returns the same sales-page JSON and still degrades if retrieval is unavailable.

## Impact

- New ingest command and `studio/` retrieval helper. `llm.write_page_copy` gains an optional notes argument.
- Dependencies: `sqlite-vec`, a PDF text extractor, OpenRouter embeddings (same API key).
- Civo: `rag.sqlite` lives on the existing `studio-data` PVC. No extra Service.
- `guides/` and `data/rag.sqlite` are gitignored except a tiny test fixture.
