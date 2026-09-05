## Purpose

Lets operators register and sign in with Google so the studio can identify who is using it and keep each person’s work separate.

## ADDED Requirements

### Requirement: Google is the only studio sign-in

The studio SHALL offer Google OAuth as the sole way to register and sign in. The first successful Google consent for an email SHALL create a user. A later sign-in with the same Google account SHALL reuse that user. Email-and-password registration MUST NOT be offered.

#### Scenario: First Google consent creates the account

- **WHEN** a visitor completes Google OAuth and no user exists for that Google subject
- **THEN** the studio creates a user bound to that Google identity and a signed-in session

#### Scenario: Return visit is the same user

- **WHEN** the same Google account completes OAuth again
- **THEN** the studio resumes that existing user and MUST NOT create a second user for that Google subject

### Requirement: Studio UI requires a session

Until a session exists, the studio chrome SHALL show a sign-in with Google path and MUST NOT show another user’s conversations or a usable new-page control. After sign-in the operator SHALL land in the three-pane studio as that user.

#### Scenario: Anonymous opens the studio

- **WHEN** a browser with no session visits the studio origin
- **THEN** the UI presents Google sign-in and does not list conversations

#### Scenario: Sign-in reveals the studio

- **WHEN** the operator completes Google OAuth
- **THEN** the three-pane studio loads for that user

### Requirement: Session can be ended

A signed-in operator SHALL be able to sign out. After sign-out, studio conversation APIs SHALL treat the browser as anonymous.

#### Scenario: Sign out

- **WHEN** the operator signs out
- **THEN** a later request to list conversations is rejected as unauthenticated and the UI returns to Google sign-in

### Requirement: Current user is readable

A signed-in session SHALL be able to read the current user’s public identity (stable id plus display name or email). An anonymous request for the current user SHALL report that nobody is signed in, not another user’s identity.

#### Scenario: Signed-in identity

- **WHEN** a valid session asks for the current user
- **THEN** the response identifies that user and no other user

#### Scenario: Anonymous identity

- **WHEN** a browser with no session asks for the current user
- **THEN** the response indicates there is no signed-in user
