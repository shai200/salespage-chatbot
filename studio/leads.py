from __future__ import annotations

import re
from typing import Any

from studio import billing, db

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
PHONE_OK_RE = re.compile(r"^[\d\s+\-().]+$")


def validate_lead(name: str, email: str, phone: str) -> tuple[dict[str, str] | None, str | None]:
    name = (name or "").strip()
    email = (email or "").strip()
    phone = (phone or "").strip()
    if not name or not email or not phone:
        return None, "Name, email, and phone are required."
    if not EMAIL_RE.match(email):
        return None, "Email looks invalid."
    if not PHONE_OK_RE.match(phone) or len(re.sub(r"\D", "", phone)) < 7:
        return None, "Phone looks invalid."
    return {"name": name, "email": email, "phone": phone}, None


def published_conversation_for_slug(slug: str) -> dict[str, Any] | None:
    row = db.get_conversation_by_slug(slug)
    if not row or not row.get("site_path"):
        return None
    if not billing.is_publicly_served(row):
        return None
    return row
