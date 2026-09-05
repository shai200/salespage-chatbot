## Purpose

Publishes generated sales pages as static HTML. Locally the studio serves `/{slug}/`. On Civo the same process serves `https://homerun.love/<slug>/` from the `studio-sites` PVC. Copying files to a VPS is out of scope for this change.

## ADDED Requirements

### Requirement: Generate writes a complete site directory

Finishing a generate SHALL leave `sites/<slug>/index.html` (and assets) on the studio’s disk. The studio MUST NOT start a per-page Node process. Rebuilds SHALL overwrite the same slug directory.

#### Scenario: First publish writes files

- **WHEN** a conversation generates a page with slug `demo-offer-aaaaaaaa`
- **THEN** `sites/demo-offer-aaaaaaaa/index.html` exists and no page process is listening on 3000+

#### Scenario: Rebuild keeps the slug

- **WHEN** the operator iterates on that conversation
- **THEN** the same `sites/<slug>/` directory is updated and the public path does not change

### Requirement: Civo serves pages from the studio volume

On Civo, publish SHALL be the promote onto the `studio-sites` PVC (`/app/sites/<slug>/`). The studio process SHALL serve those files at `/{slug}/`. The cluster MUST NOT require a second copy (rsync, `kubectl cp`, or a pages pod) for a page to be public. Chat, Open, Copy, and the preview iframe SHALL use `https://homerun.love/<slug>/`.

#### Scenario: Page is on the studio host

- **WHEN** a page with slug `demo-offer-aaaaaaaa` is published on Civo
- **THEN** `GET https://homerun.love/demo-offer-aaaaaaaa/` returns that page’s `index.html` and the preview URL is `https://homerun.love/demo-offer-aaaaaaaa/`

#### Scenario: Unknown slug is not the studio UI

- **WHEN** a visitor requests `https://homerun.love/no-such-page/`
- **THEN** the response is 404, not the Homerun SPA

### Requirement: Pages survive a studio restart

Site files on the `studio-sites` PVC SHALL remain after the studio pod is recreated. A subsequent `GET /<slug>/` SHALL serve the existing `index.html` without regenerating.

#### Scenario: Pod recycle still serves the slug

- **WHEN** a page has been published and the studio Deployment is rolled
- **THEN** `GET /<slug>/` still returns that page

### Requirement: Public page URL is origin plus slug

The public URL SHALL be `{PUBLIC_BASE_URL}/{slug}/` when `PUBLIC_BASE_URL` is set, otherwise the studio origin plus slug (local default). Reserved first path segments (`api`, `assets`, `health`) MUST NOT be used as slugs.

#### Scenario: URL shape on Civo

- **WHEN** `PUBLIC_BASE_URL` is `https://homerun.love` and the slug is `northline-briefings-85fbe9b4`
- **THEN** the conversation’s preview URL is `https://homerun.love/northline-briefings-85fbe9b4/`

#### Scenario: Reserved slug is avoided

- **WHEN** an offer would slugify to `api` or `assets`
- **THEN** the assigned slug is not exactly a reserved name
