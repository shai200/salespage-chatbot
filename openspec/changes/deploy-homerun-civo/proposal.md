## Why

Homerun is a local studio: one FastAPI process plus a Node server per sales page on sequential localhost ports. We need the same product on Civo at `https://homerun.love` (orchestrator) and `https://homerun.love/<slug>/` (static pages) without running a process per page. Prove the image and the write-to-volume publish path in Docker locally before touching the cluster.

## What Changes

- Add a **static publish mode**: after `sites/<slug>/` is written, do not spawn Node or allocate ports. The public URL is `{PUBLIC_BASE_URL}/{slug}/`.
- Treat “deploy the page” as **writing (then promoting) files onto a shared volume** that a static file server reads. No `kubectl cp`, no per-page pods.
- Add a **Dockerfile** for the studio (Python + Node prerender + `web/dist`) and a local **Compose** stack that mimics Civo: studio writes `/sites`, an edge nginx serves reserved paths to the studio and all other `/<slug>/` paths from that volume.
- Local and cluster both publish at `/{slug}/`. Local default is `http://localhost:8080/<slug>/` served by the studio process. No per-page ports.
- Defer live Civo apply until Docker local is green. Manifests and DNS/TLS are specified but not required to ship in the first apply slice.

## Capabilities

### New Capabilities

- `static-hosting`: Path-based static publish of generated pages (`{origin}/{slug}/`), shared volume as the deploy step, reserved prefixes so slugs cannot steal the studio.

### Modified Capabilities

- `local-hosting`: Local publish uses slug paths on port 8080 instead of sequential page ports.
- `studio-chat`: Preview / Open / chat URLs MUST use the static public URL when static publish is on, instead of `http://localhost:<port>/`.

## Impact

- `studio/config.py`, `studio/publisher.py`, `studio/app.py`, `studio/pages.py` (promote/slug safety), listen host.
- New `Dockerfile`, `docker-compose.yml`, `deploy/nginx-edge.conf`.
- Later: Civo Deployments (studio + pages), PVC, Ingress, Secret. `civo-love-kubeconfig` stays gitignored.
- Tests for static URL generation and publisher no-spawn. Docker smoke: studio `/` and a fixture `/<slug>/`.
