# ADR 0006: Route model calls through a provider, HeartAI for chat only

## Status

Accepted for the [generalize-app-generation](../../openspec/changes/generalize-app-generation/design.md) design. Not implemented yet.

## Context

Chat goes through LangChain’s OpenAI client pointed at OpenRouter. Images are a separate HTTP call in the visual node. HeartAI Studio exposes OpenAI-compatible `POST /v1/chat/completions` and does not offer image generation. Its balance refusal is HTTP 402.

## Decision

Every chat and image call goes through one provider interface. Roles (`intake`, `planner`, `architect`, `coder`, `copy`, `image`) select the model. The default provider stays OpenRouter, including today’s model ids and the fake-LLM test mode.

`MODEL_PROVIDER=heartai` sends chat roles to HeartAI. The image role stays on OpenRouter. Pointing images at a host with no image API keeps the sales-page placeholder behavior and records no image cost. A missing key or an unpaid HeartAI balance fails the turn and publishes nothing.

Changing `OPENROUTER_BASE_URL` to HeartAI is not the seam. It would send images to a chat API and would leave usage parsing split across two modules.

## Consequences

- Nodes stop importing a model client. Cost events have one place to attach.
- HeartAI can be turned on per environment without a second graph.
- Until HeartAI returns a dollar cost on the response, those events use the price table from ADR 0005.
