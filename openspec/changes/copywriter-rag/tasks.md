## 1. Docs and ignore rules

- [x] 1.1 Document sqlite-vec RAG (two SQLite files, `guides/`, degrade path) in `README.md`, and verify the architecture section names `data/rag.sqlite` and says Postgres is out of scope
- [ ] 1.2 Gitignore operator `guides/*.pdf` and keep a tiny test fixture path committable, and verify `git check-ignore` reports a sample PDF under `guides/`

## 2. Index store

- [ ] 2.1 Add `sqlite-vec` plus a PDF text library to project deps, and verify they import in the venv
- [ ] 2.2 Add `data/rag.sqlite` config and a RAG connection that loads sqlite-vec without opening `studio.sqlite`, and verify pytest can insert a vec row in a temp file
- [ ] 2.3 Implement incremental PDF ingest (hash, chunk ~500–800 tokens, embed, upsert) as `python -m studio.ingest_guides`, and verify a second run on the same fixture does not re-embed

## 3. Copywriter hook

- [ ] 3.1 Retrieve top 4–6 passages for offer + audience + operator message and pass them into `write_page_copy` as craft notes, and verify pytest covers a mocked hit that still returns the existing JSON shape
- [ ] 3.2 Degrade when the index is empty, missing, or sqlite-vec fails to load, and verify generate still publishes under `STUDIO_FAKE_LLM` with no guides
- [ ] 3.3 Keep Hebrew page copy when notes are English, and verify the existing Hebrew RTL page test still passes

## 4. Image and cluster

- [ ] 4.1 Ensure the Dockerfile can load sqlite-vec at runtime, and verify `docker build` succeeds or record the blocker if Docker is unavailable
- [ ] 4.2 Confirm Civo needs no new Service (`rag.sqlite` on `studio-data`), and verify deploy docs/README say that
