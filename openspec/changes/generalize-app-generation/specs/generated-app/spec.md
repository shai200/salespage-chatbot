## Purpose

Defines a generated app as the thing one studio conversation builds. A sales page is the first template; a multi-page app with its own data, API, and end-user auth is the second.

## ADDED Requirements

### Requirement: One conversation is one app

Each conversation SHALL correspond to exactly one generated app. Creating a conversation SHALL start a new app. A follow-up in that conversation SHALL update that app and MUST NOT create a second app. The app SHALL have a template of `sales-page` or `app`.

#### Scenario: New conversation starts a new app

- **WHEN** the operator starts a new conversation
- **THEN** generation and publish for that thread affect only that new app

#### Scenario: Follow-up keeps the same app

- **WHEN** an app already exists for the conversation and the operator asks for a change
- **THEN** the system updates that app rather than creating another one

#### Scenario: Switching conversations switches apps

- **WHEN** the operator selects a different conversation
- **THEN** the thread, preview, and public URL belong to the selected conversation’s app

### Requirement: A sales brief selects the sales-page template

When the operator asks for a sales page, landing page, or a single offer page, the app template SHALL be `sales-page`. That template SHALL publish one static page and MUST NOT provision a database or end-user accounts for visitors of the page.

#### Scenario: Offer brief stays a sales page

- **WHEN** the operator describes an offer, an audience, and a call to action and does not ask for accounts, saved records, or multiple screens
- **THEN** the conversation’s template is `sales-page` and the published result is one static page with no visitor login and no database

#### Scenario: Existing sales-page rules still apply

- **WHEN** a `sales-page` app is published
- **THEN** it still follows the editorial sales-page appearance, Hebrew right-to-left layout when the copy is Hebrew, and static publish at `{origin}/{slug}/`

### Requirement: An application brief selects the app template

When the operator describes software with more than one screen, saved records, or accounts for the people who use it, the template SHALL be `app`. A published `app` SHALL expose one or more pages with distinct paths, a data model that the app’s API reads and writes, and an HTTP API for that data.

#### Scenario: Multi-screen brief becomes an app

- **WHEN** the operator asks for an application with more than one screen or with records that visitors create and see again later
- **THEN** the conversation’s template is `app` and the published result has those pages, a data model, and an HTTP API

#### Scenario: A sales page is not forced into the app template

- **WHEN** the operator asks only for a sales page
- **THEN** the template is not `app`

### Requirement: End-user auth belongs to the generated app

Auth for the people who use a generated app SHALL be separate from any Homerun operator login. When the brief requires accounts, the published app SHALL provide email-and-password sign-up and sign-in for those people, and account-only pages and API routes MUST reject a visitor who is not signed in. When the brief does not require accounts, the published app MUST NOT require visitors to sign in. Signing in to a generated app MUST NOT sign the visitor in to Homerun.

#### Scenario: Brief needs accounts

- **WHEN** the operator asks for an app whose users sign in
- **THEN** the published app lets a new person create an account with email and password, sign in, and reach the account-only parts of that app

#### Scenario: Signed-out visitor is refused

- **WHEN** a visitor who is not signed in calls an account-only API route or opens an account-only page
- **THEN** the app refuses that request

#### Scenario: Brief does not need accounts

- **WHEN** the operator asks for an app that does not mention users, login, or accounts
- **THEN** the published app does not ask visitors to sign in

#### Scenario: App users are not Homerun operators

- **WHEN** a person signs in on a published app
- **THEN** that session is for that app only and does not authenticate them to the studio

#### Scenario: Password is not stored in the clear

- **WHEN** a person signs up with a password
- **THEN** the app’s database stores a password hash and does not store the password itself

### Requirement: The app description survives a restart

The studio SHALL persist the app’s template, pages, data model, API, and auth mode so a restart restores them for the next follow-up. A `sales-page` app MAY persist an empty data model and an empty API.

#### Scenario: Restart keeps the plan

- **WHEN** an app has been planned and the operator restarts the studio
- **THEN** the same conversation still exposes that template, its pages, its data model, its API, and its auth mode

### Requirement: Oversized apps are refused

The studio MUST NOT publish an app with more than 12 pages, more than 20 tables, or more than 40 API routes. When a request would exceed any of those caps, the studio SHALL tell the operator what is over the cap and MUST NOT publish a partial app.

#### Scenario: Too many pages

- **WHEN** the planned app has 13 or more pages
- **THEN** the thread explains that the page cap was exceeded and no app is published
