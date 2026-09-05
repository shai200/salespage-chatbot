## ADDED Requirements

### Requirement: Local pages use slug paths on the studio origin

Local publish SHALL use the same URL shape as cluster publish: `{studio origin}/{slug}/` (default `http://localhost:8080/<slug>/`). The studio MUST NOT spawn a per-page Node process or allocate ports 3000+. Rebuilding a conversation SHALL keep the same slug path.

#### Scenario: Page is on the studio origin

- **WHEN** a developer runs the studio locally with default env and a page is published
- **THEN** that page is reachable at `http://localhost:8080/<slug>/` and no process is listening on 3000 for that page

#### Scenario: Two pages have distinct paths

- **WHEN** two conversations publish pages
- **THEN** each is served under its own slug path on port 8080
