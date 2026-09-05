## ADDED Requirements

### Requirement: Generated pages ship a lead modal on the final ask

Page engineering SHALL prerender the lead modal into the static HTML and bind the final CTA to open it. Page data SHALL include the conversation id, modal heading, field labels, submit label, thank-you text, and the next URL when one exists. Mid-page buttons MUST NOT capture a lead or redirect off the page.

#### Scenario: Published HTML includes the modal

- **WHEN** a page is generated after this change
- **THEN** the shipped `index.html` contains the modal markup and the final CTA opens it

#### Scenario: Rebuild keeps the binding

- **WHEN** the operator regenerates the same conversation
- **THEN** the rebuilt page still opens the modal from the final CTA and still posts leads under that conversation id

### Requirement: Copy supplies modal text, not a destination

The copywriter SHALL write the modal heading (and button / thank-you lines) in the page language. It MUST NOT invent a next URL. The destination SHALL come only from the operator-supplied next URL on the conversation.

#### Scenario: Hebrew modal

- **WHEN** the page language is Hebrew
- **THEN** the modal heading, field labels, and button are in Hebrew

#### Scenario: Copy does not invent a checkout link

- **WHEN** the operator did not supply a next URL
- **THEN** the published page has no next URL even if the copy mentions booking or checkout
