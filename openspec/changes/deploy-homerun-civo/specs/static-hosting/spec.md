## Purpose

Publishes generated sales pages as static files on a shared volume and serves each page at `{origin}/{slug}/`, for Docker-local proof and later Civo at homerun.love.

## ADDED Requirements

### Requirement: Static publish writes the page onto the shared sites volume

When static publish is enabled, finishing a generate SHALL leave a complete site directory (at least `index.html`) at `sites/<slug>/` on the volume the file server reads. The studio MUST NOT start a per-page Node process or allocate a localhost port. Rebuilds SHALL overwrite the same slug directory so the public path stays stable.

#### Scenario: First static publish

- **WHEN** static publish is on and a conversation generates a page with slug `demo-offer-aaaaaaaa`
- **THEN** `sites/demo-offer-aaaaaaaa/index.html` exists on the shared volume and no page process is listening on 3000+

#### Scenario: Rebuild keeps the path

- **WHEN** the operator iterates on that conversation
- **THEN** the site is updated in the same `sites/<slug>/` directory and the public URL path does not change

### Requirement: Public page URL is origin plus slug

The public URL for a statically published page SHALL be `{PUBLIC_BASE_URL}/{slug}/` (trailing slash). Chat, Open, Copy, and the preview iframe SHALL use that URL. Reserved first path segments (`api`, `assets`, `health`, and the studio root) MUST NOT be used as slugs.

#### Scenario: URL shape

- **WHEN** `PUBLIC_BASE_URL` is `https://homerun.love` and the slug is `northline-briefings-85fbe9b4`
- **THEN** the conversation’s preview URL is `https://homerun.love/northline-briefings-85fbe9b4/`

#### Scenario: Reserved slug is avoided

- **WHEN** an offer would slugify to `api` or `assets`
- **THEN** the assigned slug is not exactly a reserved name

### Requirement: Edge serves studio on reserved paths and pages on slug paths

On the public origin, `/`, `/api`, `/assets`, and `/health` SHALL reach the studio. Any other `/{slug}/…` SHALL be served as static files from `sites/<slug>/`. A missing slug SHALL be a 404, not the studio SPA.

#### Scenario: Studio still loads at origin root

- **WHEN** the operator opens the public origin `/`
- **THEN** the Homerun studio UI loads

#### Scenario: Page is reachable under its slug

- **WHEN** `sites/demo-slug/index.html` exists on the volume
- **THEN** `GET /demo-slug/` returns that page and relative assets such as `hero.png` resolve under `/demo-slug/`

#### Scenario: Unknown slug is not the studio

- **WHEN** no directory exists for `/no-such-page/`
- **THEN** the response is 404, not the studio shell
