## 1. App manifest (one PR)

- [ ] 1.1 Add `template`, `owner_id`, and `manifest_json` on `conversations` in `studio/db.py` (`CREATE` plus `ALTER` for an existing file) and verify a pre-existing SQLite file gains the columns, new rows use `template=sales-page` and a null `owner_id`, and `pytest` passes
- [ ] 1.2 Return `template` from the public conversation payload in `studio/app.py` and verify `GET /api/conversations` includes `sales-page` for a new conversation
- [ ] 1.3 On sales-page publish, persist a manifest with one page, no tables, no routes, `auth: none`, and `hosting: static`, and verify that JSON is on the conversation row and under the site directory after a fake-LLM publish

## 2. Model provider and model cost events (one PR)

- [ ] 2.1 Add a model provider used by every chat and image call, with an OpenRouter implementation, and verify `studio/graph.py` no longer calls the image HTTP API itself and the existing fake-LLM suite still passes
- [ ] 2.2 Map stage roles (`intake`, `planner`, `architect`, `coder`, `copy`, `image`) to provider and model, defaulting chat roles to `OPENROUTER_MODEL` and `image` to `OPENROUTER_IMAGE_MODEL`, and verify a unit test that unsets the role map still calls those defaults
- [ ] 2.3 Add `builds` and `cost_events` and write `llm.prompt` and `llm.completion` events from `complete`, and verify one fake chat call stores both token counts and a USD-micro amount, and storing the same provider request id again does not change the sum
- [ ] 2.4 Write `llm.image` only when the image provider billed the call, and verify a billed fake image stores one event and a rejection with no charge stores none while a sales page still publishes with placeholders
- [ ] 2.5 Keep the missing-OpenRouter-key failure, and verify the existing test still reports the missing key in the thread and does not publish

## 3. Planner, with the sales-page path unchanged (one PR)

- [ ] 3.1 Add a planner stage that returns a template and a stage list as checked JSON, and verify a sales brief yields `sales-page` and an application brief (multiple screens or saved records) yields `app`
- [ ] 3.2 Until the app branch in section 4 exists, stop an `app` plan with an operator-visible message and do not publish, and verify no `sites/<slug>/` is written and the conversation is not Live
- [ ] 3.3 Insert sales-page verify between page build and publish (prerendered `index.html` exists; Hebrew sets `lang="he"` and `dir="rtl"`), and verify a Hebrew fixture passes and a missing `index.html` does not publish
- [ ] 3.4 Keep the deterministic visual skip, and verify a copy-only follow-up skips image generation and an image follow-up does not
- [ ] 3.5 Show the planner stage in SSE progress, and verify a full sales-page generate reports planning then copy, and does not report schema or backend
- [ ] 3.6 Show the template on the conversation list once it is known, and verify a sales-page row and an app-plan row are distinguishable in the studio list

## 4. Scaffold and app generation on disk (one PR)

- [ ] 4.1 Add `studio/appkit/` (one FastAPI process serving a React Router frontend, Dockerfile, migration runner, email/password session kit that stores a password hash) and verify a copy into a temp directory matches the kit file hashes
- [ ] 4.2 Replace the section 3 app stop with architect output written to `apps/<slug>/app.json`, and verify a normal brief produces pages, tables, routes, and an auth mode, and a 13-page plan does not publish and the thread names the page cap
- [ ] 4.3 Write append-only SQL migrations from the schema stage, and verify a normal plan adds a migration file and a `DROP` is rejected unless the operator asked to delete data
- [ ] 4.4 Generate backend handlers and frontend pages only under `apps/<slug>/`, and verify a write whose resolved path is outside that directory fails and leaves no file outside it
- [ ] 4.5 Copy the auth kit only when auth is `end_user`, and verify a brief that asks for sign-in includes the kit’s signup route and hash module, and a brief that does not ask for accounts has no visitor login

## 5. Verify and the repair cap (one PR)

- [ ] 5.1 Run app verify in order: path jail, kit hashes, secret scan, one test per declared route, migrations on a scratch Postgres, then the app’s tests, and verify a fixture app passes and a declared route with no test does not publish
- [ ] 5.2 On failure, rerun the failing stage at most twice and then stop, and verify a seeded failure ends as Error, the thread includes the verify log, and the conversation is not Live
- [ ] 5.3 When scratch Postgres cannot be started, fail closed, and verify nothing is published and the thread says verification could not run
- [ ] 5.4 Keep the studio suite independent of Postgres, and verify `pytest` passes without `RAILWAY_APPS_TOKEN` and without a HeartAI key

## 6. Follow-up routing (one PR)

- [ ] 6.1 Route a UI-only follow-up to frontend, verify, and publish, and verify `stages_run` does not include schema or backend and the previous migration files are unchanged
- [ ] 6.2 Route a new stored field through schema, backend, frontend, and verify, and verify a new forward migration is added and no `DROP` is present
- [ ] 6.3 Keep a sales-page follow-up on that template unless the operator asks for an application, and verify the slug and the `{origin}/{slug}/` preview URL stay the same
- [ ] 6.4 Resume the same LangGraph thread for every follow-up, and verify a second message on an app conversation updates the same manifest rather than creating a conversation

## 7. Railway per app (one PR)

- [ ] 7.1 Add a Railway client that uses only `RAILWAY_APPS_TOKEN` and explicit project, environment, and service ids, and verify a test refuses a deploy whose source directory is the studio repo root
- [ ] 7.2 On first app publish, create service `app-<slug>` and Postgres `db-<slug>`, set `DATABASE_URL` as a Railway variable reference, set `SESSION_SECRET` and `APP_BASE_URL` on the service, and verify the studio row stores the ids and the public origin and does not store the database URL or the session secret
- [ ] 7.3 Redeploy the same service on rebuild, and verify the public origin is unchanged
- [ ] 7.4 When `RAILWAY_APPS_TOKEN` is missing, fail the app publish, and verify the thread says hosting is not configured, the conversation is not Live, and the app is not served at `/{slug}/`
- [ ] 7.5 Tear down by deleting that database and that service, and verify a fake Railway client received both deletes and the conversation is no longer Live
- [ ] 7.6 Point the thread, preview, Open, and Copy at the app origin for an `app` and at `{origin}/{slug}/` for a sales page, and verify the public conversation payload matches those URLs
- [ ] 7.7 Leave Homerun’s own deploy untouched, and verify the PR diff does not modify `openspec/changes/deploy-homerun-civo/`, `Dockerfile`, `docker-compose.yml`, or `deploy/`

## 8. Hosting and storage cost (one PR)

- [ ] 8.1 Import Railway CPU, memory, egress, volume, and backup cost per hosted service since a stored cursor, and verify importing the same window twice does not increase the app total
- [ ] 8.2 Record `storage.static` bytes when a sales page is published and a later byte-hour event while the directory remains, and verify both events are tied to that app
- [ ] 8.3 Do not record a Railway build-minute event when Railway reports no build charge, and verify a fixture usage payload with no build charge adds no such event
- [ ] 8.4 Return a build total and an app total, and verify the app total includes hosting events whose build id is null
- [ ] 8.5 Record cost without charging, and verify the cost-event write path does not call a payment provider

## 9. HeartAI chat route (one PR)

- [ ] 9.1 Add a HeartAI chat provider for `POST {HEARTAI_BASE_URL}/chat/completions` with `HEARTAI_API_KEY`, selected by `MODEL_PROVIDER=heartai`, and verify a mocked HeartAI server receives the bearer call and OpenRouter is not called for that chat stage
- [ ] 9.2 Keep the image role on OpenRouter when chat uses HeartAI, and verify one generate hits HeartAI for copy and OpenRouter for the hero image
- [ ] 9.3 When HeartAI is selected and the key or base URL is missing, fail the turn, and verify nothing is published
- [ ] 9.4 When HeartAI returns an unpaid-balance refusal, fail the turn, and verify nothing is published
- [ ] 9.5 When the image provider has no image API, publish a sales page with placeholders and no image cost event, and verify `images_pending` is set and no `llm.image` event is stored
- [ ] 9.6 Honor a per-role model override, and verify the planning call and the copy call use the configured model ids
- [ ] 9.7 When a chat response has tokens and no dollar cost, store a price-table amount, and verify `cost_basis` is `price_table` and the token counts are stored
- [ ] 9.8 Update the README architecture section for templates, the provider, cost events, and per-app Railway hosting, and verify it still describes sales pages at `/{slug}/` and does not claim Homerun’s own Civo or Railway deploy is done
