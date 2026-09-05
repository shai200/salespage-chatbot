#!/usr/bin/env python3
"""Merge a pulled Civo studio.sqlite into the local file.

Local wins on conversation id and on slug. Server conversations whose id and
slug are new are inserted, with their messages, leads, and LangGraph rows.
"""

from __future__ import annotations

import sqlite3
import sys
from pathlib import Path


def table_names(conn: sqlite3.Connection) -> set[str]:
    rows = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
    ).fetchall()
    return {row[0] for row in rows}


def columns(conn: sqlite3.Connection, table: str) -> list[str]:
    return [row[1] for row in conn.execute(f"PRAGMA table_info({table})").fetchall()]


def insert_or_ignore(
    dest: sqlite3.Connection,
    source: sqlite3.Connection,
    table: str,
    rows: list[sqlite3.Row],
) -> int:
    if not rows:
        return 0
    dest_cols = columns(dest, table)
    src_cols = columns(source, table)
    use = [col for col in dest_cols if col in src_cols]
    if not use:
        return 0
    placeholders = ", ".join("?" for _ in use)
    quoted = ", ".join(use)
    added = 0
    for row in rows:
        values = [row[col] for col in use]
        dest.execute(
            f"INSERT OR IGNORE INTO {table} ({quoted}) VALUES ({placeholders})",
            values,
        )
        added += dest.total_changes
    return added


def main() -> int:
    if len(sys.argv) != 3:
        print("usage: merge_studio_sqlite.py <local.sqlite> <remote.sqlite>", file=sys.stderr)
        return 2
    local_path = Path(sys.argv[1])
    remote_path = Path(sys.argv[2])
    if not remote_path.exists():
        print(f"missing remote db: {remote_path}", file=sys.stderr)
        return 1
    local_path.parent.mkdir(parents=True, exist_ok=True)
    if not local_path.exists() or local_path.stat().st_size == 0:
        import shutil

        shutil.copy2(remote_path, local_path)
        print(f"copied cluster sqlite → {local_path}")
        return 0
    dest = sqlite3.connect(local_path)
    source = sqlite3.connect(f"file:{remote_path}?mode=ro", uri=True)
    dest.row_factory = sqlite3.Row
    source.row_factory = sqlite3.Row

    dest_tables = table_names(dest)
    src_tables = table_names(source)

    if "conversations" not in src_tables:
        print("remote db has no conversations table")
        dest.close()
        source.close()
        return 0

    local_ids = {
        row["id"]
        for row in dest.execute("SELECT id FROM conversations").fetchall()
    } if "conversations" in dest_tables else set()
    local_slugs = {
        row["slug"]
        for row in dest.execute(
            "SELECT slug FROM conversations WHERE slug IS NOT NULL AND slug != ''"
        ).fetchall()
    } if "conversations" in dest_tables else set()

    imported_ids: list[str] = []
    for row in source.execute("SELECT * FROM conversations").fetchall():
        cid = row["id"]
        slug = row["slug"] if "slug" in row.keys() else None
        if cid in local_ids:
            print(f"keep local conversation {cid}")
            continue
        if slug and slug in local_slugs:
            print(f"keep local slug {slug} (skipped server {cid})")
            continue
        insert_or_ignore(dest, source, "conversations", [row])
        imported_ids.append(cid)
        print(f"imported conversation {cid} slug={slug or ''}")

    if imported_ids and "messages" in dest_tables and "messages" in src_tables:
        q = ",".join("?" for _ in imported_ids)
        rows = source.execute(
            f"SELECT * FROM messages WHERE conversation_id IN ({q})",
            imported_ids,
        ).fetchall()
        insert_or_ignore(dest, source, "messages", rows)
        print(f"imported {len(rows)} messages")

    if imported_ids and "leads" in dest_tables and "leads" in src_tables:
        q = ",".join("?" for _ in imported_ids)
        rows = source.execute(
            f"SELECT * FROM leads WHERE conversation_id IN ({q})",
            imported_ids,
        ).fetchall()
        insert_or_ignore(dest, source, "leads", rows)
        print(f"imported {len(rows)} leads")

    if imported_ids and "checkpoints" in dest_tables and "checkpoints" in src_tables:
        q = ",".join("?" for _ in imported_ids)
        for table in ("checkpoints", "writes"):
            if table not in dest_tables or table not in src_tables:
                continue
            if "thread_id" not in columns(source, table):
                continue
            rows = source.execute(
                f"SELECT * FROM {table} WHERE thread_id IN ({q})",
                imported_ids,
            ).fetchall()
            insert_or_ignore(dest, source, table, rows)
            print(f"imported {len(rows)} {table} rows")

    dest.commit()
    dest.close()
    source.close()
    print(f"merged {len(imported_ids)} conversation(s) into {local_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
