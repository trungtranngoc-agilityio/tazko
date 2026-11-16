from __future__ import annotations

import json
import sqlite3
from collections.abc import Mapping

from tazko.core.clock import now_iso


def record(
    conn: sqlite3.Connection,
    action: str,
    *,
    actor_id: int | None,
    org_id: int | None = None,
    target: str | None = None,
    detail: Mapping[str, object] | None = None,
    ip: str | None = None,
) -> None:
    """Write one audit row inside the caller's transaction.

    `action` is `<noun>.<past verb>`, e.g. company.created, signin.refused.
    `actor_id` is None for the command line and the system.
    """
    conn.execute(
        "INSERT INTO audit_log (at, actor_id, action, org_id, target, detail, ip)"
        " VALUES (?, ?, ?, ?, ?, ?, ?)",
        (
            now_iso(),
            actor_id,
            action,
            org_id,
            target,
            json.dumps(detail, separators=(",", ":")) if detail else None,
            ip,
        ),
    )
