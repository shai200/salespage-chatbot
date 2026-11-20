# Deploy Homerun to Railway (production only)

Do this from a machine that is allowed to change the Railway account and the `homerun.love` DNS. Do not create a staging environment or a pull-request environment. Do not put secret values in git.

The image listens on `PORT` (Railway sets it). It serves the studio and the pages. One volume at `/app/persist` holds SQLite and the sites. `railway.json` already sets the Dockerfile builder, `/health`, one replica, and `requiredMountPath` `/app/persist`. A deploy without that mount should fail instead of writing the database onto ephemeral disk.

## 1. Production service

Use the Railway workspace that should own homerun.love. One project, one service, environment `production` only.

```bash
railway login
railway init --name homerun
```

If the project already exists, link it instead of creating another one:

```bash
railway link --project <project-name>
```

Confirm the linked environment is production (`railway status --json`). If a staging environment is offered, do not add it. Do not enable PR environments for this service.

## 2. Volume

Create one volume and set its mount path to `/app/persist`.

In the project canvas: Command Palette or right-click → volume → attach it to the homerun service → mount path `/app/persist`.

Or, with the CLI (flags vary by version; `railway volume --help` is the source of truth):

```bash
railway volume add --mount-path /app/persist --service homerun
```

After the first successful deploy you can list the mount:

```bash
railway volume files list / --service homerun
```

Expect empty `data/` and `sites/` directories after the process has started once (the app creates them).

## 3. Variables

Set these on the production service. `OPENROUTER_API_KEY` is a secret. The others are configuration, not secrets. Do not set `STUDIO_FAKE_LLM`.

| Name | Value |
|---|---|
| `OPENROUTER_API_KEY` | secret, from OpenRouter |
| `PUBLIC_BASE_URL` | `https://homerun.love` |
| `PUBLISH_MODE` | `static` |
| `STUDIO_HOST` | `0.0.0.0` |
| `DATA_DIR` | `/app/persist/data` |
| `SITES_DIR` | `/app/persist/sites` |

Optional, only to override the image defaults: `OPENROUTER_MODEL`, `OPENROUTER_IMAGE_MODEL`, `OPENROUTER_BASE_URL`.

Leave `PORT` unset. Railway injects it.

```bash
railway variable set OPENROUTER_API_KEY=<openrouter-secret> --service homerun
railway variable set PUBLIC_BASE_URL=https://homerun.love --service homerun
railway variable set PUBLISH_MODE=static --service homerun
railway variable set STUDIO_HOST=0.0.0.0 --service homerun
railway variable set DATA_DIR=/app/persist/data --service homerun
railway variable set SITES_DIR=/app/persist/sites --service homerun
```

Replace `<openrouter-secret>` in your own shell. Do not commit it, and do not paste it into this file.

Check names, not values:

```bash
railway variable list --service homerun --json
```

## 4. Deploy

From the repo root, on the commit you intend to run in production:

```bash
railway up --detach --service homerun --environment production -m "Homerun production"
railway deployment list --service homerun --environment production --json
```

Wait until the newest deployment status is `SUCCESS`. `railway up --detach` only means the build was queued. If the status is `FAILED` or `CRASHED`, read `railway logs --service homerun` before retrying. A missing volume at `/app/persist` is a failed deploy, not a reason to remove `requiredMountPath`.

## 5. Domain

```bash
railway domain homerun.love --service homerun --json
railway domain status homerun.love --service homerun --json
```

At the DNS host for `homerun.love`, add the records the `domain` command prints (routing record and ownership TXT). Do not invent a CNAME target; use the target Railway returns. Certificate issue can be retried with:

```bash
railway domain certificate retry homerun.love --service homerun --json
```

DNS can take a while. `railway domain status` is the check.

## 6. Checks

```bash
curl -fsS https://homerun.love/health
curl -fsS https://homerun.love/ | grep -q Homerun
curl -sS -o /dev/null -w '%{http_code}\n' https://homerun.love/missing-slug/
```

Expect `{"status":"ok"}`, an HTML shell that contains Homerun, and `404` for the missing slug.

Then generate one page in the studio. Its Open link should be `https://homerun.love/<slug>/`. Confirm:

```bash
curl -fsS "https://homerun.love/<slug>/"
```

That response is the sales page, not the studio shell. `railway volume files list /sites --service homerun` should show that slug’s `index.html` after publish.

Also confirm `https://homerun.love/api/conversations` returns JSON (it may be `[]` before the first conversation).
