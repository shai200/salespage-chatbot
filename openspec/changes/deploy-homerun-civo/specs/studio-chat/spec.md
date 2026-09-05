## ADDED Requirements

### Requirement: Thread and preview use the static public URL

When static publish is enabled and a page exists, the studio thread, Open control, copy-link, and preview iframe SHALL use `{PUBLIC_BASE_URL}/{slug}/` rather than a localhost port URL.

#### Scenario: Chat link after static publish

- **WHEN** static publish is on and a page has been published
- **THEN** the assistant message and conversation `preview_url` contain the origin-plus-slug URL and do not require `localhost:<port>`
