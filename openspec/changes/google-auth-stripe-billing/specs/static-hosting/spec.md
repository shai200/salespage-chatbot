## ADDED Requirements

### Requirement: Published pages stay public without a studio session

While a page is published, `GET /{slug}/` SHALL serve that page’s HTML to any visitor. The studio MUST NOT require Google sign-in to view a published sales page.

#### Scenario: Visitor opens a live slug

- **WHEN** a published page exists at slug `northline-briefings-85fbe9b4` and the browser has no studio session
- **THEN** `GET /northline-briefings-85fbe9b4/` returns that page

### Requirement: Unpublished extra pages are not served

After billing unpublishes an extra page, `GET /{slug}/` SHALL not return that sales page (404). Site files MAY remain on disk for later restore.

#### Scenario: Unpaid extra page is hidden

- **WHEN** an extra page has been unpublished for non-payment
- **THEN** `GET /{slug}/` is 404, not the generated HTML

### Requirement: Auth and billing paths are reserved

First path segments used for Google OAuth, session, and Stripe webhooks SHALL be reserved and MUST NOT be assigned as page slugs.

#### Scenario: Auth path is not a page slug

- **WHEN** an offer would slugify to `auth` or `login`
- **THEN** the assigned slug is not exactly a reserved name

#### Scenario: Stripe webhook is not a sales page

- **WHEN** Stripe posts to the configured webhook path
- **THEN** the studio handles the event and MUST NOT treat that path as a generated page
