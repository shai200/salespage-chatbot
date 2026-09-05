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

STUDIO_HOST = "127.0.0.1"
STUDIO_PORT = 8080
PAGE_PORT_START = 3000

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "").strip()
OPENROUTER_BASE_URL = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1").strip()
OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "openai/gpt-4o-mini").strip()
STUDIO_FAKE_LLM = os.getenv("STUDIO_FAKE_LLM", "").strip() in {"1", "true", "yes"}


def missing_api_key_message() -> str:
    return (
        "OPENROUTER_API_KEY is not configured. "
        "Add it to your local .env file and restart the studio. "
        "No page was published."
    )


def preview_url(port: int) -> str:
    return f"http://localhost:{port}/"
