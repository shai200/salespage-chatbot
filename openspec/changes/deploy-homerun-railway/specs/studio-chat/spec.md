## MODIFIED Requirements

### Requirement: Chat includes a new-tab sales page URL

When a sales page is available for the conversation, the chatbot SHALL include a clickable `{public origin}/{slug}/` URL in the thread. That origin SHALL be `PUBLIC_BASE_URL` when set, otherwise the studio origin. Activating that URL SHALL open the sales page in a new browser tab. The in-app preview MUST load the same URL. The thread MUST NOT require a per-page `localhost:<port>` URL.

#### Scenario: URL after publish

- **WHEN** the publisher has made a page available for the conversation
- **THEN** the thread contains the origin-plus-slug URL for that page and does not use a per-page port

#### Scenario: Preview and link together

- **WHEN** the operator has a live page
- **THEN** they can view it in the preview pane and open the same origin-plus-slug URL in a new tab

#### Scenario: Chat link after static publish

- **WHEN** a page has been published and `PUBLIC_BASE_URL` is `https://homerun.love`
- **THEN** the assistant message and conversation `preview_url` contain `https://homerun.love/<slug>/`
