## 1. Studio backend skeleton

- [x] 1.1 Add a Python package for the studio (FastAPI app entrypoint) that listens on port 8080 and verify `GET /health` returns OK
- [x] 1.2 Add SQLite at `data/studio.sqlite` with `conversations` and `messages` tables and verify a conversation row can be inserted and read back
- [x] 1.3 Load `OPENROUTER_API_KEY` from `.env` and verify the app reports a clear error on generate when the key is missing (without committing `.env`)

## 2. Studio React shell

- [x] 2.1 Scaffold a Vite React app for the studio and verify FastAPI serves it (or proxies it) at `http://localhost:8080`
- [x] 2.2 Implement the three-pane layout (conversation list, thread, preview iframe) with white/black tool chrome and verify all three panes render
- [x] 2.3 Implement new conversation + conversation switcher backed by SQLite and verify restarting the studio restores the list and messages

## 3. Design system for generated pages

- [x] 3.1 Add editorial tokens (white background, near-black body, one accent, body + display fonts) and verify a sample page renders with those colors/fonts
- [x] 3.2 Add sales section primitives (Hero, Problem, Benefits, Proof, Offer, FAQ, Final CTA, Footer) and verify a composed sample looks like a landing page, not an app dashboard

## 4. Generation pipeline

- [x] 4.1 Implement a LangGraph graph with copywriter, visual, page-engineer, and publisher nodes and verify a thread runs those stages in order
- [x] 4.2 Bind graph `thread_id` to `conversation_id` with the SQLite checkpointer and verify a follow-up message resumes the same thread
- [x] 4.3 Call OpenRouter from the language nodes and verify a successful copy stage returns non-empty copy (or a clear gateway error)
- [x] 4.4 Implement short intake (offer, audience, CTA) before the first full generate and verify an incomplete first message does not publish a page
- [x] 4.5 Implement placeholder visuals when no image provider is configured and verify a page still publishes with placeholders

## 5. Local hosting

- [x] 5.1 Write generated React output to `sites/<slug>/`, prerender to static HTML, and verify the files exist on disk per conversation
- [x] 5.2 Spawn a Node static server per site starting at port 3000, then 3001, and verify two conversations get two ports and the first stays on 3000
- [x] 5.3 Persist slug/port/pid in SQLite and respawn on studio start; verify a rebuild of the same conversation keeps the same port
- [x] 5.4 After publish, post `http://localhost:<port>/` in the thread as a new-tab link and load the same URL in the preview iframe; verify both show the sales page, not the studio shell

## 6. Docs and cutover

- [x] 6.1 Update README with how to run the studio on 8080, required env vars, and how page ports work; verify the documented commands start the studio
- [x] 6.2 Leave the existing Node regex prototype runnable until the studio can publish one page; verify `node src/server.js` still starts if retained
