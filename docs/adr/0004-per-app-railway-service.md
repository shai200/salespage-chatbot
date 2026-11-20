# ADR 0004: One Railway service and one Postgres per generated app

## Status

Accepted for the [generalize-app-generation](../../openspec/changes/generalize-app-generation/design.md) design. Not implemented yet.

## Context

Generated backends are untrusted and each has its own schema. Homerun’s own hosting is a different effort: `deploy-homerun-civo` is in progress, and another change is moving that deploy from Civo to Railway. Sales pages are static files on the studio origin.

Railway bills active CPU and memory, not idle CPU and memory, plus egress, volume, and backups. Builds are not billed. A Postgres volume is the cost that remains while an app is quiet.

## Decision

Host each `app` as service `app-<slug>` plus Postgres `db-<slug>` in a Railway project `homerun-apps`, using `RAILWAY_APPS_TOKEN` and explicit project and service ids. Never deploy the studio repo as an app.

The service runs migrations and serves the API and the frontend on one Railway-generated origin. Rebuilds reuse the service, so the origin stays. `DATABASE_URL` is a Railway variable reference. `SESSION_SECRET` is set on the service and is not stored in SQLite.

Sales pages do not get a service. Tearing an app down deletes its database and its service.

Do not edit `deploy-homerun-civo`, the studio image, Compose, or `deploy/`.

## Consequences

- Isolation matches the way Railway meters cost. A shared runtime or a shared database was rejected because one app could read or break the others.
- The quiet-app floor is mostly database volume, not an always-on VM. Prices are not hardcoded; a poller stores what Railway reports.
- One project will accumulate many services. Split projects only if Railway refuses a create. That would not change the per-app service and database.
