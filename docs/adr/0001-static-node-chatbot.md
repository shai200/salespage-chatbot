# ADR 0001: Use a static page with a small Node server

## Status

Superseded by [sales-page-studio design](../../openspec/changes/sales-page-studio/design.md)

## Context

The repository started empty and needed a minimal sales page chatbot implementation plus SDD, OpenSpec, and ADR artifacts.

## Decision

Use:

- a static HTML/CSS/JS sales page for the frontend
- the built-in Node HTTP server for serving assets and chat responses
- an OpenAPI-style spec to describe the chat API

## Consequences

- No external dependencies are required
- The project stays easy to run and test
- The chatbot is intentionally simple and rule-based for this first version

## Supersession

This described the visitor FAQ prototype (`src/server.js`, `public/`). The product is the local studio chatbot (Python + React on port 8080, generated pages on 3000+). Do not treat this ADR as current architecture.
