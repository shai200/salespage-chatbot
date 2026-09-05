from __future__ import annotations

import os
import signal
import socket
import subprocess
from pathlib import Path
from typing import Any

from studio import config
from studio import db

_processes: dict[str, subprocess.Popen] = {}


def port_is_free(port: int, host: str = "127.0.0.1") -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            sock.bind((host, port))
        except OSError:
            return False
    return True


def pid_is_alive(pid: int | None) -> bool:
    if not pid:
        return False
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    return True


def allocate_port(preferred: int | None = None) -> int:
    if preferred and preferred != config.STUDIO_PORT and port_is_free(preferred):
        return preferred
    port = config.PAGE_PORT_START
    while True:
        if port != config.STUDIO_PORT and port_is_free(port):
            return port
        port += 1
        if port > 3999:
            raise RuntimeError("No free local port available for a sales page")


def spawn(site_dir: Path, port: int) -> int:
    site_dir = Path(site_dir)
    if not (site_dir / "index.html").exists():
        raise RuntimeError(f"Cannot host {site_dir}: index.html is missing")
    process = subprocess.Popen(
        ["node", str(config.PAGEKIT_DIR / "serve.mjs"), str(site_dir), str(port)],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
    )
    _processes[str(site_dir)] = process
    return process.pid


def ensure_hosted(conversation: dict[str, Any]) -> dict[str, Any]:
    site_path = conversation.get("site_path")
    if not site_path:
        raise RuntimeError("Conversation has no site path")
    site_dir = Path(site_path)
    preferred = conversation.get("port")
    if preferred and not port_is_free(preferred):
        return (
            db.update_conversation(
                conversation["id"],
                port=preferred,
                pid=conversation.get("pid"),
                status="published",
            )
            or conversation
        )
    port = allocate_port(preferred)
    pid = spawn(site_dir, port)
    return (
        db.update_conversation(
            conversation["id"],
            port=port,
            pid=pid,
            site_path=str(site_dir),
            status="published",
        )
        or conversation
    )


def respawn_all() -> None:
    for conversation in db.list_published():
        port = conversation.get("port")
        site_path = conversation.get("site_path")
        if not port or not site_path:
            continue
        site_dir = Path(site_path)
        if not site_dir.exists():
            continue
        if not port_is_free(port):
            continue
        try:
            pid = spawn(site_dir, port)
            db.update_conversation(conversation["id"], pid=pid, status="published")
        except Exception:
            new_port = allocate_port()
            pid = spawn(site_dir, new_port)
            db.update_conversation(
                conversation["id"],
                port=new_port,
                pid=pid,
                status="published",
            )


def shutdown_all() -> None:
    for process in list(_processes.values()):
        if process.poll() is None:
            try:
                os.killpg(process.pid, signal.SIGTERM)
            except OSError:
                process.terminate()
    _processes.clear()
