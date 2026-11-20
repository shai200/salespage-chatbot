# ADR 0003: Generate apps into a fixed scaffold and verify before publish

## Status

Accepted for the [generalize-app-generation](../../openspec/changes/generalize-app-generation/design.md) design. Not implemented yet.

## Context

The current graph writes a sales page with fixed section components. A general app needs a backend, a schema, and tests. Letting the model pick a framework per brief would make those tests meaningless.

## Decision

The app template copies `studio/appkit/` (FastAPI, React Router, one process, Postgres migrations, an auth kit) and the model only fills routes, pages, and SQL. Kit files are hashed at verify time. The model does not write password hashing.

Verify runs before publish: files stay in the app directory, kit hashes match, studio secrets are absent, every declared route has a test, and migrations apply on a scratch Postgres. Failure repairs the owning stage at most twice, then the turn stops and the app is not Live.

Sales pages keep their current nodes. A smaller verify checks the prerendered HTML, including Hebrew `dir="rtl"`. Copy-only follow-ups still skip image generation by the existing word-boundary rule.

Schema follow-ups add migration files. `DROP` is allowed only when the operator asked to delete data.

## Consequences

- Two apps differ in content, not in stack. Changing the stack later means changing the kit, not the prompts.
- Studio `pytest` stays on SQLite. App verify needs Postgres and fails closed when it cannot start one.
- The graph grows a planner and an app branch. Sales-page publish is no longer “page engineer then publisher” with the check left implicit.
