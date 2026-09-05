## Purpose

Defines how the studio turns a conversation into a React sales page: orchestration stages, editorial visual rules, and prerendered static output.

## ADDED Requirements

### Requirement: Orchestrated generation stages

Page generation SHALL run as an orchestrated pipeline with distinct stages: ad copy, visuals/graphics, page design and code, and publish. The operator chatbot SHALL be the only user-facing control surface for starting and steering that pipeline. A follow-up that targets one concern (for example copy) SHALL NOT force an unnecessary full republish of unrelated stages when those outputs are still valid.

#### Scenario: First full build

- **WHEN** intake is complete and the operator proceeds to generate
- **THEN** the system produces copy, visuals, coded page, and a local publish for that conversation

#### Scenario: Copy-only follow-up

- **WHEN** the operator asks only to change headline copy on an existing page
- **THEN** copy is updated and the page is rebuilt without treating the request as a brand-new site

### Requirement: Remote models via a configured gateway

Language and (when enabled) image generation SHALL use a remote model gateway configured on the development machine. Models MUST NOT be required to run locally. Credentials SHALL come from the environment (not from the repository).

#### Scenario: Generation uses the gateway

- **WHEN** a generation stage needs a model
- **THEN** the system calls the configured remote gateway and does not require a local model server

#### Scenario: Missing credentials

- **WHEN** the gateway API key is not configured
- **THEN** generation fails with an operator-visible error and no page is published

### Requirement: Editorial sales page appearance

Generated sales pages SHALL use a white page background and black or near-black body text. Headlines SHALL use a distinct display typeface and at most one accent color on selected words. Pages SHALL be composed as a landing-page section stack (hero, problem, benefits, proof, offer, FAQ, final CTA, footer) rather than as an application dashboard.

#### Scenario: Visual contract

- **WHEN** a page is generated from a complete brief
- **THEN** the rendered page has a white background, dark body copy, distinctive headlines, and recognizable sales sections including a hero and a CTA

### Requirement: React authored, static HTML shipped

Generated sales pages SHALL be authored as React and SHALL be prerendered to static HTML for serving. A generated page MUST remain readable as HTML without depending on the studio chatbot.

#### Scenario: New tab is the sales page

- **WHEN** the operator opens the conversation’s localhost URL in a new tab
- **THEN** they see the generated sales page, not the studio three-pane shell

### Requirement: Visual stage generates images via the remote gateway

The visual stage SHALL request images from the same remote model gateway used for language (OpenRouter), using that gateway’s image API. Generated image bytes SHALL be stored on disk with the sales page and referenced from the page. The image model SHALL be configurable. If the image request fails or returns no images, generation MUST still complete with placeholders and an operator-visible note.

#### Scenario: Successful image generation

- **WHEN** intake is complete, the gateway key is configured, and the image API returns image data
- **THEN** the published page includes those images as files on disk (not only a pending placeholder)

#### Scenario: Image request fails

- **WHEN** the image API errors or returns no images
- **THEN** the page is still published with placeholder graphics and an operator-visible note that images are pending
