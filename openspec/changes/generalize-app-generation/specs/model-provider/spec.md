## Purpose

Sends every studio model call through one provider interface so chat can move from OpenRouter to HeartAI Studio without rewriting generation stages. Image generation stays on a provider that offers images.

## ADDED Requirements

### Requirement: Generation stages call models only through the provider

Every chat and image call made by generation SHALL go through the configured model provider. A generation stage MUST NOT send model traffic to a host on its own. The provider SHALL expose, for each completed call, the model id, token counts or image count, a provider request id when the host supplies one, and the dollar cost when the host supplies one.

#### Scenario: Chat stage uses the provider

- **WHEN** a generation stage needs a chat completion
- **THEN** the request is sent by the configured chat provider and the stage receives the completion plus usage

#### Scenario: Image stage uses the provider

- **WHEN** the visual stage needs an image
- **THEN** the request is sent by the configured image provider and not by a separate direct call from that stage

### Requirement: OpenRouter remains the default

When no chat or image provider override is set, chat and image calls SHALL use OpenRouter with the current base URL, chat model, and image model. Missing OpenRouter credentials SHALL still fail generation with an operator-visible error and publish nothing.

#### Scenario: Default gateway is unchanged

- **WHEN** the operator has only `OPENROUTER_API_KEY` configured, as today
- **THEN** chat and image calls go to OpenRouter and a sales page still generates

#### Scenario: Missing default credentials

- **WHEN** the default provider is OpenRouter and the API key is missing
- **THEN** generation fails in the thread and no page or app is published

### Requirement: Chat can be routed to HeartAI Studio

The chat provider SHALL be switchable to HeartAI Studio without changing generation stages. HeartAI chat calls SHALL use its OpenAI-compatible chat completions API (`/v1/chat/completions`) and a bearer API key. When that provider is selected and the key or base URL is missing, generation SHALL fail with an operator-visible error and MUST NOT publish. When HeartAI refuses the call because the account cannot pay, generation SHALL fail the same way and MUST NOT publish.

#### Scenario: HeartAI is selected

- **WHEN** the chat provider is set to HeartAI and the base URL and API key are configured
- **THEN** chat stages call HeartAI’s chat completions API and do not call OpenRouter for those chat stages

#### Scenario: HeartAI is selected but not configured

- **WHEN** the chat provider is set to HeartAI and the API key or base URL is missing
- **THEN** generation fails in the thread and nothing is published

#### Scenario: HeartAI account cannot pay

- **WHEN** HeartAI rejects a chat call because the balance cannot cover it
- **THEN** the thread shows an error and nothing is published

### Requirement: Image generation stays on a provider that supports images

Image generation MUST use a provider that implements image generation. HeartAI Studio’s current API does not. When chat is routed to HeartAI, image generation SHALL continue to use the configured image provider (OpenRouter by default). When the selected image provider cannot generate images, a `sales-page` build SHALL still publish with placeholders and an operator-visible note, and no image cost event SHALL be recorded for an unbilled failure.

#### Scenario: Chat on HeartAI, images on OpenRouter

- **WHEN** the chat provider is HeartAI and the image provider is OpenRouter
- **THEN** copy and planning use HeartAI and the hero image request uses OpenRouter

#### Scenario: Image provider cannot generate images

- **WHEN** the image provider has no image API
- **THEN** a sales page still publishes with placeholder graphics and the thread says images are pending

### Requirement: Stage models are configuration

The model id used for planning, code, copy, and images SHALL be configurable per stage role without editing generation stages. Unset roles SHALL use the default chat model or the default image model, matching today’s `OPENROUTER_MODEL` and `OPENROUTER_IMAGE_MODEL` when OpenRouter is the provider for that role.

#### Scenario: Role override

- **WHEN** the planning role is configured with a different model id than the copy role
- **THEN** the planning call uses the planning model and the copy call uses the copy model

#### Scenario: No override

- **WHEN** no per-role model is set
- **THEN** chat roles use the default chat model and the image role uses the default image model
