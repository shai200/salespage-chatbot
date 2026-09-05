# Homerun Sales Page Builder

Local **sales page studio**: a chatbot that writes a React sales page per conversation and hosts it on localhost.

The older visitor FAQ prototype (`src/server.js`) is still runnable. The product is the studio on port 8080.

## Studio (port 8080)

Requires Python 3.9+, Node.js, and an [OpenRouter](https://openrouter.ai/) API key.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

cd web && npm install && npm run build && cd ..
cd pagekit && npm install && cd ..

# .env is gitignored — do not commit it
# OPENROUTER_API_KEY=sk-or-...
# optional: OPENROUTER_MODEL=openai/gpt-4o-mini
# optional: OPENROUTER_IMAGE_MODEL=meta/muse-image

python -m studio
```

Open `http://localhost:8080`.

Each conversation is one sales page. After publish, the thread includes `http://localhost:8080/<slug>/` (opens in a new tab) and the right pane loads the same URL.

### Page URLs

The studio stays on **8080**. Generated pages are static files served on the same origin:

- a page with slug `northline-briefings-85fbe9b4` → `http://localhost:8080/northline-briefings-85fbe9b4/`
- rebuilding that conversation keeps the same path
- `/`, `/api`, `/assets`, and `/health` stay the studio

Site files live in `sites/<slug>/` (React source + prerendered `index.html`). SQLite is `data/studio.sqlite`.

If `OPENROUTER_API_KEY` is missing, generation fails with a visible error and nothing is published.

## Tests

```bash
source .venv/bin/activate
pytest
```

## Old prototype (port 3000)

```bash
npm start
```

Then open `http://localhost:3000`. Do not run this at the same time as a published studio page if you want that page to keep 3000.

```bash
npm test
```
