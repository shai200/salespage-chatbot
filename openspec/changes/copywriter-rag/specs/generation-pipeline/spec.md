## ADDED Requirements

### Requirement: Copy stage may use retrieved craft notes

When retrieval returns passages, the copy stage SHALL include them as craft notes (structure, objections, CTA sharpness) while still returning the existing sales-page JSON shape. Hebrew briefs SHALL still produce Hebrew page copy even if the guides are English. Copy-only follow-ups SHALL retrieve as well as first generates.

#### Scenario: Notes improve copy without changing the schema

- **WHEN** intake is complete and retrieval returns passages
- **THEN** the copy stage still emits headline, sections, CTA, and language as today

#### Scenario: Hebrew page with English guides

- **WHEN** the operator brief is in Hebrew and retrieved notes are in English
- **THEN** the page copy language is Hebrew

### Requirement: Missing retrieval does not block generate

If the vector index is empty, embeddings fail, or retrieval errors, the copy stage SHALL run with the current brief-only prompt. Generate MUST still publish when the rest of the pipeline succeeds. Fake or test runs that skip the gateway MUST NOT require guides or a live index.

#### Scenario: No notes still publishes

- **WHEN** retrieval returns no passages and the brief is complete
- **THEN** copy is produced and a page can still be published

#### Scenario: Fake generate ignores guides

- **WHEN** the studio runs with fake language models
- **THEN** generate completes without reading operator PDFs
