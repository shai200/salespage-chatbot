## Purpose

Publishes generated sales pages as static files and serves each page at `{origin}/{slug}/`. Locally that is the studio on port 8080, or Compose nginx on port 8081. In production it is one Railway service at homerun.love.

## ADDED Requirements

### Requirement: Static publish writes the page onto the sites directory

Finishing a generate SHALL leave a complete site directory (at least `index.html`) at `sites/<slug>/` on the directory the file server reads. The studio MUST NOT start a per-page Node process or allocate a localhost port. Rebuilds SHALL overwrite the same slug directory so the public path stays stable. Files MUST be promoted from a staging directory so a reader does not observe a half-written tree.

#### Scenario: First static publish

- **WHEN** a conversation generates a page with slug `demo-offer-aaaaaaaa`
- **THEN** `sites/demo-offer-aaaaaaaa/index.html` exists and no page process is listening on 3000+

#### Scenario: Rebuild keeps the path

- **WHEN** the operator iterates on that conversation
- **THEN** the site is updated in the same `sites/<slug>/` directory and the public URL path does not change

### Requirement: Public page URL is origin plus slug

The public URL for a published page SHALL be `{public origin}/{slug}/` (trailing slash). The public origin SHALL be `PUBLIC_BASE_URL` when that is set. Chat, Open, Copy, and the preview iframe SHALL use that URL. Reserved first path segments (`api`, `assets`, `health`, `static`) MUST NOT be used as slugs.

#### Scenario: URL shape

- **WHEN** `PUBLIC_BASE_URL` is `https://homerun.love` and the slug is `northline-briefings-85fbe9b4`
- **THEN** the conversation’s preview URL is `https://homerun.love/northline-briefings-85fbe9b4/`

#### Scenario: Reserved slug is avoided

- **WHEN** an offer would slugify to `api`, `assets`, `health`, or `static`
- **THEN** the assigned slug is not exactly a reserved name

### Requirement: Reserved paths reach the studio and slug paths are files

On the public origin, `/`, `/api`, `/assets`, `/health`, and `/static` SHALL reach the studio. Any other `/{slug}/…` SHALL be served as static files from the sites directory. A missing slug SHALL be a 404, not the studio SPA. A path whose first segment is `.staging` or otherwise starts with `.` SHALL NOT be served as a page.

#### Scenario: Studio still loads at origin root

- **WHEN** the operator opens the public origin `/`
- **THEN** the Homerun studio UI loads

#### Scenario: Page is reachable under its slug

- **WHEN** `sites/demo-slug/index.html` exists
- **THEN** `GET /demo-slug/` returns that page and relative assets such as `hero.png` resolve under `/demo-slug/`

#### Scenario: Unknown slug is not the studio

- **WHEN** no directory exists for `/no-such-page/`
- **THEN** the response is 404, not the studio shell

#### Scenario: Reserved path is not a planted page

- **WHEN** a directory named `api`, `assets`, `health`, or `static` exists under the sites directory
- **THEN** requests to that path are handled by the studio and do not return that directory’s `index.html`
