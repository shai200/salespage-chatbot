## Purpose

Hosts each generated application on its own Railway service and database. Static sales pages stay on the studio origin and are not given a service of their own.

## ADDED Requirements

### Requirement: Each app template gets its own service and database

Publishing an `app` template SHALL create a dedicated Railway service and a dedicated database for that app only. The service SHALL serve that app’s pages and HTTP API on one public origin. Two published apps MUST NOT share a service, a database, or a public origin. A failed deploy of one app MUST NOT replace another app’s data or take the studio offline.

#### Scenario: First app publish

- **WHEN** an `app` template passes verification and hosting credentials are configured
- **THEN** the app is reachable at its own public origin and its API reads and writes only its own database

#### Scenario: Two apps stay isolated

- **WHEN** two conversations publish `app` templates
- **THEN** each has a different public origin and a different database, and a request to one does not return the other’s records

### Requirement: Sales pages stay on the studio origin

Publishing a `sales-page` template SHALL keep the current static URL `{origin}/{slug}/` and MUST NOT create a Railway service or database for that page.

#### Scenario: Sales page does not get a service

- **WHEN** a `sales-page` conversation is published
- **THEN** the page is served at `{origin}/{slug}/` and no Railway service exists for that conversation

### Requirement: Rebuild keeps the public origin

Rebuilding an `app` SHALL update the same Railway service and the same database. The public origin MUST NOT change across successful rebuilds of the same conversation.

#### Scenario: Follow-up keeps the URL

- **WHEN** the operator iterates on an already published app
- **THEN** the new deploy replaces that app at the same public origin

### Requirement: Studio secrets are not deployed with the app

A generated app’s runtime configuration MUST NOT include the studio’s model-gateway credential or the studio’s Railway credential. The app’s database URL and session secret SHALL exist only as that app’s runtime configuration. The studio’s conversation and cost records MUST NOT store those secret values.

#### Scenario: App environment is minimal

- **WHEN** an app is deployed
- **THEN** its runtime configuration has its database location, a session secret, and its public origin, and does not have the studio model key or the studio Railway token

#### Scenario: Studio records hold identifiers, not secrets

- **WHEN** the studio stores the hosting record for an app
- **THEN** that record includes the public origin and the hosting identifiers needed to manage the service, and it does not include the database URL or the session secret

### Requirement: Missing hosting credentials fail closed

When the Railway credential required to host generated apps is not configured, publishing an `app` template SHALL fail with an operator-visible error. The studio MUST NOT claim a public origin for that app and MUST NOT publish it as a static slug on the studio origin.

#### Scenario: No Railway token

- **WHEN** an `app` template is ready to publish and the generated-app Railway credential is missing
- **THEN** the thread reports that hosting is not configured, the conversation is not Live, and `/{slug}/` on the studio is not that app

### Requirement: Tearing an app down removes its hosting

The studio SHALL be able to tear down a published app. Teardown MUST remove that app’s Railway service and its database. After teardown, new hosting usage MUST NOT keep accruing for that app, and the studio UI MUST NOT present the old origin as Live.

#### Scenario: Teardown removes the service and database

- **WHEN** the studio tears down a published app
- **THEN** that app’s service and database are deleted and the conversation is no longer Live at the old origin

### Requirement: Hosting a generated app does not move the studio

Publishing or tearing down a generated app MUST NOT change how the studio itself is deployed. `/` on the studio origin SHALL still be the studio, and sales-page slug paths SHALL still be static files.

#### Scenario: Studio origin is unchanged

- **WHEN** an app template is published to Railway
- **THEN** the studio origin still serves the studio at `/` and still serves published sales pages at `/{slug}/`
