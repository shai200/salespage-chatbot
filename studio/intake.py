from __future__ import annotations

import json
import re
from typing import Any

LABELS = ("offer", "audience", "cta")
LABEL_RE = re.compile(
    r"^\s*(offer|audience|cta|call[\s-]?to[\s-]?action)\s*[:\-]\s*(.+)$",
    re.IGNORECASE | re.MULTILINE,
)


def _normalize_label(raw: str) -> str:
    key = re.sub(r"[^a-z]", "", raw.lower())
    if key in {"cta", "calltoaction"}:
        return "cta"
    return key


def parse_labeled_fields(text: str) -> dict[str, str]:
    found: dict[str, str] = {}
    for match in LABEL_RE.finditer(text or ""):
        key = _normalize_label(match.group(1))
        value = match.group(2).strip()
        if key in LABELS and value:
            found[key] = value
    return found


def merge_intake(existing: dict[str, Any], incoming: dict[str, str]) -> dict[str, str]:
    merged = {
        "offer": (existing.get("offer") or "").strip(),
        "audience": (existing.get("audience") or "").strip(),
        "cta": (existing.get("cta") or "").strip(),
    }
    for key in LABELS:
        value = (incoming.get(key) or "").strip()
        if value:
            merged[key] = value
    return merged


def missing_fields(intake: dict[str, str]) -> list[str]:
    return [key for key in LABELS if not (intake.get(key) or "").strip()]


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
        "CTA: …"
    )


def extract_with_pattern_or_llm(text: str, existing: dict[str, Any], llm_extract) -> dict[str, str]:
    merged = merge_intake(existing, parse_labeled_fields(text))
    if is_complete(merged) or llm_extract is None:
        return merged
    try:
        raw = llm_extract(text)
        parsed = raw if isinstance(raw, dict) else json.loads(raw)
        extracted = {
            key: str(parsed.get(key) or "").strip()
            for key in LABELS
        }
        return merge_intake(merged, extracted)
    except Exception:
        return merged
