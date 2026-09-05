from __future__ import annotations

import json
import re
from typing import Any

from studio import config

SAMPLE_COPY = {
    "headline": "Ship a sales page before the meeting ends",
    "headline_accent": "before the meeting ends",
    "subheadline": "Turn a rough offer into a clear landing page your buyer can say yes to.",
    "problem": {
        "title": "Most offers die in a Google Doc",
        "body": (
            "Your product is clear in your head and messy on the page. "
            "Prospects bounce before they understand the outcome or the next step."
        ),
    },
    "benefits": [
        {"title": "One offer, one page", "body": "A single conversation becomes a single sales page."},
        {"title": "Editorial, not dashboard", "body": "Hero, proof, offer, and CTA — not an app shell."},
        {"title": "Local preview now", "body": "Open localhost and send the link while the idea is hot."},
    ],
    "proof": [
        {
            "quote": "I stopped rewriting the same landing page from scratch every week.",
            "name": "Founder, B2B workshop",
        }
    ],
    "offer": {
        "title": "A complete sales page",
        "body": "Copy, structure, and a live local URL you can iterate in chat.",
        "price": "Local studio",
    },
    "faq": [
        {"q": "Do I need a designer?", "a": "No. The page uses a fixed editorial kit."},
        {"q": "Can I change the headline?", "a": "Yes. Follow up in the same conversation."},
    ],
    "cta": {"label": "Book a walkthrough", "text": "Ready to put this offer in front of buyers?"},
    "footer": "Generated locally by Sales Page Studio.",
}


class GatewayError(RuntimeError):
    pass


def require_api_key() -> str:
    if config.STUDIO_FAKE_LLM:
        return "fake"
    key = config.OPENROUTER_API_KEY
    if not key:
        raise GatewayError(config.missing_api_key_message())
    return key


def _chat_model():
    from langchain_openai import ChatOpenAI

    key = require_api_key()
    return ChatOpenAI(
        model=config.OPENROUTER_MODEL,
        api_key=key,
        base_url=config.OPENROUTER_BASE_URL,
        temperature=0.4,
        timeout=60,
        max_retries=1,
        default_headers={
            "HTTP-Referer": "http://localhost:8080",
            "X-Title": "Sales Page Studio",
        },
    )


def _parse_json_object(text: str) -> dict[str, Any]:
    text = (text or "").strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    return json.loads(text)


def extract_intake_fields(user_message: str) -> dict[str, str]:
    if config.STUDIO_FAKE_LLM:
        return {}
    require_api_key()
    prompt = (
        "Extract sales-page intake fields from the operator message. "
        "Return JSON with keys offer, audience, cta. Use empty strings if unknown.\n\n"
        f"Message:\n{user_message}"
    )
    response = _chat_model().invoke(prompt)
    parsed = _parse_json_object(str(response.content))
    return {
        "offer": str(parsed.get("offer") or "").strip(),
        "audience": str(parsed.get("audience") or "").strip(),
        "cta": str(parsed.get("cta") or "").strip(),
    }


def write_page_copy(offer: str, audience: str, cta: str, user_message: str, previous: dict | None) -> dict[str, Any]:
    if config.STUDIO_FAKE_LLM:
        copy = dict(SAMPLE_COPY)
        copy["headline"] = offer or copy["headline"]
        copy["cta"] = {"label": cta or copy["cta"]["label"], "text": copy["cta"]["text"]}
        if previous:
            copy = {**previous, **copy}
        if "headline" in user_message.lower() and previous:
            copy = dict(previous)
            copy["headline"] = f"{previous.get('headline', offer)} — sharper"
        return copy

    require_api_key()
    previous_json = json.dumps(previous or {}, ensure_ascii=False)
    prompt = f"""You write landing-page copy for a local sales-page studio.
Return ONLY JSON with this shape:
{{
  "headline": string,
  "headline_accent": string (a short phrase that appears inside the headline),
  "subheadline": string,
  "problem": {{"title": string, "body": string}},
  "benefits": [{{"title": string, "body": string}}, {{"title": string, "body": string}}, {{"title": string, "body": string}}],
  "proof": [{{"quote": string, "name": string}}],
  "offer": {{"title": string, "body": string, "price": string}},
  "faq": [{{"q": string, "a": string}}, {{"q": string, "a": string}}],
  "cta": {{"label": string, "text": string}},
  "footer": string
}}

Offer: {offer}
Audience: {audience}
Call to action: {cta}
Operator request: {user_message}
Previous copy JSON (may be empty): {previous_json}

If the operator asked only to change copy, keep structure and update the requested lines.
Use a white-page editorial voice. Do not mention being an AI.
"""
    try:
        response = _chat_model().invoke(prompt)
        parsed = _parse_json_object(str(response.content))
    except GatewayError:
        raise
    except Exception as exc:
        raise GatewayError(f"OpenRouter gateway error: {exc}. No page was published.") from exc

    if not parsed.get("headline"):
        raise GatewayError("Copy stage returned empty copy. No page was published.")
    parsed.setdefault("cta", {"label": cta, "text": f"Ready? {cta}"})
    return parsed
