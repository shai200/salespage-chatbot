## 1. Static publish mode

- [x] 1.1 Add `PUBLISH_MODE`, `PUBLIC_BASE_URL`, and `STUDIO_HOST` to config and bind uvicorn to `STUDIO_HOST`, and verify default local host remains `127.0.0.1`
- [x] 1.2 Write sites through `sites/.staging/<slug>/` then replace `sites/<slug>/`, and verify a generate leaves `index.html` only in the live slug dir
- [x] 1.3 In static mode skip Node spawn and set `preview_url` to `{PUBLIC_BASE_URL}/{slug}/`, and verify pytest covers URL shape plus no listen on 3000
- [x] 1.4 Keep reserved slugs (`api`, `assets`, `health`, `static`) out of `unique_slug`, and verify a reserved base gets a distinct slug
- [x] 1.5 Local and cluster both serve `{origin}/{slug}/` from `sites/<slug>/` with no per-page ports, and verify pytest covers distinct slug URLs plus 404 for unknown slugs

## 2. Docker local rehearsal

- [ ] 2.1 Add a studio Dockerfile (Python + Node prerender + web dist + pagekit) that does not copy `.env` or kubeconfig, and verify `docker build` succeeds
- [ ] 2.2 Add Compose + edge nginx (reserved paths → studio, other `/<slug>/` → `/sites`), and verify `docker compose up` serves `/` as Homerun
- [ ] 2.3 Smoke a fixture site on the shared volume at `/<slug>/`, and verify `GET /missing-slug/` is 404 not the studio UI

## 3. Civo path hosting

- [x] 3.1 Add cluster manifests and `deploy/deploy.sh` for the studio Service + Ingress on Civo, and verify the script and YAML exist
- [x] 3.2 Set cluster `SERVE_SITES=true` and `PUBLIC_BASE_URL=https://homerun.love` (rsync unset) so FastAPI serves `/<slug>/` from the `studio-sites` PVC, and verify pytest covers that origin plus a served page after a simulated restart
- [ ] 3.3 Run `./deploy/deploy.sh` against Civo and verify the studio at `https://homerun.love/` plus a generated page at `https://homerun.love/<slug>/`
