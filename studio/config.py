from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")

DATA_DIR = ROOT / "data"
SITES_DIR = ROOT / "sites"
DB_PATH = DATA_DIR / "studio.sqlite"
WEB_DIST = ROOT / "web" / "dist"
PAGEKIT_DIR = ROOT / "pagekit"

STUDIO_HOST = os.getenv("STUDIO_HOST", "127.0.0.1").strip() or "127.0.0.1"
STUDIO_PORT = int(os.getenv("STUDIO_PORT", "8080") or "8080")
PAGE_PORT_START = 3000
PUBLISH_MODE = os.getenv("PUBLISH_MODE", "local").strip().lower() or "local"
PUBLIC_BASE_URL = os.getenv("PUBLIC_BASE_URL", "").strip().rstrip("/")
PAGE_RSYNC_TARGET = os.getenv("PAGE_RSYNC_TARGET", "").strip()
PAGE_SSH_KEY = os.getenv("PAGE_SSH_KEY", "").strip()
SERVE_SITES = os.getenv("SERVE_SITES", "1").strip() not in {"0", "false", "no"}
RESERVED_SLUGS = frozenset(
    {"api", "assets", "health", "static", "auth", "login", "billing"}
)
FREE_PAGE_LIMIT = int(os.getenv("FREE_PAGE_LIMIT", "3") or "3")
BILLING_GRACE_DAYS = int(os.getenv("BILLING_GRACE_DAYS", "7") or "7")

GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "").strip()
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET", "").strip()
SESSION_SECRET = os.getenv("SESSION_SECRET", "").strip()
HOMERUN_LEGACY_OWNER_EMAIL = os.getenv("HOMERUN_LEGACY_OWNER_EMAIL", "").strip().lower()
STUDIO_FAKE_AUTH = os.getenv("STUDIO_FAKE_AUTH", "").strip() in {"1", "true", "yes"}

STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY", "").strip()
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET", "").strip()
STRIPE_PAGE_ANNUAL_PRICE_ID = os.getenv("STRIPE_PAGE_ANNUAL_PRICE_ID", "").strip()

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "").strip()
OPENROUTER_BASE_URL = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1").strip()
OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "openai/gpt-4o-mini").strip()
OPENROUTER_IMAGE_MODEL = os.getenv("OPENROUTER_IMAGE_MODEL", "meta/muse-image").strip()
STUDIO_FAKE_LLM = os.getenv("STUDIO_FAKE_LLM", "").strip() in {"1", "true", "yes"}
COPY_MIN_WORDS = int(os.getenv("COPY_MIN_WORDS", "2100") or "2100")


def session_secret() -> str:
    if SESSION_SECRET:
        return SESSION_SECRET
    if STUDIO_FAKE_AUTH:
        return "studio-fake-session-secret"
    return ""


def google_oauth_ready() -> bool:
    return bool(GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET)


def cookie_secure() -> bool:
    return public_origin().startswith("https://")


def missing_api_key_message() -> str:
    return (
        "OPENROUTER_API_KEY is not configured. "
        "Add it to your local .env file and restart the studio. "
        "No page was published."
    )


def is_static_publish() -> bool:
    return True


def public_origin() -> str:
    if PUBLIC_BASE_URL:
        return PUBLIC_BASE_URL
    return f"http://localhost:{STUDIO_PORT}"


def preview_url(port: int | None = None, slug: str = "") -> str | None:
    if slug:
        return f"{public_origin()}/{slug}/"
    return None
