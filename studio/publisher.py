from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any

from studio import billing, config, db, pages


def _ssh_command() -> str:
    parts = ["ssh", "-o", "BatchMode=yes", "-o", "StrictHostKeyChecking=accept-new"]
    if config.PAGE_SSH_KEY:
        parts.extend(["-i", config.PAGE_SSH_KEY])
    return " ".join(parts)


def sync_site(slug: str, site_dir: Path) -> None:
    target = config.PAGE_RSYNC_TARGET
    if not target:
        return
    if not (site_dir / "index.html").is_file():
        raise RuntimeError(f"Cannot copy {slug}: index.html is missing")
    dest = f"{target.rstrip('/')}/{slug}/"
    command = [
        "rsync",
        "-az",
        "--delete",
        "-e",
        _ssh_command(),
        f"{site_dir}/",
        dest,
    ]
    result = subprocess.run(command, check=False, capture_output=True, text=True)
    if result.returncode != 0:
        detail = (result.stderr or result.stdout or "rsync failed").strip()
        raise RuntimeError(f"Page copy to VPS failed: {detail}")


def ensure_hosted(conversation: dict[str, Any]) -> dict[str, Any]:
    slug = conversation.get("slug")
    if not slug:
        raise RuntimeError("Conversation has no slug")
    site_dir = pages.promote_staged_site(slug)
    db.update_conversation(
        conversation["id"],
        site_path=str(site_dir),
        port=None,
        pid=None,
        status="built",
    )
    sync_site(slug, site_dir)
    published = (
        db.update_conversation(
            conversation["id"],
            site_path=str(site_dir),
            port=None,
            pid=None,
            status="published",
        )
        or conversation
    )
    billing.ensure_extra_subscription(published)
    return published


def respawn_all() -> None:
    return


def shutdown_all() -> None:
    return
