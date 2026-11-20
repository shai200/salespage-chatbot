## ADDED Requirements

### Requirement: A conversation builds one app of a known template

The studio SHALL treat the selected conversation as one generated app with template `sales-page` or `app`. The conversation list SHALL show which template that row is, once the template is known. Creating a conversation SHALL NOT publish anything before the operator sends a brief.

#### Scenario: List distinguishes templates

- **WHEN** one conversation is a published sales page and another is a published app
- **THEN** the list shows a sales-page template and an app template on the matching rows

#### Scenario: New conversation is empty

- **WHEN** the operator creates a conversation and has not sent a message
- **THEN** the thread shows the first-run starter and nothing is published

### Requirement: Intake follows the template

A `sales-page` conversation SHALL still require offer, audience, and a call to action before the first publish. An `app` conversation SHALL require a description of what the application does before the first publish, and MUST NOT be held to the sales-page offer, audience, and call-to-action checklist. An incomplete first message SHALL ask for what is missing and MUST NOT publish.

#### Scenario: Sales page still asks for offer, audience, and CTA

- **WHEN** the operator’s first message asks for a sales page and omits the audience
- **THEN** the chatbot asks for the missing audience and does not publish

#### Scenario: App brief is not a sales checklist

- **WHEN** the operator’s first message describes a working application and does not name an offer, audience, or call to action
- **THEN** the studio does not reject it for a missing sales-page field, and it does not publish a sales page in place of the app

### Requirement: Preview URL follows the template

When a `sales-page` is published, the thread, the preview iframe, Open, and Copy SHALL use `{origin}/{slug}/`. When an `app` is published, those same surfaces SHALL use that app’s public hosting origin. Until an app is published, the preview pane SHALL stay in its empty state and MUST NOT load a broken iframe. The new-tab control SHALL open whichever of those URLs is live.

#### Scenario: Sales page link is the slug URL

- **WHEN** a sales page has been published
- **THEN** the thread contains `{origin}/{slug}/` and the preview loads that same URL

#### Scenario: App link is the hosted origin

- **WHEN** an app template has been published
- **THEN** the thread contains that app’s public origin, the preview loads it, and the URL is not a `/{slug}/` path on the studio origin

#### Scenario: Unpublished app has no fake preview

- **WHEN** an app conversation has not been published
- **THEN** the preview pane shows the empty state and Open and Copy are inactive

### Requirement: Progress and status cover both templates

Pipeline progress SHALL name the stage that is running for the active template. Status pills SHALL keep their current meanings: Draft when nothing is published, Generating while a turn is running, Live when a preview URL exists, Error when the last turn failed. Images pending SHALL still appear for a live sales page that uses image placeholders, and MUST NOT appear for an `app` template.

#### Scenario: App turn shows Generating

- **WHEN** the operator has sent an app brief and generation has not finished
- **THEN** the thread header shows Generating and the pending status names the current app stage

#### Scenario: Failed verification is Error

- **WHEN** verification fails and the turn stops without publishing
- **THEN** the conversation shows an Error pill and does not show Live

#### Scenario: Sales page can still be Images pending

- **WHEN** a live sales page is using placeholder images
- **THEN** the UI shows Images pending in addition to Live

#### Scenario: App has no image pill

- **WHEN** an app template is Live
- **THEN** the UI does not show Images pending for that conversation
