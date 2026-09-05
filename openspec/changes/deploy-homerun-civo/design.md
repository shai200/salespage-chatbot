## Context

See `proposal.md`. Today `page_engineer` writes `sites/<slug>/` (prerendered `index.html`, relative `hero.png`) and `publisher.ensure_hosted` spawns `pagekit/serve.mjs` on port 3000+. `config.preview_url(port)` is `http://localhost:{port}/`. FastAPI binds `127.0.0.1`. There is no Docker image. Civo apply is out of the first slice; Docker Compose is the rehearsal.

## Goals / Non-Goals

**Goals:**

- Make “deploy a page” = write files onto a volume the edge already serves.
- Prove that in Docker: studio + nginx, one `sites` volume, URLs like `http://localhost:8081/<slug>/` (8081 so it does not collide with a host studio on 8080).
- Keep `python -m studio` on the host; pages are served by that same process at `/<slug>/`.

**Non-Goals:**

- Applying manifests to Civo in this slice.
- Per-page Kubernetes pods or `kubectl cp`.
- Pretty slugs without the id suffix.
- Multi-replica SQLite.

## Decisions

### 1. Publish process (the copy)

```
generate
  intake -> copywriter -> visual -> page_engineer
      write sites/.staging/<slug>/   (full site, including index.html)
  publisher (static)
      replace sites/<slug>/ with the staging dir   (os.replace / swap)
      mark published
      preview_url = PUBLIC_BASE_URL + / + slug + /
  edge nginx
      GET /<slug>/  ->  /sites/<slug>/index.html
```

There is no second copy into the cluster. Studio and the file server mount the same volume. Staging then replace is the deploy step so nginx never reads a half-written tree.

**Local mode:** same write, then spawn Node as today. Staging swap can still run so both modes share `write_site`.

**Alternative rejected:** `kubectl cp` from the studio pod (RBAC, races, extra API). **Alternative rejected:** tar upload HTTP to the pages pod (another service).

### 2. `PUBLISH_MODE` + `PUBLIC_BASE_URL`

- Default origin: `http://localhost:{STUDIO_PORT}`. Override with `PUBLIC_BASE_URL` (Compose `http://localhost:8081`, Civo `https://homerun.love`).
- `preview_url` is always `{origin}/{slug}/`.
- FastAPI serves `sites/<slug>/` for non-reserved paths. Docker/Civo edge nginx does the same from the shared volume.
- `STUDIO_HOST` env (default `127.0.0.1`; Docker `0.0.0.0`).
- No per-page Node processes.

### 3. Edge routing (Docker now, Civo later)

Reserved → studio: `/`, `/api`, `/assets`, `/health`.

Everything else: `root /sites` so `/<slug>/hero.png` → `/sites/<slug>/hero.png`. Relative assets work; CSS is already inlined in prerender.

Docker Compose uses one nginx as both edge and pages server. Civo will split: Traefik (reserved → studio Service; rest → pages Service) + nginx pages pod with the same `root /sites`. Same volume contract.

Reserved slug names: `api`, `assets`, `health`, `static`. `unique_slug` must not return those exactly.

### 4. Studio image

One image: Python 3.12, Node (prerender), `web/dist`, `pagekit` + `node_modules`, `pip install .`. Do not copy `.env` or kubeconfig. Compose passes `OPENROUTER_API_KEY` at run time. Persist `data/` and `sites/` as volumes.

### 5. Civo (specified, not applied yet)

Namespace `homerun`. PVC for `data` and `sites`. Deployment studio (replicas 1) + Deployment pages (nginx). Secret for the API key. Ingress/TLS for `homerun.love`. Same env as Compose. Apply only after Docker smoke is green.

## Risks / Trade-offs

- [SQLite + PVC] → single studio replica.
- [In-place overwrite without swap] → brief broken HTML; mitigated by staging replace.
- [Slug vs studio paths] → reserved-name list + nginx longest prefix.
- [Iframe cache] → existing studio nonce still applies; URL path is stable.
- [Existing local conversations] → unchanged; static mode is opt-in.

## Migration Plan

1. Ship config/publisher/Dockerfile/Compose.
2. `docker compose up --build` and smoke `/` plus a fixture slug.
3. Write Civo manifests; apply in a later session.

## Open Questions

None that block the Docker slice. Civo storage class and Traefik vs nginx-ingress can wait until apply-to-cluster.
