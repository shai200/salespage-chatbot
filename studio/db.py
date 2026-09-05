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
                images_pending INTEGER NOT NULL DEFAULT 0,
                next_url TEXT,
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

            CREATE TABLE IF NOT EXISTS leads (
                id TEXT PRIMARY KEY,
                conversation_id TEXT NOT NULL,
                slug TEXT,
                name TEXT NOT NULL,
                email TEXT NOT NULL,
                phone TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY (conversation_id) REFERENCES conversations(id)
            );

            CREATE TABLE IF NOT EXISTS users (
                id TEXT PRIMARY KEY,
                google_sub TEXT NOT NULL UNIQUE,
                email TEXT NOT NULL,
                name TEXT,
                stripe_customer_id TEXT,
                payment_method_ok INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS page_subscriptions (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                conversation_id TEXT NOT NULL UNIQUE,
                stripe_subscription_id TEXT,
                status TEXT NOT NULL DEFAULT 'trialing',
                trial_end TEXT,
                grace_started_at TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users(id),
                FOREIGN KEY (conversation_id) REFERENCES conversations(id)
            );
            """
        )
        columns = {
            row[1] for row in conn.execute("PRAGMA table_info(conversations)").fetchall()
        }
        if "images_pending" not in columns:
            conn.execute(
                "ALTER TABLE conversations ADD COLUMN images_pending INTEGER NOT NULL DEFAULT 0"
            )
        if "next_url" not in columns:
            conn.execute("ALTER TABLE conversations ADD COLUMN next_url TEXT")
        if "user_id" not in columns:
            conn.execute("ALTER TABLE conversations ADD COLUMN user_id TEXT")
        conn.commit()
    finally:
        conn.close()


def create_conversation(title: str = "Untitled page", user_id: str | None = None) -> dict[str, Any]:
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
        "images_pending": 0,
        "next_url": None,
        "user_id": user_id,
        "created_at": now,
        "updated_at": now,
    }
    conn = connect()
    try:
        conn.execute(
            """
            INSERT INTO conversations (
                id, title, slug, port, site_path, pid, status,
                offer, audience, cta, images_pending, next_url, user_id,
                created_at, updated_at
            ) VALUES (
                :id, :title, :slug, :port, :site_path, :pid, :status,
                :offer, :audience, :cta, :images_pending, :next_url, :user_id,
                :created_at, :updated_at
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


def list_conversations(user_id: str | None = None) -> list[dict[str, Any]]:
    conn = connect()
    try:
        if user_id:
            rows = conn.execute(
                """
                SELECT * FROM conversations
                WHERE user_id = ?
                ORDER BY updated_at DESC
                """,
                (user_id,),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM conversations ORDER BY updated_at DESC"
            ).fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


def count_conversations(user_id: str) -> int:
    conn = connect()
    try:
        row = conn.execute(
            "SELECT COUNT(*) AS n FROM conversations WHERE user_id = ?",
            (user_id,),
        ).fetchone()
        return int(row["n"] if row else 0)
    finally:
        conn.close()


def free_conversation_ids(user_id: str) -> set[str]:
    conn = connect()
    try:
        rows = conn.execute(
            """
            SELECT id FROM conversations
            WHERE user_id = ?
            ORDER BY created_at ASC, id ASC
            LIMIT ?
            """,
            (user_id, config.FREE_PAGE_LIMIT),
        ).fetchall()
        return {row["id"] for row in rows}
    finally:
        conn.close()


def is_extra_page(conversation: dict[str, Any]) -> bool:
    user_id = conversation.get("user_id")
    if not user_id:
        return False
    return conversation["id"] not in free_conversation_ids(user_id)


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
        "images_pending",
        "next_url",
        "user_id",
    }
    updates = {key: value for key, value in fields.items() if key in allowed}
    if "images_pending" in updates:
        updates["images_pending"] = 1 if updates["images_pending"] else 0
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


def get_conversation_by_slug(slug: str) -> dict[str, Any] | None:
    conn = connect()
    try:
        row = conn.execute(
            """
            SELECT * FROM conversations
            WHERE slug = ?
            ORDER BY updated_at DESC
            """,
            (slug,),
        ).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def add_lead(
    conversation_id: str,
    slug: str,
    name: str,
    email: str,
    phone: str,
) -> dict[str, Any]:
    row = {
        "id": str(uuid4()),
        "conversation_id": conversation_id,
        "slug": slug,
        "name": name,
        "email": email,
        "phone": phone,
        "created_at": utcnow(),
    }
    conn = connect()
    try:
        conn.execute(
            """
            INSERT INTO leads (
                id, conversation_id, slug, name, email, phone, created_at
            ) VALUES (
                :id, :conversation_id, :slug, :name, :email, :phone, :created_at
            )
            """,
            row,
        )
        conn.commit()
    finally:
        conn.close()
    return row


def _row(conn: sqlite3.Connection, query: str, params: tuple = ()) -> dict[str, Any] | None:
    row = conn.execute(query, params).fetchone()
    return dict(row) if row else None


def upsert_user(google_sub: str, email: str, name: str = "") -> dict[str, Any]:
    now = utcnow()
    conn = connect()
    try:
        existing = _row(conn, "SELECT * FROM users WHERE google_sub = ?", (google_sub,))
        if existing:
            conn.execute(
                """
                UPDATE users
                SET email = ?, name = ?, updated_at = ?
                WHERE id = ?
                """,
                (email, name or existing.get("name"), now, existing["id"]),
            )
            conn.commit()
            return get_user(existing["id"]) or existing
        row = {
            "id": str(uuid4()),
            "google_sub": google_sub,
            "email": email,
            "name": name or email,
            "stripe_customer_id": None,
            "payment_method_ok": 0,
            "created_at": now,
            "updated_at": now,
        }
        conn.execute(
            """
            INSERT INTO users (
                id, google_sub, email, name, stripe_customer_id,
                payment_method_ok, created_at, updated_at
            ) VALUES (
                :id, :google_sub, :email, :name, :stripe_customer_id,
                :payment_method_ok, :created_at, :updated_at
            )
            """,
            row,
        )
        conn.commit()
        return row
    finally:
        conn.close()


def get_user(user_id: str) -> dict[str, Any] | None:
    conn = connect()
    try:
        return _row(conn, "SELECT * FROM users WHERE id = ?", (user_id,))
    finally:
        conn.close()


def update_user(user_id: str, **fields: Any) -> dict[str, Any] | None:
    allowed = {"email", "name", "stripe_customer_id", "payment_method_ok"}
    updates = {key: value for key, value in fields.items() if key in allowed}
    if "payment_method_ok" in updates:
        updates["payment_method_ok"] = 1 if updates["payment_method_ok"] else 0
    if not updates:
        return get_user(user_id)
    updates["updated_at"] = utcnow()
    assignments = ", ".join(f"{key} = :{key}" for key in updates)
    updates["id"] = user_id
    conn = connect()
    try:
        conn.execute(f"UPDATE users SET {assignments} WHERE id = :id", updates)
        conn.commit()
    finally:
        conn.close()
    return get_user(user_id)


def claim_unowned_conversations(user_id: str) -> int:
    conn = connect()
    try:
        cur = conn.execute(
            """
            UPDATE conversations
            SET user_id = ?, updated_at = ?
            WHERE user_id IS NULL
            """,
            (user_id, utcnow()),
        )
        conn.commit()
        return int(cur.rowcount or 0)
    finally:
        conn.close()


def get_page_subscription(conversation_id: str) -> dict[str, Any] | None:
    conn = connect()
    try:
        return _row(
            conn,
            "SELECT * FROM page_subscriptions WHERE conversation_id = ?",
            (conversation_id,),
        )
    finally:
        conn.close()


def get_page_subscription_by_stripe_id(stripe_subscription_id: str) -> dict[str, Any] | None:
    conn = connect()
    try:
        return _row(
            conn,
            "SELECT * FROM page_subscriptions WHERE stripe_subscription_id = ?",
            (stripe_subscription_id,),
        )
    finally:
        conn.close()


def upsert_page_subscription(
    user_id: str,
    conversation_id: str,
    *,
    stripe_subscription_id: str | None = None,
    status: str = "trialing",
    trial_end: str | None = None,
    grace_started_at: str | None = None,
) -> dict[str, Any]:
    now = utcnow()
    existing = get_page_subscription(conversation_id)
    conn = connect()
    try:
        if existing:
            conn.execute(
                """
                UPDATE page_subscriptions
                SET stripe_subscription_id = COALESCE(?, stripe_subscription_id),
                    status = ?, trial_end = COALESCE(?, trial_end),
                    grace_started_at = ?, updated_at = ?
                WHERE conversation_id = ?
                """,
                (
                    stripe_subscription_id,
                    status,
                    trial_end,
                    grace_started_at,
                    now,
                    conversation_id,
                ),
            )
            conn.commit()
            return get_page_subscription(conversation_id) or existing
        row = {
            "id": str(uuid4()),
            "user_id": user_id,
            "conversation_id": conversation_id,
            "stripe_subscription_id": stripe_subscription_id,
            "status": status,
            "trial_end": trial_end,
            "grace_started_at": grace_started_at,
            "created_at": now,
            "updated_at": now,
        }
        conn.execute(
            """
            INSERT INTO page_subscriptions (
                id, user_id, conversation_id, stripe_subscription_id, status,
                trial_end, grace_started_at, created_at, updated_at
            ) VALUES (
                :id, :user_id, :conversation_id, :stripe_subscription_id, :status,
                :trial_end, :grace_started_at, :created_at, :updated_at
            )
            """,
            row,
        )
        conn.commit()
        return row
    finally:
        conn.close()


def list_leads(conversation_id: str) -> list[dict[str, Any]]:
    conn = connect()
    try:
        rows = conn.execute(
            """
            SELECT * FROM leads
            WHERE conversation_id = ?
            ORDER BY created_at ASC
            """,
            (conversation_id,),
        ).fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()
