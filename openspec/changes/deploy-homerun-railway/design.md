## Context

See `proposal.md`. `page_engineer` writes `sites/.staging/<slug>/` and `publisher` promotes that directory onto `sites/<slug>/`. FastAPI serves the studio UI and those files from one process. There is no per-page Node server.

The first draft of this change specified Civo: a studio Deployment, an nginx pages Deployment, two PVCs, and an Ingress. That is withdrawn. HeartAI Studio already runs on Railway, and Homerun’s SQLite file cannot be shared across replicas. A cluster would add manifests and credentials without changing the product.

## Goals / Non-Goals

**Goals:**

- Make “deploy a page” mean “write files the running server already reads.”
- Ship one image that Railway can build from the Dockerfile, with secrets and local data left out of the build context.
- Prove the path split locally: Compose nginx on port 8081 (so it does not collide with a host studio on 8080) plus the studio, one volume.
- Describe production as a single Railway service, a volume at `/app/persist`, healthcheck `/health`, and `https://homerun.love`.

**Non-Goals:**

- Creating the Railway project, setting variables, attaching the volume, deploying, or changing DNS. The owner does that from `runbook.md`.
- A staging or preview environment.
- Per-page services, Kubernetes manifests, or `kubectl cp`.
- Pretty slugs without the id suffix.
- More than one studio replica.

## Decisions

### 1. Publish process

```
generate
  intake -> copywriter -> visual -> page_engineer
      write sites/.staging/<slug>/
  publisher
      replace sites/<slug>/ with the staging dir
      preview_url = public origin + / + slug + /
  the same process
      GET /<slug>/  ->  sites/<slug>/index.html
```

Staging then replace is the deploy step so a reader never sees a half-written tree. Requests under `/.staging/` are not served.

**Alternative rejected:** a second container that only serves files. Railway would need two services sharing one volume, and the studio already implements the route split. **Alternative rejected:** Kubernetes plus an Ingress. Withdrawn with the Civo target.

### 2. One Railway service, studio process only

Production is the studio container. It serves `/`, `/api`, `/assets`, `/health`, and `/static`, and it serves every other first path segment from `sites/<slug>/`. Unknown slugs are 404, not the studio shell.

Compose still runs nginx in front of the studio. That is the local rehearsal of the same split (reserved paths proxied, other paths read from the volume) and the smoke test for tasks 2.2 and 2.3. Putting nginx and uvicorn in one container would need a process supervisor for no extra behavior, so the production image stays a single process.

`railway.json` sets `numReplicas` to 1 and `overlapSeconds` to 0 so a deploy does not run two processes against the same SQLite file.

### 3. One volume at `/app/persist`

SQLite (`data/studio.sqlite`) and generated sites must survive restarts, and they must stay on the same service. `railway.json` can require a single mount path (`requiredMountPath`), so both trees live on one volume:

- mount: `/app/persist`
- `DATA_DIR` defaults to `/app/persist/data` in the image (`data/` when running from a checkout)
- `SITES_DIR` defaults to `/app/persist/sites` in the image (`sites/` when running from a checkout)

If those variables are unset and Railway sets `RAILWAY_VOLUME_MOUNT_PATH`, the app uses `<mount>/data` and `<mount>/sites`. An explicit `DATA_DIR` or `SITES_DIR` wins. The image does not copy a local database or a local `sites/` tree.

### 4. Listen address and public URL

- `PORT` wins over `STUDIO_PORT`. Railway sets `PORT`. Compose sets `STUDIO_PORT=8080` and does not set `PORT`.
- Default host remains `127.0.0.1`. The image sets `STUDIO_HOST=0.0.0.0`.
- `PUBLIC_BASE_URL` is the link origin. Production sets it to `https://homerun.love`. If it is unset and `RAILWAY_PUBLIC_DOMAIN` is present, links use `https://<that domain>` so a first boot is not stuck on `http://localhost:<port>`. The custom domain is still the production URL the owner sets.
- `preview_url` is `{origin}/{slug}/`.

### 5. Edge routing

Reserved paths go to the studio: `/`, `/api`, `/assets`, `/health`, `/static`.

Anything else is files under the sites directory. A missing slug is 404.

Reserved slug names: `api`, `assets`, `health`, `static`. `unique_slug` must not return those exactly. Names starting with `.` (including `.staging`) are not pages.

### 6. Image and Railway config

The Dockerfile copies `pyproject.toml`, `studio/`, the built `web/dist`, and `pagekit` plus its `node_modules`. The Python base image is `python:3.12-slim-bookworm`. Docker Hub no longer publishes `python:3.12-bookworm-slim` (the tag this repo first used); the slim Bookworm tag is `3.12-slim-bookworm`. The image installs Debian Node for prerender. `.dockerignore` excludes `.env`, `.env.*`, `data/`, `sites/`, and kubeconfig files. No secret is baked into `ENV`.

`railway.json` is service config-as-code (Dockerfile builder, healthcheck `/health`, one replica, required mount `/app/persist`). This repo has no TypeScript, so the Railway agent guidance for this repo is `railway.json`, not `.railway/railway.ts`. The file can be checked against Railway’s published schema without logging in. It does not declare `environments.staging` or `environments.pr`. Config-as-code does not create the volume or the domain; the runbook does. Do not add `.railway/railway.ts` beside this file — Railway will not manage one service with both.

Railway’s docs mark config-as-code deprecated in favor of TypeScript IaC, with a cutoff of 2026-12-01 for legacy services. `railway.json` is still the file this change ships, because applying TypeScript IaC means `railway config plan` against the owner’s project. If a later deploy ignores `railway.json`, migrate this manifest into `.railway/railway.ts` and plan it; do not apply that plan until the owner asks.

### 7. Production only

There is no staging or preview environment in the manifest or the runbook. Deploys of this service are production, on `homerun.love`.

## Risks / Trade-offs

- [SQLite on one volume] → one replica, and deploys drain the old container before the new one listens (`overlapSeconds` 0). A deploy has a short gap.
- [In-place overwrite without swap] → avoided by the staging replace.
- [Slug vs studio paths] → reserved names plus the nginx prefix list in Compose. Railway uses the same list inside FastAPI.
- [Volume missing at boot] → `requiredMountPath` fails the deploy instead of writing the database onto ephemeral disk.
- [Config-as-code cutoff] → called out above. The runbook does not depend on a second config file.
- [Existing local conversations] → unchanged. A checkout still uses `./data` and `./sites`.

## Migration Plan

1. Image, Compose, and `railway.json` land in git. Compose smoke is green.
2. The owner follows `runbook.md`: production service, volume at `/app/persist`, variables, deploy, then `homerun.love` DNS.
3. Check `/health`, `/`, and a generated `/<slug>/` over TLS.

## Open Questions

None for this slice. The owner chooses which Railway workspace and project to use; the runbook does not assume an existing project id.
