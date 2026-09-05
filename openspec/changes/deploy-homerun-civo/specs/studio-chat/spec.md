## ADDED Requirements

### Requirement: Thread and preview use the static public URL

When a page exists, the studio thread, Open control, copy-link, and preview iframe SHALL use `{PUBLIC_BASE_URL}/{slug}/` (on Civo, `https://homerun.love/<slug>/`) rather than a localhost port URL.

#### Scenario: Chat link after static publish

- **WHEN** a page has been published with `PUBLIC_BASE_URL` set to `https://homerun.love`
- **THEN** the assistant message and conversation `preview_url` contain `https://homerun.love/<slug>/` and do not require `localhost:<port>`
