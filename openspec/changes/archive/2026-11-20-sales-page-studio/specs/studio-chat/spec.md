## Purpose

Defines the operator chatbot: a local three-pane studio where each conversation is one sales page, with chat, live preview, and a new-tab URL.

## ADDED Requirements

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
