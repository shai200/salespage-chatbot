## Context

See `proposal.md` for why. Today one FastAPI process on port 8080 runs a LangGraph thread per conversation (`studio/graph.py`): `intake → copywriter → visual → page_engineer → publisher`. Chat completions go through LangChain in `studio/llm.py` (`ChatOpenAI`, `OPENROUTER_BASE_URL`, default model `openai/gpt-4o-mini`). Hero images are a separate `httpx` POST from `visual_node` to `{OPENROUTER_BASE_URL}/images` (`fetch_openrouter_images`). Checkpoints and conversations share `data/studio.sqlite`. Sales pages are prerendered by `pagekit/` into `sites/<slug>/` and served at `{origin}/{slug}/`. There is no accounts table, no cost ledger, and no per-app process.

`deploy-homerun-civo` is the in-repo hosting change and is not applied to a cluster. A separate change is moving Homerun’s own deploy from Civo to Railway. That change is not in this tree. This design does not edit it, `deploy-homerun-civo`, the studio Dockerfile, Compose, or `deploy/`.

HeartAI Studio (`shai200/HeartAIStudio`) is an OpenAI-compatible chat router: `POST /v1/chat/completions` with `Authorization: Bearer`. It meters tokens into integer micro-dollars and its own price is already at least 2× upstream (`DEFAULT_MARKUP` defaults to 1 and refuses a lower markup). Its README lists image generation as out of scope. Railway bills active CPU and memory (not idle CPU/memory), plus egress, volume, and backups; service builds and image storage are not charged. Usage is reported per service. Those two facts are why cost events store provider-reported amounts instead of a rate card we invent.

## Goals / Non-Goals

**Goals:**

- One app model that makes `sales-page` a template and `app` a second template, without changing a published sales page’s URL or editorial rules.
- A graph the operator can follow in the thread, that refuses to publish when checks fail.
- Hosting for generated backends that cannot read another app’s database or the studio’s secrets.
- A ledger a later Stripe change can sum, per build and per app, and multiply by at least 2.
- A provider seam so chat can move to HeartAI without rewriting nodes.

**Non-Goals:**

- Stripe products, Checkout, invoices, or a customer price column.
- Homerun operator login. `owner_id` is a nullable column until that change.
- Moving the studio process onto Railway, or editing the change that does.
- A GitHub repository per app, custom domains, magic-link or OAuth login, visitor chat on a sales page.
- Image generation through HeartAI.
- Splitting Homerun’s workspace subscription fee across apps. Only metered usage is attributed.

## Decisions

### 1. Conversation, app, and template are the same row

`conversation_id` stays the LangGraph `thread_id` and becomes the app id. SQLite `conversations` gains `template` (`sales-page` | `app`), `owner_id` (nullable text), and `manifest_json`. The manifest is also written to disk so a human can read what the last successful plan was.

```text
template, pages[], data_model.tables[], api.routes[], auth: none | end_user
hosting: static | service
caps observed: pages ≤ 12, tables ≤ 20, routes ≤ 40
```

A `sales-page` manifest has one page, empty tables, empty routes, `auth: none`, `hosting: static`. An `app` manifest is what the architect node returns, after a schema check, and is what later nodes implement. Follow-ups patch this manifest; they do not start a second conversation.

**Why the same row:** the studio already restores threads from this table. A parallel `apps` table would fork identity. **Alternative rejected:** a new app id with many conversations (no operator story for it yet).

Canonical `openspec/specs/` is still empty, so the delta that replaces “one conversation is one sales page” is an ADDED requirement on `studio-chat` and `generated-app`. When those deltas are archived, retire the sales-page-studio requirement of that name instead of keeping both.

### 2. Sales page is a template branch, not a special case bolted on afterwards

The planner runs for every complete brief and returns JSON: `{template, stages, destructive}`. The graph then takes one of two branches.

```text
START → intake → planner
  incomplete or over cap → END (question in the thread, nothing published)
  template=sales-page → copywriter → visual → page_engineer → verify → publish → END
  template=app        → architect → schema → backend → frontend → verify → publish → END
  verify failed, repairs left → back to the failing stage (at most twice)
  verify failed, repairs spent → END (error, not Live)
```

Sales-page nodes stay the ones in `studio/graph.py` and `pagekit/`. The planner must not send a sales brief down the app branch. The existing word-boundary check (`_copy_only_follow_up`) remains the deterministic rule for skipping `visual`: image words never skip it, copy words skip it only when a page already exists. The planner may add work; it may not skip `visual` when that check says to run it. That keeps today’s copy-only and image follow-up tests as the contract.

**Alternative rejected:** reimplement sales pages as an `app` with no tables. That throws away the editorial kit and the slug publish path to reuse nodes that do not know about Hebrew RTL or hero placeholders.

### 3. The app template fills a scaffold; it does not invent a stack

Every `app` is the same shape, copied from `studio/appkit/` into `apps/<slug>/` and then filled in:

```text
apps/<slug>/
  app.json
  Dockerfile              # one process: API + built frontend
  backend/                # FastAPI. Auth and migration runner are kit files.
  frontend/               # React, Vite, React Router. Routes come from the manifest.
  db/migrations/          # append-only SQL
  tests/                  # one test module per declared route group
```

Kit files (password hashing, session cookie, migration runner, Dockerfile, server entry) are copied, not generated. Verify hashes them against `studio/appkit/`. The model writes route handlers, page components, and SQL migrations. Both apps therefore differ in content, not in framework. One service serves pages and the API, which matches the single public origin in the hosting spec.

**Why FastAPI and Postgres:** the studio is already Python, and Railway’s Postgres plugin injects `DATABASE_URL`. A Node backend would be a second runtime to test. **Alternative rejected:** letting the planner pick Next.js, Django, or SQLite per brief. The verify node cannot be a real gate if the stack moves every time. **Alternative rejected:** a separate frontend service. Two Railway services per app doubles the thing we have to meter and gives the preview two origins.

Schema changes are new migration files. The schema node must not emit `DROP`, `TRUNCATE`, or `DELETE` unless the planner set `destructive: true` because the operator asked to delete data. SQL is linted before it is written: single migration per file, no shell-out, no extension outside an empty allowlist.

### 4. End-user auth is a kit, and only when the brief needs it

`auth: end_user` copies the kit’s users table, signup, login, logout, and session middleware. Passwords are hashed in that kit (a maintained password-hash library, not model-written crypto). Account-only routes from the manifest are wrapped by that middleware. `auth: none` does not copy it, and verify fails if generated code still asks visitors to sign in.

These users live in the app’s Postgres. They are not rows in `studio.sqlite` and they do not establish a studio session. Homerun operator accounts are a later change; until then `owner_id` is null and the single local operator owns every row.

**Alternative rejected:** Homerun as the identity provider for generated apps. Apps would not boot without the studio, and one Homerun account would be coupled to every customer’s end users.

### 5. Follow-ups diff the manifest

The planner sees the stored manifest and the new message and returns the smallest stage list. Deterministic overrides:

- Sales page: `_copy_only_follow_up` wins over the planner for the visual stage.
- App, UI-only (`stages` has `frontend` and not `schema`): do not run schema or backend. Publish still runs verify first.
- App, stored fields changed: force `schema → backend → frontend → verify → publish` even if the planner omitted one.
- App, defect: planner names the owning stage; verify always runs before publish.
- Turning a sales page into an app only when the operator asks. The slug page is left in place until the app publish succeeds; the preview then switches to the app origin. The static directory is not deleted in that turn.

Repairs: verify returns `{ok, failed_stage, log}`. The graph re-enters `failed_stage` with the log on state, up to two times, then ends. Publish is not on the repair edge.

### 6. Verify is a gate, and generated code cannot see studio secrets

Sales-page verify: `sites/.staging/<slug>/index.html` exists; if the page language is Hebrew, the root has `lang="he"` and `dir="rtl"`. This is the check that today is implicit in `page_engineer`.

App verify, in order:

1. Every path written this turn resolves under `apps/<slug>/`.
2. Kit file hashes match.
3. A scan of the workspace rejects the studio model key, the Railway token, and the `sk-or-` / `sk-heartai-` prefixes.
4. Every manifest route has a test that calls it.
5. Migrations apply on a scratch Postgres, then the app’s pytest runs against that database. The scratch database is dropped afterward. It is not the Railway database.
6. If Postgres cannot be started, verify fails closed. Nothing is published and the thread says verification could not run.

The studio’s own `pytest` stays on SQLite and the fake LLM. It does not require Postgres. The verify task’s integration check starts Postgres the same way local Docker rehearsal already does, and asserts a fixture app passes and a missing-test fixture does not publish.

### 7. One Railway service and one Postgres per app, in one project that is not the studio

Generated apps live in a Railway project `homerun-apps`, environment `production`, created and managed only with `RAILWAY_APPS_TOKEN`. Every call passes that project id and the service id explicitly. The studio must not use a Railway CLI context linked to the studio project, or `railway up` from the repo root. That is how this change stays off Homerun’s own deploy.

For each first publish of an `app`:

- Service `app-<slug>`, built from `apps/<slug>/` (Railway upload / deploy API pointed at that directory, not a GitHub repo).
- Postgres `db-<slug>`.
- Variables on the service only: `DATABASE_URL=${{db-<slug>.DATABASE_URL}}` (Railway reference, not a pasted URL), `SESSION_SECRET` (random, set via the variable API), `APP_BASE_URL` (the public origin, no trailing slash). Railway sets `PORT`. The container runs migrations, then listens.
- Public origin is the Railway-generated domain for that service. It is stored as `preview_url`. Rebuilds deploy the same service id, so the origin stays put.
- Studio SQLite stores `railway_project_id`, `railway_environment_id`, `railway_service_id`, `railway_database_id`, and the origin. It does not store `DATABASE_URL` or `SESSION_SECRET`.

Teardown deletes the database and the service, then clears the Live URL. There is no delete button in the studio today; the teardown function is still required and tested against a fake Railway client so a later delete control has one path.

Sales pages do not get a service. `publisher.ensure_hosted` stays the static promote in `sites/<slug>/`.

**Why not a shared multi-tenant runtime:** generated code is untrusted, schemas differ per app and change on follow-up, and Railway already meters per service. A shared process would be cheaper and would also be one bug away from reading every tenant. **Why not one Railway project per app:** the usage poller and the token stay simpler with one project. Isolation that matters is the service plus the database. **Why not schema-per-app on one Postgres:** one bad migration would take down every app, and the cost we would save is the volume floor called out below.

**Cost shape, from Railway’s docs at the time of this design:** idle CPU and memory are not billed; builds and image storage are not billed; egress, volume, and backups are. A quiet app’s floor is mostly its Postgres volume, not a second always-on VM. Do not encode those prices in the studio. The poller stores the dollars Railway reports. The workspace subscription (Hobby is a flat monthly fee with a usage credit) is not split into per-app events.

Missing `RAILWAY_APPS_TOKEN`: the app turn fails in the thread, status is not Live, and the studio does not fall back to `/{slug}/`.

### 8. Cost events are our cost, written in one place per kind

New tables in `data/studio.sqlite`:

```text
builds
  id, app_id, template, status, started_at, finished_at

cost_events
  id
  app_id            # conversation id, required
  build_id          # null for hosting and storage accrual
  owner_id          # null until accounts exist
  kind              # llm.prompt | llm.completion | llm.image
                    # railway.cpu | railway.memory | railway.egress
                    # railway.volume | railway.backup
                    # storage.static
  unit              # token | image | vcpu_minute | gb_minute | byte | gb_hour
  quantity          # decimal as text
  amount_usd_micros # integer, Homerun's cost, >= 0
  provider          # openrouter | heartai | railway | homerun
  provider_request_id
  model
  cost_basis        # provider_reported | price_table
  occurred_at, recorded_at
  metadata_json
```

Unique on `(provider, provider_request_id, kind)` when `provider_request_id` is not null. Hosting windows use a synthetic id `service_id:meter:period_start:period_end` until Railway gives a measurement id.

Emission points, and no others:

| Kind | Where | When |
|---|---|---|
| `llm.prompt`, `llm.completion` | `ModelProvider.complete` | After every chat call that returns usage. Nodes cannot call a model except through this method. |
| `llm.image` | `ModelProvider.generate_image` | Only when the provider billed the image. A failure with no charge records nothing; sales-page placeholders still apply. |
| `storage.static` | static publish | Byte size of `sites/<slug>/` at publish, then a periodic byte-hour event while the directory remains. |
| `railway.*` | usage poller | Per hosted service, since a stored cursor, using Railway’s reported cost for CPU, memory, egress, volume, and backup. Same window twice does not add. |

`fetch_openrouter_images` and `_chat_model()` stop being call sites. They move inside the OpenRouter provider.

There is no `customer_price` column and no Stripe call. A later billing change has to be able to do `charge >= 2 * sum(amount_usd_micros)` for a build and for an app. HeartAI’s charge is already ≥2× its upstream; we store what HeartAI bills us (our cash cost), not the upstream raw price. Whether the later 2× should apply to that cash cost or to upstream is an open question for that billing change, not a second number in this ledger.

When the host returns tokens and no dollars (HeartAI’s public chat schema does not add a cost field; the micro-dollar ledger is on HeartAI’s server), `cost_basis` is `price_table` and the amount comes from a table keyed by model id, in USD micros per million tokens, prompt and completion separately. OpenRouter’s `usage.cost`, when present, is `provider_reported`.

Railway builds are not an event while Railway does not charge them.

### 9. Providers are selected by role, and HeartAI is chat-only

```text
ModelProvider
  complete(role, messages) -> text, model, prompt_tokens, completion_tokens,
                              cost_usd_micros | none, provider_request_id
  generate_image(role, prompt) -> images, model, cost_usd_micros | none,
                                  provider_request_id
```

Roles: `intake`, `planner`, `architect`, `coder`, `copy`, `image`. A config map sends each role to a provider and a model. Unset chat roles use `OPENROUTER_MODEL`. The image role uses `OPENROUTER_IMAGE_MODEL`. `MODEL_PROVIDER=openrouter` is the default and must keep today’s sales-page behavior, including `STUDIO_FAKE_LLM`.

`MODEL_PROVIDER=heartai` switches chat roles to `POST {HEARTAI_BASE_URL}/chat/completions` with `HEARTAI_API_KEY`. Both hosts speak the OpenAI chat schema, so one HTTP client can serve both; the difference is base URL, key, and which usage fields we trust. The image role does not follow `MODEL_PROVIDER`. It stays on OpenRouter unless `IMAGE_PROVIDER` is set to another host that implements an image API. Setting the image provider to HeartAI fails that call as “no image API”, and a sales page still publishes with placeholders and no image cost event.

A HeartAI refusal for an empty balance (HTTP 402) becomes the same operator-visible gateway error as a missing key: the turn stops, nothing is published.

**Alternative rejected:** pointing `OPENROUTER_BASE_URL` at HeartAI and calling that the abstraction. Images would silently go to a host with no image API, usage parsing would stay split between `llm.py` and `graph.py`, and cost events would have nowhere to hang.

## Risks / Trade-offs

- [Per-app Postgres volume is the hosting floor] → Recorded as Railway volume events, not hidden. Revisit a shared database only if that floor makes the later 2× price impossible; do not start there.
- [Generated code is hostile or just wrong] → Scaffold plus path jail, secret scan, kit hashes, test-per-route, two repairs, then stop. No publish on failure.
- [Planner skips a stage the diff needs] → Deterministic overrides for visual, schema, and verify. The planner is not the only router.
- [HeartAI cash cost is already marked up] → Ledger stores that cash cost. The billing change has to decide the base. This change does not multiply.
- [Price-table drift] → `cost_basis` says which number it is. Prefer `usage.cost` whenever the host sends it.
- [Railway token can deploy the wrong project] → A separate token and explicit project and service ids. No deploy from the studio repo root.
- [Scratch Postgres missing on a developer machine] → Verify fails closed with an explicit error. Studio unit tests do not need it.
- [One project accumulates many services] → Accept until Railway refuses a create. Splitting projects does not change the per-app service and database.
- [Sales page turned into an app leaves a stale slug page] → Left in place on purpose so a failed app publish does not 404 the old page. A later cleanup can remove it after a successful app deploy.
- [Canonical specs are not synced] → Deltas are ADDED. Archive must replace the old “one conversation, one sales page” requirement rather than stack a contradiction on it.

## Migration Plan

1. Land the manifest and `template=sales-page` on existing rows. No graph change. Existing pytest stays green.
2. Move chat and image calls behind the provider. Default stays OpenRouter. Cost events start for those calls.
3. Add the planner. Unknown or `app` briefs stop with a clear “not buildable yet” until the app branch exists. Sales pages keep their current stages.
4. Add the scaffold, architect, schema, backend, and frontend writers. Still no Railway.
5. Add verify, the repair cap, and local proof that a fixture app passes.
6. Add follow-up diffing on the manifest.
7. Add the Railway client, service, database, domain, and teardown. Token is `RAILWAY_APPS_TOKEN` only.
8. Add the usage poller and static byte-hour events.
9. Add the HeartAI chat provider behind configuration. Do not switch the default.

Rollback at each step is reverting that step’s code. Published sales pages stay files in `sites/`. A Railway service created in step 7 is removed with the teardown function, not by editing the studio’s own service.

## Open Questions

- Railway’s usage payload may or may not include a stable measurement id. The poller uses `service_id:meter:period_start:period_end` until one is confirmed. That does not change the event schema.
- HeartAI may later return a dollar cost on the chat response. Until it does, chat events for that provider use the price table. The fallback is already specified.
- The later billing change has to choose whether “at least 2×” applies to Homerun’s cash cost (HeartAI’s charge, Railway’s invoice lines) or to upstream model cost before HeartAI’s markup. This ledger stores cash cost only.
