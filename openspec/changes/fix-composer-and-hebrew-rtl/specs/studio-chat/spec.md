## ADDED Requirements

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

### Requirement: Studio chrome stays LTR while preview may be RTL

The studio three-pane shell SHALL remain left-to-right. A Hebrew sales page’s RTL layout SHALL appear in the preview iframe and in the new-tab URL, not as a mirrored studio chrome.

#### Scenario: Preview is RTL, chrome is not

- **WHEN** the active conversation’s sales page is Hebrew
- **THEN** the preview (and new-tab page) is RTL and the conversation list, thread, and composer remain LTR
