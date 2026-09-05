## Why

Homerun’s studio belongs on Civo at `https://homerun.love`. Generated sales pages are static HTML already written under `sites/<slug>/`. The first production publish is the same path contract as local: serve them at `https://homerun.love/<slug>/` from the studio volume. Copying HTML to a cheap VPS is a later change, not this slice.

## What Changes

- Civo runs the studio (FastAPI + LangGraph) and serves published pages from the same process.
- Generate promotes `sites/.staging/<slug>/` → `sites/<slug>/` on the `studio-sites` PVC. That write *is* publish. No rsync, `kubectl cp`, or pages pod.
- Ingress sends `homerun.love/` to the studio Service. Reserved paths stay the app; other first segments are pages (or 404).
- Preview / Open / chat URLs use `https://homerun.love/<slug>/`.
- Local default unchanged: `http://localhost:8080/<slug>/`.
- Repeatable `./deploy/deploy.sh` rolls the studio image. First apply replaces the current Next.js app on the apex.

## Capabilities

### New Capabilities

- `static-hosting`: Generate a site directory and serve `{origin}/{slug}/` from it (local FastAPI; Civo FastAPI + PVC).

### Modified Capabilities

- `local-hosting`: Local publish uses slug paths on port 8080 instead of sequential page ports.
- `studio-chat`: Preview URLs follow `PUBLIC_BASE_URL` when set, otherwise the local studio origin.

## Impact

- Cluster ConfigMap: `SERVE_SITES=true`, `PUBLIC_BASE_URL=https://homerun.love`, `PAGE_RSYNC_TARGET` unset.
- One studio Deployment (replicas 1, Recreate) mounts `studio-data` and `studio-sites`.
- VPS rsync / `pages-ssh` stay in code as unused later work; this slice does not require a VPS.
