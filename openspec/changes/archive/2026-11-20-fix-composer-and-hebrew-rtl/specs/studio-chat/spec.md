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
