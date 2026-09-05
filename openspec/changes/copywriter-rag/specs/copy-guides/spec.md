## Purpose

Indexes operator-owned copywriting PDF guides in a local vector store and returns a small set of passages the copy stage can use as craft notes.

## ADDED Requirements

### Requirement: Ingest indexes PDF guides

The system SHALL ingest PDF files from an operator `guides/` directory into a vector store that is a SQLite file separate from conversation memory. Ingest SHALL be incremental: an unchanged file (same content hash) MUST NOT be re-embedded. Image-only pages MAY be skipped. The first slice MAY ship with an empty guides directory plus a test fixture; operator PDFs MUST NOT be required in the repository.

#### Scenario: First ingest of a guide

- **WHEN** the operator places a text PDF in `guides/` and runs ingest
- **THEN** that file is chunked, stored, and available for retrieval

#### Scenario: Unchanged file is skipped

- **WHEN** ingest runs again and the PDF bytes have not changed
- **THEN** the file is not re-embedded

### Requirement: Retrieve a few passages for a brief

Given offer, audience, and the operator message, retrieval SHALL return at most a handful of short passages (enough for craft notes, not a chapter). Each passage SHALL retain enough source metadata to identify the guide. If the index is empty or retrieval fails, the system SHALL return no passages and MUST NOT raise to the operator as a generate failure.

#### Scenario: Index has matching notes

- **WHEN** at least one guide is indexed and the brief mentions a familiar sales problem
- **THEN** retrieval returns a small list of passages with source labels

#### Scenario: Empty index is silent

- **WHEN** no guides have been ingested
- **THEN** retrieval returns an empty list and does not error

### Requirement: Guides stay off the published page

Retrieved passages SHALL be used as hidden craft notes for the copy model. The published sales page MUST NOT be required to quote those passages. Guide PDFs and the RAG SQLite file SHALL stay out of git except a tiny test fixture.

#### Scenario: Page does not dump the guide

- **WHEN** copy is generated with retrieved passages present
- **THEN** the published HTML is still the studio’s sales-page JSON sections, not a reprint of the PDF
