# ADR 0002: A conversation is one app, and a sales page is a template

## Status

Accepted for the [generalize-app-generation](../../openspec/changes/generalize-app-generation/design.md) design. Not implemented yet.

## Context

Each studio conversation is one sales page: intake, copy, a hero image, a prerendered page, and a static URL at `/{slug}/`. The product goal is to generate other applications from the same chat without losing that path.

## Decision

Keep one conversation as one app id (the same id as the LangGraph thread). Store a template on that row.

- `sales-page`: one static page, no database, no end-user accounts, same slug URL and editorial rules as today.
- `app`: pages, a data model, an HTTP API, and email/password auth for that app’s own users only when the brief asks for accounts.

The planner chooses the template. A follow-up updates the same app. Caps are 12 pages, 20 tables, and 40 routes.

## Consequences

- Existing sales-page behavior stays on its own graph branch.
- “One conversation is one sales page” is no longer the product rule. Archive has to replace that requirement, because `openspec/specs/` is still empty and this change adds the new one instead of editing a canonical spec.
- Homerun operator login is not part of this decision. `owner_id` stays null until a later change.
