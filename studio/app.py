from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from studio import config, db, graph, publisher


class CreateConversationBody(BaseModel):
    title: str = "New sales page"


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
        "preview_url": config.preview_url(port) if port else None,
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


app = FastAPI(title="Sales Page Studio", lifespan=lifespan)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/conversations")
def api_list_conversations() -> list[dict]:
    return [_public_conversation(row) for row in db.list_conversations()]


@app.post("/api/conversations")
def api_create_conversation(body: Optional[CreateConversationBody] = None) -> dict:
    title = body.title if body else "New sales page"
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


@app.post("/api/conversations/{conversation_id}/messages")
def api_post_message(conversation_id: str, body: PostMessageBody) -> dict:
    if not db.get_conversation(conversation_id):
        raise HTTPException(status_code=404, detail="Conversation not found")
    user = db.add_message(conversation_id, "user", body.content.strip())
    result = graph.run_turn(conversation_id, body.content.strip())
    reply = (result.get("assistant_message") or result.get("error") or "Done.").strip()
    assistant = db.add_message(conversation_id, "assistant", reply)
    row = db.get_conversation(conversation_id)
    if result.get("error"):
        db.update_conversation(conversation_id, status="error")
        row = db.get_conversation(conversation_id)
    return {
        "conversation": _public_conversation(row or {}),
        "user": user,
        "assistant": assistant,
        "stages_run": result.get("stages_run") or [],
        "preview_url": result.get("preview_url") or _public_conversation(row or {}).get("preview_url"),
    }


def _dist_index() -> Path | None:
    index = config.WEB_DIST / "index.html"
    return index if index.exists() else None


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
    index = _dist_index()
    if not index:
        raise HTTPException(status_code=404, detail="Studio UI is not built yet")
    candidate = config.WEB_DIST / path
    if candidate.is_file():
        return FileResponse(candidate)
    return FileResponse(index)
