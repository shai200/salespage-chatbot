from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from studio import config


def utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


def connect() -> sqlite3.Connection:
    config.DATA_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(config.DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init() -> None:
    conn = connect()
    try:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS conversations (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                slug TEXT,
                port INTEGER,
                site_path TEXT,
                pid INTEGER,
                status TEXT NOT NULL DEFAULT 'draft',
                offer TEXT,
                audience TEXT,
                cta TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS messages (
                id TEXT PRIMARY KEY,
                conversation_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY (conversation_id) REFERENCES conversations(id)
            );
            """
        )
        conn.commit()
    finally:
        conn.close()


def create_conversation(title: str = "New sales page") -> dict[str, Any]:
    now = utcnow()
    row = {
        "id": str(uuid4()),
        "title": title,
        "slug": None,
        "port": None,
        "site_path": None,
        "pid": None,
        "status": "draft",
        "offer": None,
        "audience": None,
        "cta": None,
        "created_at": now,
        "updated_at": now,
    }
    conn = connect()
    try:
        conn.execute(
            """
            INSERT INTO conversations (
                id, title, slug, port, site_path, pid, status,
                offer, audience, cta, created_at, updated_at
            ) VALUES (
                :id, :title, :slug, :port, :site_path, :pid, :status,
                :offer, :audience, :cta, :created_at, :updated_at
            )
            """,
            row,
        )
        conn.commit()
    finally:
        conn.close()
    return row


def get_conversation(conversation_id: str) -> dict[str, Any] | None:
    conn = connect()
    try:
        row = conn.execute(
            "SELECT * FROM conversations WHERE id = ?", (conversation_id,)
        ).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def list_conversations() -> list[dict[str, Any]]:
    conn = connect()
    try:
        rows = conn.execute(
            "SELECT * FROM conversations ORDER BY updated_at DESC"
        ).fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


def list_published() -> list[dict[str, Any]]:
    conn = connect()
    try:
        rows = conn.execute(
            """
            SELECT * FROM conversations
            WHERE site_path IS NOT NULL AND port IS NOT NULL
            ORDER BY port ASC
            """
        ).fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


def update_conversation(conversation_id: str, **fields: Any) -> dict[str, Any] | None:
    allowed = {
        "title",
        "slug",
        "port",
        "site_path",
        "pid",
        "status",
        "offer",
        "audience",
        "cta",
    }
    updates = {key: value for key, value in fields.items() if key in allowed}
    if not updates:
        return get_conversation(conversation_id)
    updates["updated_at"] = utcnow()
    assignments = ", ".join(f"{key} = :{key}" for key in updates)
    updates["id"] = conversation_id
    conn = connect()
    try:
        conn.execute(
            f"UPDATE conversations SET {assignments} WHERE id = :id",
            updates,
        )
        conn.commit()
    finally:
        conn.close()
    return get_conversation(conversation_id)


def add_message(conversation_id: str, role: str, content: str) -> dict[str, Any]:
    row = {
        "id": str(uuid4()),
        "conversation_id": conversation_id,
        "role": role,
        "content": content,
        "created_at": utcnow(),
    }
    conn = connect()
    try:
        conn.execute(
            """
            INSERT INTO messages (id, conversation_id, role, content, created_at)
            VALUES (:id, :conversation_id, :role, :content, :created_at)
            """,
            row,
        )
        conn.execute(
            "UPDATE conversations SET updated_at = ? WHERE id = ?",
            (row["created_at"], conversation_id),
        )
        conn.commit()
    finally:
        conn.close()
    return row


def list_messages(conversation_id: str) -> list[dict[str, Any]]:
    conn = connect()
    try:
        rows = conn.execute(
            """
            SELECT * FROM messages
            WHERE conversation_id = ?
            ORDER BY created_at ASC
            """,
            (conversation_id,),
        ).fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


def conversation_site_dir(slug: str) -> Path:
    return config.SITES_DIR / slug
