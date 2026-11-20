## REMOVED Requirements

### Requirement: Sequential local ports for pages

### Requirement: Stable port per conversation

### Requirement: Pages served independently of the studio UI

### Requirement: Registry of hosted pages

## ADDED Requirements

### Requirement: Local pages use slug paths on the studio origin

Local publish SHALL use `{studio origin}/{slug}/` (default `http://localhost:8080/<slug>/`). The studio MUST NOT spawn a per-page Node process or allocate ports 3000+. Rebuilding a conversation SHALL keep the same slug path. The studio SHALL persist the slug and site directory so a restart still serves that path.

#### Scenario: Page is on the studio origin

- **WHEN** a developer runs the studio locally with default env and a page is published
- **THEN** that page is reachable at `http://localhost:8080/<slug>/` and no process is listening on 3000 for that page

#### Scenario: Two pages have distinct paths

- **WHEN** two conversations publish pages
- **THEN** each is served under its own slug path on port 8080

#### Scenario: Rebuild keeps the slug path

- **WHEN** the operator iterates on a page already hosted at a slug path
- **THEN** the preview and the chat URL continue to use that same path

#### Scenario: Restart keeps the page

- **WHEN** the studio restarts after pages were published
- **THEN** previously published conversations are still served at their slug paths without the operator starting Node
