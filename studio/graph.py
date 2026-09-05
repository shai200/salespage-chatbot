from __future__ import annotations

import base64
import json
import os
import re
import shutil
import sqlite3
from typing import Any, TypedDict

import httpx
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph import END, START, StateGraph

from studio import config, db, intake, llm, pages, publisher


class StudioState(TypedDict, total=False):
    conversation_id: str
    user_message: str
    assistant_message: str
    offer: str
    audience: str
    cta: str
    intake_complete: bool
    copy: dict
    visuals: dict
    slug: str
    port: int
    preview_url: str
    error: str
    stages_run: list
    skip_visual: bool
    images_pending: bool


_checkpointer: SqliteSaver | None = None
_checkpoint_conn: sqlite3.Connection | None = None
_graph = None

STAGE_INFO = {
    "intake": {
        "label": "Reading the brief",
        "detail": "Checking offer, audience, and CTA",
        "short": "Reading",
    },
    "copywriter": {
        "label": "Writing the page copy",
        "detail": "Headline, sections, proof, and CTA",
        "short": "Writing",
    },
    "visual": {
        "label": "Generating the hero image",
        "detail": "This can take a moment",
        "short": "Imaging",
    },
    "page_engineer": {
        "label": "Building the page",
        "detail": "Assembling React and HTML",
        "short": "Building",
    },
    "publisher": {
        "label": "Publishing the preview",
        "detail": "Starting the local server",
        "short": "Publishing",
    },
}


def stage_progress(name: str, state: StudioState | None = None) -> dict[str, str]:
    if name == "visual" and state and state.get("skip_visual"):
        return {
            "stage": "visual",
            "label": "Keeping existing visuals",
            "detail": "Copy-only change — skipping image generation",
            "short": "Updating",
        }
    info = STAGE_INFO.get(name) or {
        "label": "Working",
        "detail": "",
        "short": "Working",
    }
    return {"stage": name, **info}


def next_stage(completed: str, state: StudioState) -> str | None:
    if completed == "intake":
        if state.get("error") or not state.get("intake_complete"):
            return None
        return "copywriter"
    if completed == "copywriter":
        if state.get("error"):
            return None
        return "visual"
    if completed == "visual":
        return "page_engineer"
    if completed == "page_engineer":
        return "publisher"
    return None


def _copy_only_follow_up(message: str, has_page: bool) -> bool:
    if not has_page:
        return False
    text = (message or "").lower()
    # Asking for images must never skip the visual node.
    if re.search(r"\b(image|images|visual|visuals|photo|photos|picture|placeholder)\b", text):
        return False
    return bool(
        re.search(
            r"\b(headline|copy|wording|punchier|rewrite|text|cta|subhead)\b",
            text,
        )
    )


def _append_stage(state: StudioState, name: str) -> list[str]:
    stages = list(state.get("stages_run") or [])
    stages.append(name)
    return stages


def intake_node(state: StudioState) -> dict[str, Any]:
    conversation = db.get_conversation(state["conversation_id"]) or {}
    existing = {
        "offer": conversation.get("offer") or state.get("offer") or "",
        "audience": conversation.get("audience") or state.get("audience") or "",
        "cta": conversation.get("cta") or state.get("cta") or "",
    }
    llm_extract = None
    if config.OPENROUTER_API_KEY and not config.STUDIO_FAKE_LLM:
        llm_extract = llm.extract_intake_fields
    merged = intake.extract_with_pattern_or_llm(
        state.get("user_message") or "",
        existing,
        llm_extract,
    )
    db.update_conversation(state["conversation_id"], **merged)
    if merged["offer"] and (not conversation.get("title") or conversation.get("title") == "Untitled page"):
        db.update_conversation(state["conversation_id"], title=merged["offer"][:80])

    if not intake.is_complete(merged):
        return {
            **merged,
            "intake_complete": False,
            "assistant_message": intake.ask_for_missing(intake.missing_fields(merged)),
            "stages_run": _append_stage(state, "intake"),
        }
    return {
        **merged,
        "intake_complete": True,
        "stages_run": _append_stage(state, "intake"),
    }


def copywriter_node(state: StudioState) -> dict[str, Any]:
    try:
        copy = llm.write_page_copy(
            offer=state.get("offer") or "",
            audience=state.get("audience") or "",
            cta=state.get("cta") or "",
            user_message=state.get("user_message") or "",
            previous=state.get("copy"),
        )
    except llm.GatewayError as exc:
        return {
            "error": str(exc),
            "assistant_message": str(exc),
            "stages_run": _append_stage(state, "copywriter"),
        }
    if not copy or not copy.get("headline"):
        message = "Copy stage returned empty copy. No page was published."
        return {
            "error": message,
            "assistant_message": message,
            "stages_run": _append_stage(state, "copywriter"),
        }
    return {"copy": copy, "stages_run": _append_stage(state, "copywriter")}


def _placeholder_visuals(note: str | None = None) -> dict[str, Any]:
    return {
        "provider": None,
        "images_pending": True,
        "hero": {"type": "placeholder", "label": "Hero visual pending"},
        "note": note
        or "Images are pending — the page uses placeholders.",
    }


def _hero_image_prompt(state: StudioState) -> str:
    copy = state.get("copy") or {}
    offer = state.get("offer") or "a product"
    audience = state.get("audience") or "buyers"
    headline = copy.get("headline") or offer
    return (
        f"Editorial hero photograph for a sales page. Offer: {offer}. "
        f"Audience: {audience}. Headline: {headline}. "
        "Clean, high-end, no text overlay, no logos."
    )


def fetch_openrouter_images(prompt: str) -> list[bytes]:
    if config.STUDIO_FAKE_LLM:
        raise RuntimeError("image generation skipped in fake-llm mode")
    api_key = os.environ.get("OPENROUTER_API_KEY") or config.OPENROUTER_API_KEY
    if not api_key:
        raise RuntimeError("OPENROUTER_API_KEY is not configured")
    model = os.environ.get("OPENROUTER_IMAGE_MODEL") or config.OPENROUTER_IMAGE_MODEL
    url = f"{config.OPENROUTER_BASE_URL.rstrip('/')}/images"
    response = httpx.post(
        url,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        content=json.dumps({"model": model, "prompt": prompt}),
        timeout=90,
    )
    response.raise_for_status()
    payload = response.json()
    images = []
    for image in payload.get("data") or []:
        encoded = image.get("b64_json")
        if encoded:
            images.append(base64.b64decode(encoded))
    if not images:
        raise RuntimeError("OpenRouter image API returned no images")
    return images


def visual_node(state: StudioState) -> dict[str, Any]:
    if state.get("skip_visual") and state.get("visuals"):
        return {"stages_run": _append_stage(state, "visual")}

    conversation = db.get_conversation(state["conversation_id"]) or {}
    slug = conversation.get("slug") or state.get("slug")
    if not slug:
        slug = pages.unique_slug(state.get("offer") or "sales-page", state["conversation_id"])
    site_dir = pages.staging_site_dir(slug)
    db.update_conversation(state["conversation_id"], slug=slug)

    visuals = _placeholder_visuals()
    try:
        images = fetch_openrouter_images(_hero_image_prompt(state))
        site_dir.mkdir(parents=True, exist_ok=True)
        dest = site_dir / "hero.png"
        dest.write_bytes(images[0])
        visuals = {
            "provider": "openrouter",
            "images_pending": False,
            "hero": {"type": "image", "src": "hero.png", "label": "Hero"},
            "note": "",
        }
    except Exception as exc:
        visuals = _placeholder_visuals(
            f"Images are pending — OpenRouter image request failed ({exc})."
        )

    pending = bool(visuals.get("images_pending"))
    db.update_conversation(state["conversation_id"], slug=slug, images_pending=pending)
    return {
        "visuals": visuals,
        "slug": slug,
        "images_pending": pending,
        "stages_run": _append_stage(state, "visual"),
    }


def page_engineer_node(state: StudioState) -> dict[str, Any]:
    conversation = db.get_conversation(state["conversation_id"]) or {}
    slug = conversation.get("slug") or state.get("slug")
    if not slug:
        slug = pages.unique_slug(state.get("offer") or "sales-page", state["conversation_id"])
    site_dir = pages.staging_site_dir(slug)
    live = pages.live_site_dir(slug)
    hero = live / "hero.png"
    if hero.exists():
        site_dir.mkdir(parents=True, exist_ok=True)
        shutil.copy2(hero, site_dir / "hero.png")
    page_data = pages.page_data_from_copy(
        state.get("copy") or {},
        state.get("visuals") or {},
        {
            "offer": state.get("offer") or "",
            "audience": state.get("audience") or "",
            "cta": state.get("cta") or "",
        },
        user_message=state.get("user_message") or "",
    )
    pages.write_site(site_dir, page_data)
    db.update_conversation(
        state["conversation_id"],
        slug=slug,
        status="built",
    )
    return {"slug": slug, "stages_run": _append_stage(state, "page_engineer")}


def publisher_node(state: StudioState) -> dict[str, Any]:
    conversation = db.get_conversation(state["conversation_id"])
    if not conversation:
        return {"error": "Conversation disappeared before publish."}
    try:
        hosted = publisher.ensure_hosted(conversation)
    except Exception as exc:
        return {
            "error": str(exc),
            "assistant_message": str(exc),
            "stages_run": _append_stage(state, "publisher"),
        }
    hosted = hosted or conversation
    url = config.preview_url(port=hosted.get("port"), slug=hosted.get("slug") or state.get("slug") or "")
    note = ""
    visuals = state.get("visuals") or {}
    if visuals.get("images_pending"):
        note = f"\n\n{visuals.get('note') or 'Images are pending — the page uses placeholders.'}"
    message = (
        f"Your sales page is live:\n{url}\n\n"
        "Open that link in a new tab, or use the preview pane."
        f"{note}"
    )
    return {
        "port": hosted["port"],
        "preview_url": url,
        "assistant_message": message,
        "stages_run": _append_stage(state, "publisher"),
    }


def route_after_intake(state: StudioState) -> str:
    if state.get("error") or not state.get("intake_complete"):
        return END
    return "copywriter"


def route_after_copy(state: StudioState) -> str:
    if state.get("error"):
        return END
    return "visual"


def build_graph(checkpointer: SqliteSaver | None = None):
    builder = StateGraph(StudioState)
    builder.add_node("intake", intake_node)
    builder.add_node("copywriter", copywriter_node)
    builder.add_node("visual", visual_node)
    builder.add_node("page_engineer", page_engineer_node)
    builder.add_node("publisher", publisher_node)
    builder.add_edge(START, "intake")
    builder.add_conditional_edges("intake", route_after_intake)
    builder.add_conditional_edges("copywriter", route_after_copy)
    builder.add_edge("visual", "page_engineer")
    builder.add_edge("page_engineer", "publisher")
    builder.add_edge("publisher", END)
    return builder.compile(checkpointer=checkpointer)


def get_checkpointer() -> SqliteSaver:
    global _checkpointer, _checkpoint_conn
    if _checkpointer is None:
        config.DATA_DIR.mkdir(parents=True, exist_ok=True)
        _checkpoint_conn = sqlite3.connect(str(config.DB_PATH), check_same_thread=False)
        _checkpointer = SqliteSaver(_checkpoint_conn)
        _checkpointer.setup()
    return _checkpointer


def get_graph():
    global _graph
    if _graph is None:
        _graph = build_graph(get_checkpointer())
    return _graph


def reset_runtime() -> None:
    global _graph, _checkpointer, _checkpoint_conn
    if _checkpoint_conn is not None:
        try:
            _checkpoint_conn.close()
        except Exception:
            pass
    _checkpointer = None
    _checkpoint_conn = None
    _graph = None


def _turn_payload(conversation_id: str, user_message: str) -> tuple[StudioState, dict[str, Any]]:
    conversation = db.get_conversation(conversation_id) or {}
    compiled = get_graph()
    thread = {"configurable": {"thread_id": conversation_id}}
    previous: dict[str, Any] = {}
    try:
        snapshot = compiled.get_state(thread)
        if snapshot and snapshot.values:
            previous = dict(snapshot.values)
    except Exception:
        previous = {}

    payload: StudioState = {
        "conversation_id": conversation_id,
        "user_message": user_message,
        "offer": conversation.get("offer") or previous.get("offer") or "",
        "audience": conversation.get("audience") or previous.get("audience") or "",
        "cta": conversation.get("cta") or previous.get("cta") or "",
        "copy": previous.get("copy"),
        "visuals": previous.get("visuals"),
        "slug": conversation.get("slug") or previous.get("slug") or "",
        "port": conversation.get("port") or previous.get("port"),
        "preview_url": previous.get("preview_url") or "",
        "stages_run": [],
        "skip_visual": _copy_only_follow_up(user_message, bool(conversation.get("site_path"))),
        "error": "",
        "assistant_message": "",
    }
    return payload, thread


def iter_turn_events(conversation_id: str, user_message: str):
    payload, thread = _turn_payload(conversation_id, user_message)
    compiled = get_graph()
    yield {"type": "progress", **stage_progress("intake", payload)}
    last: dict[str, Any] = dict(payload)
    for chunk in compiled.stream(payload, thread, stream_mode="updates"):
        if not chunk:
            continue
        node = next(iter(chunk))
        update = chunk[node] or {}
        last.update(update)
        following = next_stage(node, last)
        if following:
            yield {"type": "progress", **stage_progress(following, last)}
    yield {"type": "result", "state": last}


def run_turn(conversation_id: str, user_message: str) -> StudioState:
    result: StudioState = {}
    for event in iter_turn_events(conversation_id, user_message):
        if event.get("type") == "result":
            result = event.get("state") or {}
    return result
