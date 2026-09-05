## ADDED Requirements

### Requirement: Page status is shown as pills

The studio SHALL present each conversation’s page state as a compact pill, not as a raw `draft` string or a bare `localhost:<port>` label. Pills SHALL use these labels: Draft (no published preview), Generating (a generate is in progress for that conversation), Live (a preview URL exists), Error (the last generate failed). When a live page is still using image placeholders, the studio SHALL also show an Images pending pill. The same status SHALL appear on the conversation list row, the thread header, and the app bar. The app bar MUST NOT repeat the page title already shown in the thread header; when the page is Live the app bar SHALL include an Open control that opens the preview URL in a new tab.

#### Scenario: Draft page in the list

- **WHEN** a conversation has no preview URL
- **THEN** its list row shows a Draft pill instead of the word `draft` as plain meta text

#### Scenario: Live page after publish

- **WHEN** a conversation has a localhost preview URL
- **THEN** its list row, thread header, and app bar show a Live pill (not the raw host:port string as the only status)

#### Scenario: Generating replaces idle status

- **WHEN** the operator has sent a message and generation is still running for that conversation
- **THEN** the thread header and app bar show Generating

#### Scenario: Images still placeholders

- **WHEN** the published page is live and the conversation’s images are still pending
- **THEN** the UI shows Images pending in addition to Live

#### Scenario: App bar does not duplicate the title

- **WHEN** a conversation is selected
- **THEN** the app bar shows status (and Open if live) rather than repeating that conversation’s title

### Requirement: Preview pane is a viewer with a toolbar

The preview pane SHALL include a toolbar with: reload (which MUST reload the iframe so a newly published page is visible even when the URL is unchanged), copy link (when a preview URL exists), open in a new tab, and a desktop/mobile width toggle. The preview iframe SHALL use the selected width. When no page is published, the toolbar’s reload/copy/open controls MUST be inactive and the pane SHALL keep an empty state (not a broken iframe).

#### Scenario: Reload after republish

- **WHEN** the operator generates an update to an already-live page and then activates Reload
- **THEN** the iframe shows the updated page without the operator having to leave the studio

#### Scenario: Copy and open

- **WHEN** a conversation is live
- **THEN** Copy link puts the preview URL on the clipboard and Open (toolbar or app bar) opens that URL in a new tab

#### Scenario: Mobile width

- **WHEN** the operator chooses the mobile width
- **THEN** the preview iframe is constrained to a phone-like width inside the pane

#### Scenario: No page yet

- **WHEN** the active conversation has no preview URL
- **THEN** the preview pane does not load an iframe and reload/copy/open do not navigate or copy

### Requirement: Empty and first-run states tell the operator what to do

When the conversation list is empty, the studio SHALL tell the operator to create a page (not only “No conversations yet”). When the active conversation has no messages, the thread SHALL show a short starter that names offer, audience, and CTA, and the composer SHALL be focused and enabled. Creating a new conversation SHALL select it and focus the composer.

#### Scenario: Empty list

- **WHEN** the operator has no conversations
- **THEN** the list explains that they should create a page

#### Scenario: New conversation starter

- **WHEN** the operator creates or selects a conversation with no messages
- **THEN** the thread shows a starter for offer, audience, and CTA and the composer is focused

### Requirement: Studio chrome uses the declared typeface

The studio shell SHALL load and use IBM Plex Sans. Generated sales pages keep their own editorial fonts.

#### Scenario: Shell font

- **WHEN** the operator opens the studio UI
- **THEN** chrome text is IBM Plex Sans, not a silent fallback to the system UI font alone
