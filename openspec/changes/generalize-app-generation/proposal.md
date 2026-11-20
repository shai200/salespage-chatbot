## Why

Homerun today builds one kind of thing: a static sales page from a chat thread (`intake → copywriter → visual → page_engineer → publisher`), served at `/{slug}/`. The product we want is a chat-first studio that can build any small app — pages, a data model, a backend, and auth for that app’s end users — deploy it on our own Railway hosting, and later charge for builds and hosting at no less than twice our cost. Sales pages stay the first template, not the whole product.

## What Changes

- Treat each conversation as one **generated app**. A sales page is the `sales-page` template: static, no database, no end-user auth, still published at `{origin}/{slug}/`. A general app is the `app` template: multiple pages, its own schema, a backend API, and optional end-user auth.
- Extend the LangGraph pipeline with planner, architect, schema, backend, frontend, verify, and publish stages. The sales-page path keeps today’s copy, image, and pagekit stages. Follow-up chat edits the same app and reruns only the stages the change needs.
- Generate app code inside a fixed scaffold (React + FastAPI + Postgres migrations + tests). The model fills the scaffold; it does not pick a new stack per app. Verify must pass before publish.
- Host each `app` template as its own Railway service plus its own Postgres. Do not run generated backends inside the studio process. Do not change Homerun’s own deploy (the in-progress `deploy-homerun-civo` change, or the concurrent move of that deploy from Civo to Railway).
- Record a cost event for every LLM call, image generation, Railway meter, and static-site storage byte, tied to a build and to a hosted app. Billing and Stripe are a later change. The recorded amount is our cost, so that later change can charge at least 2×.
- Put every model call behind a provider interface. OpenRouter stays the default. Chat can later target HeartAI Studio’s OpenAI-compatible API. Image generation stays on a provider that actually offers images (OpenRouter today; HeartAI’s current API does not).
- **BREAKING** for the product rule “a conversation is always a sales page.” Existing sales-page behavior (editorial kit, Hebrew RTL, slug URL, placeholder images) stays. App-template preview URLs are the app’s public origin, not `/{slug}/` on the studio.

## Capabilities

### New Capabilities

- `generated-app`: What a generated app is — template, pages, data model, backend API, and auth for the app’s end users — and how `sales-page` is one template.
- `app-hosting`: Per-app Railway service, per-app Postgres, secrets, and public URL. Static sales pages stay on the studio origin.
- `cost-metering`: Cost-event records for LLM tokens, images, Railway usage, and static storage, per build and per hosted app. No charging.
- `model-provider`: One interface for chat and image calls, OpenRouter as the default, HeartAI as a later chat route.

### Modified Capabilities

- `generation-pipeline`: Template routing, the new stages, follow-up iteration, and verify-before-publish. Sales-page stages remain for that template.
- `studio-chat`: A conversation is one app of a given template. Intake, progress labels, and the preview URL follow the template. Sales-page chrome (pills, toolbar, Hebrew in the preview) stays.

## Impact

- `studio/graph.py` grows from five nodes to a template-branched graph. `studio/llm.py` and the direct OpenRouter image POST in `graph.py` move behind the provider.
- SQLite gains an app manifest (template, pages, schema, API, auth), build rows, and cost events. `owner_id` is stored and left empty until a later accounts change.
- New on-disk tree `apps/<slug>/` for the app template. `sites/<slug>/` remains the sales-page publish path.
- New studio env: Railway token for generated apps, optional HeartAI base URL and key. Those secrets are not copied into generated apps or into `deploy-homerun-civo`.
- Tests stay pytest. App-template verify needs Postgres for migrations. No Stripe, no Homerun login, no edit to Homerun’s Dockerfile, Compose, or Civo manifests in this change.
