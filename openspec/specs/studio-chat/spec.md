# studio-chat Specification

## Purpose

Defines the operator chatbot: a local three-pane studio where each conversation is one sales page, with chat, live preview, and a new-tab URL.

## Requirements

### Requirement: Studio is served on a single local port

The studio application SHALL be available at `http://localhost:8080` for both the operator UI and its backend API. The studio SHALL run on the development machine and MUST NOT require a remote host for the UI or API.

#### Scenario: Operator opens the studio

- **WHEN** the studio process is running and the operator visits `http://localhost:8080`
- **THEN** the chatbot UI loads without visiting a second origin for the shell

### Requirement: Three-pane operator layout

The studio UI SHALL present three panes at once: a conversation list, the active conversation thread, and a live preview of the sales page bound to that conversation.

#### Scenario: Operator works in one screen

- **WHEN** a conversation that has a published preview is selected
- **THEN** the UI shows the conversation list, the chat thread, and an in-app preview of that conversation’s sales page

### Requirement: One conversation maps to one sales page

Each conversation SHALL correspond to exactly one sales page. Creating a new conversation SHALL start a new sales page. Selecting a different conversation SHALL show that page’s thread and preview, not another conversation’s page.

#### Scenario: New chat is a new page

- **WHEN** the operator starts a new conversation
- **THEN** subsequent generation and publish for that thread affect only that new sales page

#### Scenario: Switching conversations switches pages

- **WHEN** the operator selects a different existing conversation
- **THEN** the thread and preview (and page URL) belong to the selected conversation

### Requirement: Conversations persist across studio restarts

The studio SHALL persist conversations and their messages on the local machine so that restarting the studio restores the conversation list and thread history.

#### Scenario: Restart restores chats

- **WHEN** the operator has at least one conversation with messages and then restarts the studio
- **THEN** those conversations and messages are still listed and readable

### Requirement: Short intake then generate

On a new conversation, the chatbot SHALL gather offer, audience, and a single call-to-action before running a full page generation. After that first generation, further messages SHALL be treated as iterative edits to the same page unless the operator starts a new conversation.

#### Scenario: First message is incomplete

- **WHEN** the operator’s first message does not include offer, audience, and CTA
- **THEN** the chatbot asks for the missing items before publishing a page

#### Scenario: Follow-up edits the same page

- **WHEN** a page already exists for the conversation and the operator asks to change the headline
- **THEN** the system updates that conversation’s page rather than creating a second page

### Requirement: Chat includes a new-tab sales page URL

When a sales page is available for the conversation, the chatbot SHALL include a clickable `http://localhost:<port>/` URL in the thread. Activating that URL SHALL open the sales page in a new browser tab. The in-app preview MUST remain available in addition to this link.

#### Scenario: URL after publish

- **WHEN** the publisher has made a page available for the conversation
- **THEN** the thread contains a localhost URL for that page that opens in a new tab

#### Scenario: Preview and link together

- **WHEN** the operator has a live page
- **THEN** they can view it in the preview pane and open the same URL in a new tab

### Requirement: Studio chrome is a tool, not a landing page

The studio chrome (list, thread, chrome typography) SHALL use a compact product layout with a white background and dark body text. Large display headlines and sales-section layout SHALL appear on generated sales pages (including the preview), not as the studio shell.

#### Scenario: Shell vs preview

- **WHEN** the operator views the studio with a generated page
- **THEN** the chrome remains a dense three-pane tool and the sales typography is visible inside the preview (and the new-tab page)

### Requirement: Chat composer is at the bottom of the thread pane

The message input and send control SHALL be pinned to the bottom of the center (thread) pane. Conversation messages SHALL appear above the composer and SHALL scroll within the remaining space. The composer MUST NOT sit above the message list or immediately under the pane header when the pane is taller than the messages.

#### Scenario: Composer stays at the bottom

- **WHEN** the operator has an active conversation (including with few or no messages)
- **THEN** the chat input is at the bottom of the thread pane and the messages occupy the space above it

#### Scenario: Long thread still keeps composer at the bottom

- **WHEN** the thread has more messages than fit in the pane
- **THEN** messages scroll above the composer and the composer remains visible at the bottom

### Requirement: Send shows the user message immediately

When the operator sends a message, the studio SHALL append that message to the visible thread and SHALL clear the composer before generation finishes. The composer MUST NOT keep the submitted text while a generate is in progress.

#### Scenario: Send clears the box

- **WHEN** the operator submits a non-empty message
- **THEN** that text appears as a user message in the thread and the composer is empty, even if the assistant reply has not arrived yet

### Requirement: Pending generate shows pipeline progress

While a generate is in progress, the studio SHALL replace a generic “Working…” wait with the current pipeline stage (and a short detail) as that stage starts. Progress MUST reflect the graph (intake, copy, visuals, page build, publish), including skipped stages such as copy-only visual reuse.

#### Scenario: Full generate names the current stage

- **WHEN** the operator sends a complete brief and generation is running
- **THEN** the pending thread status shows the live stage, such as writing copy or generating the hero image, before the assistant reply arrives

#### Scenario: Incomplete intake does not invent later stages

- **WHEN** the operator’s message is still missing offer, audience, or CTA
- **THEN** the pending status stays on the intake stage and does not claim copy or publish work

### Requirement: Studio chrome stays LTR while preview may be RTL

The studio three-pane shell SHALL remain left-to-right. A Hebrew sales page’s RTL layout SHALL appear in the preview iframe and in the new-tab URL, not as a mirrored studio chrome. Individual chat messages (and the composer while typing Hebrew) SHALL use right-to-left text direction when the content is Hebrew. Chat messages SHALL render Markdown (headings, lists, links, emphasis) rather than showing the raw markup.

#### Scenario: Preview is RTL, chrome is not

- **WHEN** the active conversation’s sales page is Hebrew
- **THEN** the preview (and new-tab page) is RTL and the conversation list, thread, and composer remain LTR

#### Scenario: Hebrew chat message is RTL

- **WHEN** a thread message is written in Hebrew
- **THEN** that message (not the whole studio shell) is shown right-to-left

#### Scenario: Markdown in the thread

- **WHEN** a message contains Markdown such as headings, lists, or links
- **THEN** the thread shows the rendered formatting, not the raw markup

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
