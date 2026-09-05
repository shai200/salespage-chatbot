from __future__ import annotations

import json
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, Optional

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, RedirectResponse, StreamingResponse
from pydantic import BaseModel, Field

from studio import auth, billing, config, db, graph, intake, leads, publisher


class CreateConversationBody(BaseModel):
    title: str = "Untitled page"


class PostMessageBody(BaseModel):
    content: str = Field(min_length=1)


class LeadBody(BaseModel):
    name: str = ""
    email: str = ""
    phone: str = ""
    conversation_id: Optional[str] = None


class FakeLoginBody(BaseModel):
    email: str = "tester@example.com"
    name: str = "Tester"
    google_sub: str = "google-sub-tester"


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
        "next_url": row.get("next_url") or None,
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
auth.attach_session(app)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/me")
def api_me(request: Request) -> dict:
    return {"user": auth.public_user(auth.current_user(request))}


@app.get("/auth/google")
async def auth_google(request: Request):
    if config.STUDIO_FAKE_AUTH:
        raise HTTPException(status_code=404, detail="Google OAuth is not used in fake auth")
    client = auth.get_oauth()
    if client is None:
        raise HTTPException(status_code=503, detail="Google sign-in is not configured")
    redirect = str(request.base_url).rstrip("/") + "/auth/google/callback"
    return await client.google.authorize_redirect(request, redirect)


@app.get("/auth/google/callback")
async def auth_google_callback(request: Request):
    client = auth.get_oauth()
    if client is None:
        raise HTTPException(status_code=503, detail="Google sign-in is not configured")
    token = await client.google.authorize_access_token(request)
    profile = token.get("userinfo") or {}
    auth.login_google_profile(request, profile)
    return RedirectResponse(url="/", status_code=302)


@app.post("/auth/logout")
def auth_logout(request: Request) -> dict:
    auth.logout(request)
    return {"ok": True}


@app.post("/auth/fake")
def auth_fake(request: Request, body: Optional[FakeLoginBody] = None) -> dict:
    if not config.STUDIO_FAKE_AUTH:
        raise HTTPException(status_code=404, detail="Not found")
    payload = body or FakeLoginBody()
    user = auth.login_google_profile(
        request,
        {"sub": payload.google_sub, "email": payload.email, "name": payload.name},
    )
    return {"user": auth.public_user(user)}


@app.get("/api/billing/status")
def api_billing_status(request: Request) -> dict:
    user = auth.require_user(request)
    return billing.status_payload(user)


@app.post("/api/billing/checkout")
def api_billing_checkout(request: Request) -> dict:
    user = auth.require_user(request)
    return billing.start_checkout(user, config.public_origin())


@app.post("/api/billing/stripe/webhook")
async def api_stripe_webhook(request: Request) -> dict:
    payload = await request.body()
    if config.STUDIO_FAKE_AUTH or not config.STRIPE_WEBHOOK_SECRET:
        event = json.loads(payload.decode() or "{}") if payload else {}
        billing.handle_stripe_event(event)
        return {"ok": True}
    import stripe

    sig = request.headers.get("stripe-signature", "")
    try:
        event = stripe.Webhook.construct_event(payload, sig, config.STRIPE_WEBHOOK_SECRET)
    except Exception as exc:
        raise HTTPException(status_code=400, detail="Invalid Stripe signature") from exc
    billing.handle_stripe_event(event)
    return {"ok": True}


@app.get("/api/conversations")
def api_list_conversations(request: Request) -> list[dict]:
    user = auth.require_user(request)
    return [_public_conversation(row) for row in db.list_conversations(user["id"])]


@app.post("/api/conversations")
def api_create_conversation(
    request: Request, body: Optional[CreateConversationBody] = None
) -> dict:
    user = auth.require_user(request)
    if db.count_conversations(user["id"]) >= config.FREE_PAGE_LIMIT and not billing.has_payment_method(
        user
    ):
        raise HTTPException(status_code=402, detail=billing.create_blocked_payload(user))
    title = body.title if body else "Untitled page"
    return _public_conversation(db.create_conversation(title=title, user_id=user["id"]))


@app.get("/api/conversations/{conversation_id}")
def api_get_conversation(request: Request, conversation_id: str) -> dict:
    row = auth.owned_conversation(request, conversation_id)
    return {
        **_public_conversation(row),
        "messages": db.list_messages(conversation_id),
    }


@app.get("/api/conversations/{conversation_id}/messages")
def api_list_messages(request: Request, conversation_id: str) -> list[dict]:
    auth.owned_conversation(request, conversation_id)
    return db.list_messages(conversation_id)


@app.get("/api/conversations/{conversation_id}/leads")
def api_list_leads(request: Request, conversation_id: str) -> list[dict]:
    auth.owned_conversation(request, conversation_id)
    return db.list_leads(conversation_id)


@app.post("/api/pages/{slug}/leads")
def api_capture_lead(slug: str, body: LeadBody) -> dict:
    conversation = leads.published_conversation_for_slug(slug)
    if not conversation:
        raise HTTPException(status_code=404, detail="Page not found")
    cleaned, error = leads.validate_lead(body.name, body.email, body.phone)
    if error or not cleaned:
        raise HTTPException(status_code=400, detail=error or "Invalid lead")
    row = db.add_lead(
        conversation["id"],
        slug,
        cleaned["name"],
        cleaned["email"],
        cleaned["phone"],
    )
    next_url = intake.sanitize_next_url(str(conversation.get("next_url") or "")) or None
    return {
        "ok": True,
        "id": row["id"],
        "conversation_id": conversation["id"],
        "next_url": next_url,
    }


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
    auth.owned_conversation(request, conversation_id)
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
    conversation = db.get_conversation_by_slug(slug)
    if conversation and not billing.is_publicly_served(conversation):
        return None
    if conversation is None:
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
