from __future__ import annotations

import sqlite3
from dataclasses import dataclass


@dataclass(frozen=True)
class Org:
    id: int
    slug: str
    name: str
    status: str


@dataclass(frozen=True)
class Membership:
    org: Org
    role: str


def _org(row: sqlite3.Row) -> Org:
    return Org(id=row["id"], slug=row["slug"], name=row["name"], status=row["status"])


def by_slug(conn: sqlite3.Connection, slug: str) -> Org | None:
    row = conn.execute("SELECT id, slug, name, status FROM orgs WHERE slug = ?", (slug,)).fetchone()
    return _org(row) if row else None


def insert(conn: sqlite3.Connection, *, slug: str, name: str, now: str) -> Org:
    conn.execute("INSERT INTO orgs (slug, name, created_at) VALUES (?, ?, ?)", (slug, name, now))
    org = by_slug(conn, slug)
    if org is None:
        raise RuntimeError("row vanished inside its own transaction")
    return org


def upsert_member(
    conn: sqlite3.Connection, *, org_id: int, user_id: int, role: str, now: str
) -> None:
    conn.execute(
        "INSERT INTO org_members (org_id, user_id, role, created_at) VALUES (?, ?, ?, ?)"
        " ON CONFLICT (org_id, user_id) DO UPDATE SET role = excluded.role",
        (org_id, user_id, role, now),
    )


def insert_member_if_absent(
    conn: sqlite3.Connection, *, org_id: int, user_id: int, role: str, now: str
) -> bool:
    """Add the membership unless there is one; an existing role never changes."""
    cursor = conn.execute(
        "INSERT INTO org_members (org_id, user_id, role, created_at) VALUES (?, ?, ?, ?)"
        " ON CONFLICT (org_id, user_id) DO NOTHING",
        (org_id, user_id, role, now),
    )
    return cursor.rowcount == 1


def is_active(conn: sqlite3.Connection, org_id: int) -> bool:
    row = conn.execute("SELECT status FROM orgs WHERE id = ?", (org_id,)).fetchone()
    return bool(row) and row["status"] == "active"


def has_member_email(conn: sqlite3.Connection, *, org_id: int, email: str) -> bool:
    return (
        conn.execute(
            "SELECT 1 FROM org_members m JOIN users u ON u.id = m.user_id"
            " WHERE m.org_id = ? AND u.email = ?",
            (org_id, email),
        ).fetchone()
        is not None
    )


def standing(
    conn: sqlite3.Connection, *, org_id: int, user_id: int
) -> tuple[bool, str | None] | None:
    """(is super admin, role in this company or None) for an enabled person; None
    for a missing or disabled one."""
    row = conn.execute(
        "SELECT u.is_super_admin, m.role FROM users u"
        " LEFT JOIN org_members m ON m.user_id = u.id AND m.org_id = ?"
        " WHERE u.id = ? AND u.disabled_at IS NULL",
        (org_id, user_id),
    ).fetchone()
    return (bool(row["is_super_admin"]), row["role"]) if row else None


def memberships(conn: sqlite3.Connection, user_id: int) -> list[Membership]:
    # Includes suspended companies (status is on Org) so the switcher can show them
    # as suspended; open_company still refuses them. TODO(M1-07): M1.md Q2.
    rows = conn.execute(
        "SELECT o.id, o.slug, o.name, o.status, m.role FROM org_members m"
        " JOIN orgs o ON o.id = m.org_id"
        " WHERE m.user_id = ? AND o.status != 'deleted'"
        " ORDER BY o.name COLLATE NOCASE, o.slug",
        (user_id,),
    ).fetchall()
    return [Membership(org=_org(row), role=row["role"]) for row in rows]


def active_membership(conn: sqlite3.Connection, user_id: int, slug: str) -> Membership | None:
    row = conn.execute(
        "SELECT o.id, o.slug, o.name, o.status, m.role FROM org_members m"
        " JOIN orgs o ON o.id = m.org_id"
        " JOIN users u ON u.id = m.user_id"
        " WHERE m.user_id = ? AND o.slug = ? AND o.status = 'active' AND u.disabled_at IS NULL",
        (user_id, slug),
    ).fetchone()
    return Membership(org=_org(row), role=row["role"]) if row else None


# --- in the company's own file -------------------------------------------------


def has_person(conn: sqlite3.Connection, user_id: int) -> bool:
    return conn.execute("SELECT 1 FROM people WHERE id = ?", (user_id,)).fetchone() is not None


def upsert_person(
    conn: sqlite3.Connection,
    *,
    user_id: int,
    name: str,
    email: str,
    avatar_url: str | None,
    now: str,
) -> None:
    conn.execute(
        "INSERT INTO people (id, name, email, avatar_url, updated_at) VALUES (?, ?, ?, ?, ?)"
        " ON CONFLICT (id) DO UPDATE SET name = excluded.name, email = excluded.email,"
        " avatar_url = excluded.avatar_url, updated_at = excluded.updated_at",
        (user_id, name, email, avatar_url, now),
    )


def add_event(
    conn: sqlite3.Connection, *, type: str, actor_id: int | None, payload: str, now: str
) -> None:
    conn.execute(
        "INSERT INTO events (type, actor_id, payload, created_at) VALUES (?, ?, ?, ?)",
        (type, actor_id, payload, now),
    )
