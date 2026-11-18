"""SQL for invites in control.db. Times are ISO text and compare as text."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass


@dataclass(frozen=True)
class Invite:
    id: int
    org_id: int
    email: str
    role: str
    created_at: str
    expires_at: str
    accepted_at: str | None
    revoked_at: str | None


def _invite(row: sqlite3.Row) -> Invite:
    return Invite(
        id=row["id"],
        org_id=row["org_id"],
        email=row["email"],
        role=row["role"],
        created_at=row["created_at"],
        expires_at=row["expires_at"],
        accepted_at=row["accepted_at"],
        revoked_at=row["revoked_at"],
    )


def by_id(conn: sqlite3.Connection, invite_id: int) -> Invite | None:
    row = conn.execute(
        "SELECT i.id, i.org_id, i.email, i.role, i.created_at, i.expires_at,"
        " i.accepted_at, i.revoked_at"
        " FROM invites i WHERE i.id = ?",
        (invite_id,),
    ).fetchone()
    return _invite(row) if row else None


def insert(
    conn: sqlite3.Connection,
    *,
    org_id: int,
    email: str,
    role: str,
    created_by: int | None,
    now: str,
    expires_at: str,
) -> Invite:
    cursor = conn.execute(
        "INSERT INTO invites (org_id, email, role, created_by, created_at, expires_at)"
        " VALUES (?, ?, ?, ?, ?, ?)",
        (org_id, email, role, created_by, now, expires_at),
    )
    invite = by_id(conn, int(cursor.lastrowid or 0))
    if invite is None:
        raise RuntimeError("row vanished inside its own transaction")
    return invite


def pending(conn: sqlite3.Connection, *, org_id: int, email: str, now: str) -> Invite | None:
    row = conn.execute(
        "SELECT i.id, i.org_id, i.email, i.role, i.created_at, i.expires_at,"
        " i.accepted_at, i.revoked_at"
        " FROM invites i"
        " WHERE i.org_id = ? AND i.email = ? AND i.accepted_at IS NULL"
        " AND i.revoked_at IS NULL AND i.expires_at > ?",
        (org_id, email, now),
    ).fetchone()
    return _invite(row) if row else None


@dataclass(frozen=True)
class PendingInvite:
    id: int
    email: str
    role: str
    invited_by: str | None
    created_at: str
    expires_at: str
    workspace: bool


PENDING_CAP = 500


def pending_for_org(conn: sqlite3.Connection, org_id: int, *, now: str) -> list[PendingInvite]:
    """Unused, unrevoked, unexpired invites of one company, newest first, at
    most PENDING_CAP. `workspace`: the address's domain is a known Workspace."""
    rows = conn.execute(
        "SELECT i.id, i.email, i.role, i.created_at, i.expires_at, u.name AS invited_by,"
        " w.domain IS NOT NULL AS workspace"
        " FROM invites i LEFT JOIN users u ON u.id = i.created_by"
        " LEFT JOIN workspace_domains w ON w.domain = substr(i.email, instr(i.email, '@') + 1)"
        " WHERE i.org_id = ? AND i.accepted_at IS NULL AND i.revoked_at IS NULL"
        " AND i.expires_at > ? ORDER BY i.id DESC LIMIT ?",
        (org_id, now, PENDING_CAP),
    ).fetchall()
    return [
        PendingInvite(
            id=row["id"],
            email=row["email"],
            role=row["role"],
            invited_by=row["invited_by"] or None,
            created_at=row["created_at"],
            expires_at=row["expires_at"],
            workspace=bool(row["workspace"]),
        )
        for row in rows
    ]


def usable(conn: sqlite3.Connection, email: str, *, now: str) -> list[Invite]:
    """Invites this email can use now: not used, not revoked, not expired, for
    an active company. Uses the partial index invites_pending_by_email."""
    rows = conn.execute(
        "SELECT i.id, i.org_id, i.email, i.role, i.created_at, i.expires_at,"
        " i.accepted_at, i.revoked_at"
        " FROM invites i JOIN orgs o ON o.id = i.org_id"
        " WHERE i.email = ? AND i.accepted_at IS NULL AND i.revoked_at IS NULL"
        " AND i.expires_at > ? AND o.status = 'active'"
        " ORDER BY i.id",
        (email, now),
    ).fetchall()
    return [_invite(row) for row in rows]


def latest_unused(conn: sqlite3.Connection, email: str) -> Invite | None:
    """The newest invite for this email that was never used (expired or
    revoked ones included), to say why a sign-in was refused. Uses the
    partial index invites_unused_by_email (migration 0002_signin_lookups)."""
    row = conn.execute(
        "SELECT i.id, i.org_id, i.email, i.role, i.created_at, i.expires_at,"
        " i.accepted_at, i.revoked_at"
        " FROM invites i WHERE i.email = ? AND i.accepted_at IS NULL"
        " ORDER BY i.id DESC LIMIT 1",
        (email,),
    ).fetchone()
    return _invite(row) if row else None


def mark_accepted(conn: sqlite3.Connection, invite_id: int, *, user_id: int, now: str) -> bool:
    """Use the invite, only if it is still usable. False: it was not (used,
    revoked or expired in the meantime), and nothing changed."""
    cursor = conn.execute(
        "UPDATE invites SET accepted_at = ?, accepted_by = ?"
        " WHERE id = ? AND accepted_at IS NULL AND revoked_at IS NULL AND expires_at > ?",
        (now, user_id, invite_id, now),
    )
    return cursor.rowcount == 1


def mark_revoked(conn: sqlite3.Connection, invite_id: int, *, org_id: int, now: str) -> bool:
    """Revoke an unused invite of this company. False: none such."""
    cursor = conn.execute(
        "UPDATE invites SET revoked_at = ?"
        " WHERE id = ? AND org_id = ? AND accepted_at IS NULL AND revoked_at IS NULL",
        (now, invite_id, org_id),
    )
    return cursor.rowcount == 1
