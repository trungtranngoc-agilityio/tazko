from __future__ import annotations

import json
import sqlite3
from collections.abc import Mapping
from typing import Literal, get_args

from tazko.core.clock import now_iso
from tazko.modules.audit import repository as repo
from tazko.modules.audit.repository import Entry

__all__ = ["KINDS", "Entry", "Kind", "page", "record"]

# The kinds the console's Audit log filter offers: the part of `action` before the dot.
Kind = Literal[
    "account", "company", "invite", "member", "person", "signin", "super_admin", "workspace_domain"
]
KINDS: tuple[str, ...] = get_args(Kind)


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


def page(
    conn: sqlite3.Connection, *, before: int | None, limit: int, kind: str | None
) -> list[Entry]:
    """Audit rows newest first, inside the caller's read. The caller checks who asks."""
    if kind is not None and kind not in KINDS:
        raise ValueError(f"unknown kind {kind!r}")
    return repo.page(conn, before=before, limit=limit, prefix=kind)
