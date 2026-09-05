## Context

See `proposal.md`. Generate already writes prerendered `sites/<slug>/` and FastAPI serves `/{slug}/` locally. Civo manifests exist but were briefly pointed at a VPS copy. This slice puts pages on `homerun.love/<slug>/` from the studio PVC.

## Goals / Non-Goals

**Goals:**

- Make “deploy a page” = write files onto a volume the studio already serves.
- Same URL shape locally and on Civo: `{origin}/{slug}/`.
- Apply the studio to Civo so `https://homerun.love/` is Homerun and `https://homerun.love/<slug>/` is a generated page.

**Non-Goals:**

- Copying HTML to a VPS (later).
- A separate nginx pages pod or shared RWX volume.
- Per-page Kubernetes pods or `kubectl cp`.
- Pretty slugs without the id suffix.
- Multi-replica SQLite.
- Auth.

## Decisions

### 1. Publish process (no second copy)

```
generate
  intake -> copywriter -> visual -> page_engineer
      write sites/.staging/<slug>/
  publisher
      replace sites/<slug>/ with the staging dir
      mark published
      preview_url = PUBLIC_BASE_URL + / + slug + /
  studio (SERVE_SITES=true)
      GET /<slug>/  ->  sites/<slug>/index.html
```

On Civo, `sites/` is the `studio-sites` PVC at `/app/sites`. Staging then replace keeps a complete tree before anyone reads it.

`PAGE_RSYNC_TARGET` may exist in code; it stays unset. VPS copy is a later change.

**Alternative rejected for this slice:** rsync to a cheap VPS. **Alternative rejected:** pages pod + shared PVC. **Alternative rejected:** `kubectl cp`.

### 2. `PUBLIC_BASE_URL` + `SERVE_SITES`

- Default origin: `http://localhost:{STUDIO_PORT}`. Compose: `http://localhost:8081`. Civo: `https://homerun.love`.
- `preview_url` is always `{origin}/{slug}/`.
- `SERVE_SITES=true` on Civo so FastAPI exposes slug paths. Reserved first segments (`api`, `assets`, `health`, `static`) are never slugs.
- `STUDIO_HOST` env (default `127.0.0.1`; Docker/Civo `0.0.0.0`).
- No per-page Node processes.

### 3. Edge routing

Civo Ingress (Traefik) sends all of `homerun.love/` to the studio Service `:8080`. FastAPI splits reserved paths vs slugs. First apply **replaces** the Next.js app currently on that apex. TLS: `homerun-love-tls`.

Docker Compose may still use nginx as a local rehearsal (`/` → studio, other `/<slug>/` → volume). That is optional and does not change the Civo contract.

### 4. Studio image and persistence

One image: Python 3.12, Node (prerender), `web/dist`, `pagekit` + `node_modules`, `pip install .`. Do not copy `.env` or kubeconfig.

Replicas **1**, strategy **Recreate** (SQLite + RWO PVCs). `studio-data` → `/app/data`. `studio-sites` → `/app/sites`. A rollout keeps existing slugs.

### 5. VPS is later

Do not require `PAGE_RSYNC_TARGET`, SSH keys, or a second public origin in this slice.

## Risks / Trade-offs

- [SQLite + RWO PVC] → single studio replica.
- [Studio serves public HTML] → cluster CPU/bandwidth on the orchestrator; acceptable until traffic warrants a VPS or pages pod.
- [In-place overwrite without swap] → brief broken HTML; mitigated by staging replace.
- [Slug vs studio paths] → reserved-name list.
- [Apex takeover] → first deploy replaces the live Next.js site on `homerun.love`.

## Migration Plan

1. Point cluster ConfigMap at Civo path hosting (`SERVE_SITES=true`, `PUBLIC_BASE_URL=https://homerun.love`).
2. Apply `./deploy/deploy.sh`.
3. Generate a page and confirm `https://homerun.love/<slug>/`.

## Open Questions

None that block this slice.
