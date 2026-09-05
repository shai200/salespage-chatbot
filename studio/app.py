from __future__ import annotations

import json
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, Optional

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel, Field

from studio import config, db, graph, publisher


class CreateConversationBody(BaseModel):
    title: str = "Untitled page"


class PostMessageBody(BaseModel):
    content: str = Field(min_length=1)


def _public_conversation(row: dict) -> dict:
    port = row.get("port")
    return {
        "id": row["id"],
        "title": row["title"],
        "slug": row.get("slug"),
        "port": port,
        "site_path": row.get("site_path"),
        "status": row.get("status"),
        "offer": row.get("offer"),
        "audience": row.get("audience"),
        "cta": row.get("cta"),
        "images_pending": bool(row.get("images_pending")),
        "preview_url": config.preview_url(port=port, slug=row.get("slug") or ""),
        "created_at": row.get("created_at"),
        "updated_at": row.get("updated_at"),
    }


@asynccontextmanager
async def lifespan(_app: FastAPI):
    db.init()
    graph.get_graph()
    publisher.respawn_all()
    try:
        yield
    finally:
        publisher.shutdown_all()


app = FastAPI(title="Homerun Sales Page Builder", lifespan=lifespan)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/conversations")
def api_list_conversations() -> list[dict]:
    return [_public_conversation(row) for row in db.list_conversations()]


@app.post("/api/conversations")
def api_create_conversation(body: Optional[CreateConversationBody] = None) -> dict:
    title = body.title if body else "Untitled page"
    return _public_conversation(db.create_conversation(title=title))


@app.get("/api/conversations/{conversation_id}")
def api_get_conversation(conversation_id: str) -> dict:
    row = db.get_conversation(conversation_id)
    if not row:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return {
        **_public_conversation(row),
        "messages": db.list_messages(conversation_id),
    }


@app.get("/api/conversations/{conversation_id}/messages")
def api_list_messages(conversation_id: str) -> list[dict]:
    if not db.get_conversation(conversation_id):
        raise HTTPException(status_code=404, detail="Conversation not found")
    return db.list_messages(conversation_id)


def _sse(event: str, data: dict[str, Any]) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


def _message_payload(conversation_id: str, user: dict, result: dict) -> dict:
    reply = (result.get("assistant_message") or result.get("error") or "Done.").strip()
    assistant = db.add_message(conversation_id, "assistant", reply)
    if result.get("error"):
        db.update_conversation(conversation_id, status="error")
    row = db.get_conversation(conversation_id)
    public = _public_conversation(row or {})
    return {
        "conversation": public,
        "user": user,
        "assistant": assistant,
        "stages_run": result.get("stages_run") or [],
        "preview_url": result.get("preview_url") or public.get("preview_url"),
    }


@app.post("/api/conversations/{conversation_id}/messages")
def api_post_message(conversation_id: str, body: PostMessageBody, request: Request):
    if not db.get_conversation(conversation_id):
        raise HTTPException(status_code=404, detail="Conversation not found")
    text = body.content.strip()
    user = db.add_message(conversation_id, "user", text)
    wants_stream = "text/event-stream" in (request.headers.get("accept") or "")

    if not wants_stream:
        result = graph.run_turn(conversation_id, text)
        return _message_payload(conversation_id, user, result)

    def events():
        try:
            for event in graph.iter_turn_events(conversation_id, text):
                if event.get("type") == "progress":
                    yield _sse(
                        "progress",
                        {
                            "stage": event.get("stage"),
                            "label": event.get("label"),
                            "detail": event.get("detail"),
                            "short": event.get("short"),
                        },
                    )
                elif event.get("type") == "result":
                    yield _sse("done", _message_payload(conversation_id, user, event.get("state") or {}))
        except Exception as exc:
            yield _sse("error", {"detail": str(exc)})

    return StreamingResponse(
        events(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


def _dist_index() -> Path | None:
    index = config.WEB_DIST / "index.html"
    return index if index.exists() else None


def _published_site_file(path: str) -> Path | None:
    parts = [part for part in path.split("/") if part]
    if not parts:
        return None
    slug = parts[0]
    if slug in config.RESERVED_SLUGS:
        return None
    site = (config.SITES_DIR / slug).resolve()
    if not site.is_dir() or not (site / "index.html").is_file():
        return None
    rel = Path(*parts[1:]) if len(parts) > 1 else Path("index.html")
    candidate = (site / rel).resolve()
    try:
        candidate.relative_to(site)
    except ValueError:
        return None
    if candidate.is_file():
        return candidate
    if candidate.is_dir() and (candidate / "index.html").is_file():
        return candidate / "index.html"
    if len(parts) == 1:
        return site / "index.html"
    return None


@app.get("/")
def studio_root():
    index = _dist_index()
    if index:
        return FileResponse(index)
    return {
        "status": "ok",
        "ui": "Build the studio UI with `cd web && npm install && npm run build`",
    }


@app.get("/{path:path}")
def studio_spa(path: str):
    if path.startswith("api/") or path == "health":
        raise HTTPException(status_code=404)
    if config.SERVE_SITES:
        published = _published_site_file(path)
        if published:
            return FileResponse(published)
    candidate = config.WEB_DIST / path
    if candidate.is_file():
        return FileResponse(candidate)
    raise HTTPException(status_code=404, detail="Not found")
