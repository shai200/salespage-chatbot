## Purpose

Records what Homerun pays for model calls, image generation, Railway hosting, and static-page storage, per build and per hosted app, so a later billing change can charge at least twice that cost. This capability does not charge anyone.

## ADDED Requirements

### Requirement: Chat model calls record token cost on the build

Every chat-model call made while building an app SHALL record at least one cost event tied to that app and that build. The event SHALL include the provider, the model, the prompt token count, the completion token count, and the cost in integer USD micros (one million micros per US dollar). A retried call that the provider identifies as the same request MUST NOT create a second event.

#### Scenario: Successful chat call

- **WHEN** a build’s chat-model call returns usage
- **THEN** the studio stores a cost event for that app and build with the provider, model, prompt tokens, completion tokens, and a USD-micro cost

#### Scenario: Duplicate provider request

- **WHEN** the same provider request id is recorded twice for the same cost kind
- **THEN** the stored cost for that request is not doubled

### Requirement: Image generation records image cost on the build

When an image provider accepts and bills an image request, the studio SHALL record a cost event for that app and build with the image count and the USD-micro cost. When the image request fails before the provider bills it, the studio MUST NOT record an image cost event. Sales-page placeholder fallback SHALL still apply.

#### Scenario: Hero image is billed

- **WHEN** the image provider returns an image and reports or implies a charge
- **THEN** a cost event for that build records the image and its cost

#### Scenario: Image failure is not billed

- **WHEN** the image provider rejects the request with no usage and no charge
- **THEN** no image cost event is stored, and a sales page may still publish with placeholders

### Requirement: Railway usage is recorded per hosted app

For each hosted `app`, the studio SHALL record cost events for Railway CPU, memory, network egress, volume storage, and backups, using the cost Railway reports for that service. These events SHALL be tied to the app. They MAY omit a build id when the usage is not part of a generation turn. Recording the same usage window again MUST NOT increase the stored cost.

#### Scenario: Usage window is imported

- **WHEN** Railway reports CPU, memory, egress, volume, or backup cost for a hosted app since the last import
- **THEN** the studio stores those amounts against that app as USD micros

#### Scenario: The same window is imported twice

- **WHEN** the studio imports a usage window it has already stored
- **THEN** the app’s stored hosting cost does not increase

### Requirement: Static sales-page storage is recorded

Publishing a `sales-page` SHALL record the byte size stored for that page against that app. The studio SHALL also record later storage cost for bytes that remain hosted, so storage is not counted only at the moment of publish. Railway build minutes MUST NOT be recorded as a cost while Railway does not charge for builds.

#### Scenario: Publish records bytes

- **WHEN** a sales page is published to `sites/<slug>/`
- **THEN** a cost event records how many bytes were stored for that app

#### Scenario: Uncharged builds are omitted

- **WHEN** a generated app is built on Railway and Railway reports no build charge
- **THEN** no build-minute cost event is stored

### Requirement: Cost is what Homerun pays

Each cost event SHALL store Homerun’s cost, not a customer price. The amount SHALL be an integer count of USD micros and MUST be zero or greater. When the provider reports a dollar cost, the event SHALL use it and mark the basis as provider-reported. When the provider reports usage but no dollar cost, the event SHALL use a local price table and mark the basis as price-table. The studio MUST NOT create a customer charge or call a payment provider as part of recording a cost event.

#### Scenario: Provider reports dollars

- **WHEN** a model response includes a dollar cost for the call
- **THEN** the event’s amount is that cost in USD micros and its basis is provider-reported

#### Scenario: Provider reports tokens only

- **WHEN** a model response includes token counts and no dollar cost
- **THEN** the event’s amount is computed from the price table, the basis is price-table, and the token counts are still stored

#### Scenario: Recording does not charge the operator

- **WHEN** any cost event is stored
- **THEN** no customer invoice, checkout, or payment-provider call is made

### Requirement: Cost can be totaled per build and per app

The studio SHALL be able to return the sum of cost events for one build, and the sum of cost events for one app. The app total SHALL include hosting and storage events that have no build id. An event SHALL be attributable to the app it was spent on, and a build event SHALL also be attributable to the build that caused it.

#### Scenario: Build total

- **WHEN** a build has chat and image cost events
- **THEN** the build total equals the sum of those events’ USD micros

#### Scenario: App total includes hosting

- **WHEN** an app has build events and later Railway usage events with no build id
- **THEN** the app total equals the sum of both
