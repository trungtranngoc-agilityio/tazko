"""SQL for reading the audit log (writing is audit.service.record)."""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass


@dataclass(frozen=True)
class Entry:
    id: int
    at: str
    action: str
    actor_id: int | None
    actor_name: str | None
    actor_email: str | None
    org_slug: str | None
    org_name: str | None
    target: str | None
    detail: dict[str, object] | None
    ip: str | None


def page(
    conn: sqlite3.Connection, *, before: int | None, limit: int, prefix: str | None
) -> list[Entry]:
    """Newest first, by id: rows with id < before, at most `limit`. `prefix`
    keeps one kind of action (`company.` and so on); it comes from an allow list."""
    pattern = None if prefix is None else prefix.replace("_", "\\_") + ".%"
    rows = conn.execute(
        "SELECT a.id, a.at, a.action, a.actor_id, u.name AS actor_name, u.email AS actor_email,"
        " o.slug AS org_slug, o.name AS org_name, a.target, a.detail, a.ip"
        " FROM audit_log a LEFT JOIN users u ON u.id = a.actor_id"
        " LEFT JOIN orgs o ON o.id = a.org_id"
        " WHERE (? IS NULL OR a.id < ?) AND (? IS NULL OR a.action LIKE ? ESCAPE '\\')"
        " ORDER BY a.id DESC LIMIT ?",
        (before, before, pattern, pattern, limit),
    ).fetchall()
    return [
        Entry(
            id=row["id"],
            at=row["at"],
            action=row["action"],
            actor_id=row["actor_id"],
            actor_name=row["actor_name"],
            actor_email=row["actor_email"],
            org_slug=row["org_slug"],
            org_name=row["org_name"],
            target=row["target"],
            detail=json.loads(row["detail"]) if row["detail"] else None,
            ip=row["ip"],
        )
        for row in rows
    ]
