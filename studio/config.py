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
RESERVED_SLUGS = frozenset({"api", "assets", "health", "static"})

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "").strip()
OPENROUTER_BASE_URL = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1").strip()
OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "openai/gpt-4o-mini").strip()
OPENROUTER_IMAGE_MODEL = os.getenv("OPENROUTER_IMAGE_MODEL", "meta/muse-image").strip()
STUDIO_FAKE_LLM = os.getenv("STUDIO_FAKE_LLM", "").strip() in {"1", "true", "yes"}


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
