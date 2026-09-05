# Software Design Document

## Goal

Deliver a lightweight sales page with an embedded chatbot that can answer common buyer questions and drive visitors toward a call to action.

## Scope

- Single landing page describing the offer
- Embedded chatbot UI
- Minimal HTTP API for chat replies and health checks
- Rule-based responses for common sales questions

## Architecture

1. Browser renders a static sales page.
2. The chatbot widget posts visitor messages to `/api/chat`.
3. The Node HTTP server returns a deterministic reply based on intent keywords.

## Key Flows

- Pricing questions return pricing guidance
- Demo questions route users to a call-to-action
- Feature and integration questions provide concise summaries
- Unknown questions fall back to a consultation-oriented reply
