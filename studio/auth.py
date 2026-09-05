from __future__ import annotations

from typing import Any

from fastapi import HTTPException, Request
from starlette.middleware.sessions import SessionMiddleware

from studio import config, db

try:
    from authlib.integrations.starlette_client import OAuth
except ImportError:  # pragma: no cover
    OAuth = None

_oauth = None


def get_oauth():
    global _oauth
    if _oauth is not None:
        return _oauth
    if OAuth is None or not config.google_oauth_ready():
        return None
    _oauth = OAuth()
    _oauth.register(
        name="google",
        client_id=config.GOOGLE_CLIENT_ID,
        client_secret=config.GOOGLE_CLIENT_SECRET,
        server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
        client_kwargs={"scope": "openid email profile"},
    )
    return _oauth


def attach_session(app) -> None:
    secret = config.session_secret()
    if not secret:
        secret = "studio-missing-session-secret"
    app.add_middleware(
        SessionMiddleware,
        secret_key=secret,
        same_site="lax",
        https_only=config.cookie_secure(),
    )


def public_user(row: dict[str, Any] | None) -> dict[str, Any] | None:
    if not row:
        return None
    return {
        "id": row["id"],
        "email": row.get("email"),
        "name": row.get("name") or row.get("email"),
    }


def current_user(request: Request) -> dict[str, Any] | None:
    user_id = request.session.get("user_id")
    if not user_id:
        return None
    return db.get_user(str(user_id))


def require_user(request: Request) -> dict[str, Any]:
    user = current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Sign in required")
    return user


def owned_conversation(request: Request, conversation_id: str) -> dict[str, Any]:
    user = require_user(request)
    row = db.get_conversation(conversation_id)
    if not row or row.get("user_id") != user["id"]:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return row


def login_google_profile(request: Request, profile: dict[str, Any]) -> dict[str, Any]:
    sub = str(profile.get("sub") or "").strip()
    email = str(profile.get("email") or "").strip()
    name = str(profile.get("name") or email).strip()
    if not sub or not email:
        raise HTTPException(status_code=400, detail="Google profile is incomplete")
    user = db.upsert_user(sub, email, name)
    if email.lower() == config.HOMERUN_LEGACY_OWNER_EMAIL:
        db.claim_unowned_conversations(user["id"])
    request.session["user_id"] = user["id"]
    return user


def logout(request: Request) -> None:
    request.session.clear()
