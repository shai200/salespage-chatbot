from __future__ import annotations

from typing import Any

from studio import db, pages


def ensure_hosted(conversation: dict[str, Any]) -> dict[str, Any]:
    slug = conversation.get("slug")
    if not slug:
        raise RuntimeError("Conversation has no slug")
    site_dir = pages.promote_staged_site(slug)
    return (
        db.update_conversation(
            conversation["id"],
            site_path=str(site_dir),
            port=None,
            pid=None,
            status="published",
        )
        or conversation
    )


def respawn_all() -> None:
    return


def shutdown_all() -> None:
    return
