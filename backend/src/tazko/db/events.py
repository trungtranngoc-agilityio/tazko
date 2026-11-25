"""The company file's events table: every change writes one row in its own transaction."""

from __future__ import annotations

import json
import sqlite3

from tazko.core.clock import now_iso


def add(
    conn: sqlite3.Connection,
    kind: str,
    actor_id: int | None,
    *,
    board_id: int | None = None,
    **payload: object,
) -> None:
    conn.execute(
        "INSERT INTO events (type, actor_id, board_id, payload, created_at) VALUES (?, ?, ?, ?, ?)",
        (kind, actor_id, board_id, json.dumps(payload), now_iso()),
    )
