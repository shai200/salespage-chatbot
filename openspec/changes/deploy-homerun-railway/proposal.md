## Why

Homerun is a local studio: one FastAPI process that publishes each sales page at `http://localhost:8080/<slug>/`. We need the same product in production at `https://homerun.love` and `https://homerun.love/<slug>/`, without a process per page.

This change originally targeted a Civo Kubernetes cluster. The target is now Railway, the host already used for the sister product HeartAI Studio. Homerun is one operator, one SQLite file, and a directory of static pages, which fits a single Railway service and a volume better than a cluster. No Civo credentials or cluster access are required.

Prove the image and the volume publish path with Docker Compose before anyone deploys. Do not apply this to Railway in this change.

## What Changes

- Keep static publish: after `sites/<slug>/` is written, do not spawn Node or allocate ports. The public URL is `{PUBLIC_BASE_URL}/{slug}/`.
- Treat “deploy the page” as writing files onto a volume the same process already serves. No `kubectl`, no per-page services.
- Add a studio Dockerfile (Python + Node prerender + `web/dist` + pagekit) that does not copy `.env`, kubeconfig, or local `data/` / `sites/`.
- Add a local Compose stack: the studio writes `/app/persist`, and an edge nginx sends reserved paths to the studio and every other `/<slug>/` to files on that volume. This rehearses the path split. Production does not run nginx.
- Production is one Railway service. The studio process listens on `PORT`, serves the UI and the pages, and stores SQLite plus sites on one volume mounted at `/app/persist`.
- Production only. No staging environment and no pull-request preview environment. Custom domain `homerun.love`.
- Leave the Railway project, volume, variables, deploy, and DNS to the owner. The runbook is `runbook.md` in this change.

## Capabilities

### New Capabilities

- `static-hosting`: Path-based static publish (`{origin}/{slug}/`) on one volume, with reserved prefixes so slugs cannot steal the studio.

### Modified Capabilities

- `local-hosting`: Local publish uses slug paths on the studio origin instead of sequential page ports. Railway uses that same origin shape.
- `studio-chat`: Preview, Open, copy-link, and chat URLs use `{origin}/{slug}/`.

## Impact

- `studio/config.py` (listen port, storage paths, public origin), `studio/app.py` (slug files, reserved paths).
- `Dockerfile`, `.dockerignore`, `docker-compose.yml`, `deploy/nginx-edge.conf`, `deploy/smoke-compose.sh`, `railway.json`.
- `civo-love-kubeconfig` stays gitignored and is unused.
- Tests cover port and storage resolution, fixture slug serving, missing-slug 404, and the Railway manifest shape. Compose smoke covers `/`, `/<slug>/`, and `/missing-slug/`.
