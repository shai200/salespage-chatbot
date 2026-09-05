## ADDED Requirements

### Requirement: Studio conversation APIs require the owner

List, create, read, message, and conversation-lead studio APIs SHALL require a signed-in session. Those APIs SHALL only return or mutate conversations owned by that user. A request for another user’s conversation id SHALL fail as not found or forbidden, not as that conversation’s data. Visitor lead capture on a published slug remains unauthenticated.

#### Scenario: Anonymous list is rejected

- **WHEN** a client with no session requests the conversation list
- **THEN** the studio rejects the request as unauthenticated

#### Scenario: List is only the signed-in user’s pages

- **WHEN** user A has page P and user B is signed in
- **THEN** B’s conversation list does not include P

#### Scenario: Foreign conversation is hidden

- **WHEN** user B requests user A’s conversation by id
- **THEN** the studio does not return A’s messages or page metadata

#### Scenario: Visitor lead still works

- **WHEN** a visitor submits the lead form on a published page
- **THEN** the lead is stored without a studio session

### Requirement: New page is owned by the signed-in user

Creating a conversation SHALL attach it to the signed-in user. Later generate and publish for that conversation SHALL affect only that user’s page.

#### Scenario: Create binds the owner

- **WHEN** a signed-in user starts a new conversation
- **THEN** that conversation is owned by them and appears only on their list

### Requirement: Quota blocks create when billing requires a card

When page-billing requires a card before another page, the studio SHALL not create the conversation and SHALL return a billing-required error the UI can show.

#### Scenario: Fourth new chat without a card

- **WHEN** a user with three pages and no payment method starts a new conversation
- **THEN** no conversation is created and the client is told a card is required

### Requirement: Unowned existing pages are not listed

Conversations that have no owner SHALL not appear in a Google user’s studio unless that user’s email matches the configured legacy owner email, in which case those conversations SHALL be attached to that user on sign-in. Their public slugs stay served while still published.

#### Scenario: New Google user does not inherit the shared archive

- **WHEN** the instance already has unowned published pages and a new Google user signs in
- **THEN** that user’s conversation list is empty

#### Scenario: Configured legacy owner claims unowned pages

- **WHEN** a user signs in with the configured legacy owner email and unowned conversations exist
- **THEN** those conversations become owned by that user and appear in their list
