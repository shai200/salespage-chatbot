## ADDED Requirements

### Requirement: Planner chooses the template and the stages

After intake, generation SHALL run a planner stage that selects the template and which later stages must run. A `sales-page` plan SHALL run copy, visuals, page build, verification, and static publish. An `app` plan SHALL run architecture, schema, backend, frontend, verification, and hosted publish. An incomplete brief SHALL stop at intake or planning, ask for what is missing, and MUST NOT publish.

#### Scenario: Sales-page plan

- **WHEN** intake is complete for a sales page
- **THEN** the pipeline produces copy, visuals, a coded page, a verification result, and a static publish, and it does not provision a database

#### Scenario: App plan

- **WHEN** intake is complete for an application
- **THEN** the pipeline produces an architecture, a schema, a backend API, a frontend, a verification result, and only then a hosted publish

#### Scenario: Incomplete app brief

- **WHEN** the operator’s application request is missing what the app should do
- **THEN** the chatbot asks for the missing description and does not publish an app

### Requirement: Sales-page stages stay in force

For the `sales-page` template, copy, image generation, prerender, Hebrew right-to-left output, and placeholder images on image failure SHALL behave as they do today. A follow-up that only changes copy SHALL update the page without generating a new image. A follow-up that asks for an image SHALL run image generation.

#### Scenario: Copy-only sales follow-up

- **WHEN** the operator asks only to change the headline on an existing sales page
- **THEN** the copy and the page are updated, the existing image is kept, and the slug URL does not change

#### Scenario: Image follow-up still generates

- **WHEN** the operator asks to replace the hero image
- **THEN** the visual stage runs and does not skip image generation

### Requirement: Verification gates publish

The studio MUST NOT publish an app or a sales page when verification fails. Verification for an `app` SHALL run the app’s automated tests, apply its schema to a database, and check that every API route the plan declared has a test. Verification for a `sales-page` SHALL check that the prerendered page exists and that a Hebrew page is right-to-left. On failure, the studio SHALL repair the failing stage at most twice. After those attempts fail, the turn SHALL stop with an operator-visible error and MUST NOT publish.

#### Scenario: App tests pass

- **WHEN** an `app` plan’s tests pass and its schema applies
- **THEN** publish is allowed to proceed

#### Scenario: A declared route has no test

- **WHEN** the plan declares an API route and the generated app has no automated test for it
- **THEN** verification fails and nothing is published

#### Scenario: Repairs are bounded

- **WHEN** verification fails and two repair attempts also fail
- **THEN** the thread shows the verification error and the app is not published and is not marked Live

### Requirement: Generated code stays inside a fixed shape

An `app` template SHALL be generated as pages, a schema, an HTTP API, and tests inside one supported application shape. The generator MUST NOT choose a different language, framework, or database per app. Generated files for an `app` SHALL stay in that app’s workspace. Generated sales pages SHALL stay in the sales-page site directory. Verification MUST fail, and publish MUST NOT run, when generated output contains the studio’s model-gateway credential or Railway credential.

#### Scenario: Two apps share one shape

- **WHEN** two different `app` briefs are generated
- **THEN** both are the same kind of application (pages, a SQL schema, one HTTP API, and tests) and differ in their pages, schema, and handlers

#### Scenario: Secret leak blocks publish

- **WHEN** generated output contains the studio model key or the studio Railway token
- **THEN** verification fails and nothing is published

### Requirement: Follow-up chat reruns the narrowest stages

A follow-up SHALL resume the same app and SHALL rerun only the stages required by the change, followed by verification and publish. A copy or visual change that does not change stored fields MUST NOT regenerate the schema or the backend. A change to stored fields SHALL regenerate the schema and the backend, then the frontend, then verification and publish. A request that only reports a defect SHALL rerun the stage that owns the defect, then verification and publish.

#### Scenario: UI-only follow-up

- **WHEN** the operator asks to change button text on an existing app and does not ask to change stored data
- **THEN** the frontend is updated and verified, and the existing schema and database are left in place

#### Scenario: Data-model follow-up

- **WHEN** the operator asks the app to store a new field
- **THEN** the schema, the API, and the frontend are updated, verification runs, and the same app is published again

#### Scenario: Data is not dropped unless asked

- **WHEN** the operator asks to add a field and does not ask to delete existing data
- **THEN** the new schema is a forward change and existing tables and columns are not dropped

#### Scenario: Sales page is still one page

- **WHEN** the operator follows up on a `sales-page` conversation
- **THEN** the result is still that sales page at the same slug, not a second page and not an `app` template, unless the operator asks to turn it into an application

### Requirement: The operator sees the stage that is running

While a generate is in progress, the pending status SHALL name the stage that is actually running. For an `app` those stages include planning, architecture, schema, backend, frontend, verification, and publish. For a `sales-page` the existing labels (brief, copy, image, page build, publish) SHALL remain, including the skipped-image label on a copy-only follow-up.

#### Scenario: App generate names the stage

- **WHEN** an application generate is running the schema stage
- **THEN** the pending thread status says so before the assistant reply arrives

#### Scenario: Sales-page labels stay

- **WHEN** a sales-page generate is writing copy
- **THEN** the pending status reports the copy stage and does not claim schema or backend work
