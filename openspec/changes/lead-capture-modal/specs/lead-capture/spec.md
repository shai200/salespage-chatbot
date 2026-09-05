## Purpose

Lets a published sales page take a visitor’s name, email, and phone in a modal, store that lead on the conversation that built the page, and then send them to the operator’s next URL when one exists.

## ADDED Requirements

### Requirement: Final ask opens a lead modal

Clicking the page’s final call-to-action SHALL open a popup modal. The modal SHALL show heading text, three inputs (name, email, phone), and one submit button. The modal MUST NOT navigate away until a lead is stored successfully.

#### Scenario: Visitor clicks the ask

- **WHEN** a visitor clicks the final CTA on a published page
- **THEN** a modal appears with heading text, name, email, phone, and a submit button, and the browser does not leave the page

#### Scenario: Modal is not the first paint

- **WHEN** a visitor loads the page and has not clicked the final CTA
- **THEN** the modal is not shown as the default view

### Requirement: Lead fields are name, email, and phone

A lead submission SHALL include name, email, and phone. All three SHALL be required after trim. Email MUST look like an email. Phone MUST be a non-empty contact number (digits with optional spaces, dashes, plus, or parentheses). Empty or invalid submits MUST NOT persist a row and MUST stay on the modal with a visible error.

#### Scenario: Complete lead

- **WHEN** the visitor submits a non-empty name, a valid email, and a non-empty phone
- **THEN** the studio accepts the lead

#### Scenario: Missing phone

- **WHEN** the visitor submits name and email with a blank phone
- **THEN** no lead is stored and the modal remains open with an error

### Requirement: Leads are stored under the conversation id

Each accepted lead SHALL be written to the studio SQLite database with the conversation id of the page that collected it, plus name, email, phone, slug, and a created timestamp. A later read by conversation id SHALL return that lead. The server MUST resolve the conversation from the published page’s slug (or an equivalent server-side binding) and MUST NOT trust a client-supplied conversation id alone.

#### Scenario: Lead belongs to the page’s conversation

- **WHEN** a visitor submits a valid lead on the page for conversation `C`
- **THEN** a SQLite row exists with `conversation_id` = `C` and the submitted name, email, and phone

#### Scenario: Two pages stay isolated

- **WHEN** visitors submit leads on two different published pages
- **THEN** each lead is stored only under that page’s conversation id

### Requirement: Redirect after capture when a next URL exists

After the studio accepts a lead, if that conversation has a next URL, the page SHALL send the visitor to that URL. If there is no next URL, the visitor SHALL stay on the page and the modal SHALL show a short thank-you state instead of redirecting.

#### Scenario: Next URL is set

- **WHEN** the conversation has next URL `https://cal.example/book` and a lead is accepted
- **THEN** the visitor is taken to `https://cal.example/book`

#### Scenario: No next URL

- **WHEN** the conversation has no next URL and a lead is accepted
- **THEN** the visitor remains on the sales page and sees thank-you text in the modal

### Requirement: Public capture is same-origin on the studio host

Lead submit SHALL POST to the same origin that served the page (`http://localhost:8080` locally, `https://homerun.love` on Civo). The endpoint SHALL be under `/api`. Unknown slugs and unpublished pages MUST return an error and MUST NOT create a lead.

#### Scenario: Submit from the published page

- **WHEN** a visitor on `/{slug}/` submits a valid lead
- **THEN** the studio host stores the lead without the page calling a third-party form host

#### Scenario: Unknown page

- **WHEN** a client posts a lead for a slug that is not a published conversation
- **THEN** the response is an error and no row is written
