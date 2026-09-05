from __future__ import annotations

import json
import re
from typing import Any
from urllib.parse import urlparse

REQUIRED_LABELS = ("offer", "audience", "cta")
OPTIONAL_LABELS = ("next_url",)
ALL_LABELS = REQUIRED_LABELS + OPTIONAL_LABELS
LABEL_RE = re.compile(
    r"^\s*(offer|audience|cta|call[\s-]?to[\s-]?action|next[\s-]?url)\s*[:\-]\s*(.+)$",
    re.IGNORECASE | re.MULTILINE,
)
SEND_THEM_RE = re.compile(
    r"(?:send them to|send buyers to|after capture(?: go(?: to)?)?)\s+([^\s]+)",
    re.IGNORECASE,
)


def _normalize_label(raw: str) -> str:
    key = re.sub(r"[^a-z]", "", raw.lower())
    if key in {"cta", "calltoaction"}:
        return "cta"
    if key in {"nexturl"}:
        return "next_url"
    return key


def sanitize_next_url(value: str) -> str:
    raw = (value or "").strip()
    if not raw:
        return ""
    parsed = urlparse(raw)
    if parsed.scheme.lower() not in {"http", "https"} or not parsed.netloc:
        return ""
    return raw


def parse_labeled_fields(text: str) -> dict[str, str]:
    found: dict[str, str] = {}
    for match in LABEL_RE.finditer(text or ""):
        key = _normalize_label(match.group(1))
        value = match.group(2).strip()
        if key in ALL_LABELS and value:
            found[key] = value
    if "next_url" not in found:
        send = SEND_THEM_RE.search(text or "")
        if send:
            found["next_url"] = send.group(1).strip()
    if "next_url" in found:
        found["next_url"] = sanitize_next_url(found["next_url"])
    return found


def merge_intake(existing: dict[str, Any], incoming: dict[str, str]) -> dict[str, str]:
    merged = {
        "offer": (existing.get("offer") or "").strip(),
        "audience": (existing.get("audience") or "").strip(),
        "cta": (existing.get("cta") or "").strip(),
        "next_url": sanitize_next_url(str(existing.get("next_url") or "")),
    }
    for key in REQUIRED_LABELS:
        value = (incoming.get(key) or "").strip()
        if value:
            merged[key] = value
    if "next_url" in incoming:
        merged["next_url"] = sanitize_next_url(incoming.get("next_url") or "")
    return merged


def missing_fields(intake: dict[str, str]) -> list[str]:
    return [key for key in REQUIRED_LABELS if not (intake.get(key) or "").strip()]


def is_complete(intake: dict[str, str]) -> bool:
    return not missing_fields(intake)


def ask_for_missing(missing: list[str]) -> str:
    labels = {"offer": "the offer", "audience": "the audience", "cta": "a single call to action"}
    needed = ", ".join(labels[item] for item in missing)
    return (
        f"I can build this sales page once I have {needed}. "
        "Reply with lines like:\n"
        "Offer: …\n"
        "Audience: …\n"
        "CTA: …\n"
        "Next URL: https://…   (optional — where they go after the lead form)"
    )


def extract_with_pattern_or_llm(text: str, existing: dict[str, Any], llm_extract) -> dict[str, str]:
    merged = merge_intake(existing, parse_labeled_fields(text))
    if is_complete(merged) or llm_extract is None:
        return merged
    try:
        raw = llm_extract(text)
        parsed = raw if isinstance(raw, dict) else json.loads(raw)
        extracted = {key: str(parsed.get(key) or "").strip() for key in ALL_LABELS}
        return merge_intake(merged, extracted)
    except Exception:
        return merged
