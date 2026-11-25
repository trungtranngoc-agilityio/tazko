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


def by_id(conn: sqlite3.Connection, org_id: int) -> Org | None:
    row = conn.execute("SELECT id, slug, name, status FROM orgs WHERE id = ?", (org_id,)).fetchone()
    return _org(row) if row else None


@dataclass(frozen=True)
class OrgCounts:
    org: Org
    members: int
    storage_limit_bytes: int | None
    last_activity_at: str | None


COMPANIES_CAP = 500


def _counts(row: sqlite3.Row) -> OrgCounts:
    return OrgCounts(
        org=_org(row),
        members=row["members"],
        storage_limit_bytes=row["storage_limit_bytes"],
        last_activity_at=row["last_activity_at"],
    )


COUNTS_SELECT = (
    "SELECT o.id, o.slug, o.name, o.status, o.storage_limit_bytes,"
    " (SELECT count(*) FROM org_members m WHERE m.org_id = o.id) AS members,"
    # Newest audit row of the company (index audit_log_by_org).
    " (SELECT max(a.at) FROM audit_log a WHERE a.org_id = o.id) AS last_activity_at"
    " FROM orgs o"
)


def all_with_counts(conn: sqlite3.Connection) -> list[OrgCounts]:
    """Every company not deleted, by name, at most COMPANIES_CAP."""
    rows = conn.execute(
        COUNTS_SELECT
        + " WHERE o.status != 'deleted' ORDER BY o.name COLLATE NOCASE, o.slug LIMIT ?",
        (COMPANIES_CAP,),
    ).fetchall()
    return [_counts(row) for row in rows]


def one_with_counts(conn: sqlite3.Connection, slug: str) -> OrgCounts | None:
    row = conn.execute(
        COUNTS_SELECT + " WHERE o.slug = ? AND o.status != 'deleted'", (slug,)
    ).fetchone()
    return _counts(row) if row else None


def insert(conn: sqlite3.Connection, *, slug: str, name: str, now: str) -> Org:
    conn.execute("INSERT INTO orgs (slug, name, created_at) VALUES (?, ?, ?)", (slug, name, now))
    org = by_slug(conn, slug)
    if org is None:
        raise RuntimeError("row vanished inside its own transaction")
    return org


def insert_member(
    conn: sqlite3.Connection, *, org_id: int, user_id: int, role: str, now: str
) -> None:
    conn.execute(
        "INSERT INTO org_members (org_id, user_id, role, created_at) VALUES (?, ?, ?, ?)",
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


def member_id_by_email(conn: sqlite3.Connection, *, org_id: int, email: str) -> int | None:
    row = conn.execute(
        "SELECT m.user_id FROM org_members m JOIN users u ON u.id = m.user_id"
        " WHERE m.org_id = ? AND u.email = ?",
        (org_id, email),
    ).fetchone()
    return int(row[0]) if row else None


def set_status(conn: sqlite3.Connection, org_id: int, status: str) -> None:
    conn.execute("UPDATE orgs SET status = ? WHERE id = ?", (status, org_id))


def mark_deleted(conn: sqlite3.Connection, org_id: int, *, now: str) -> None:
    conn.execute("UPDATE orgs SET status = 'deleted', deleted_at = ? WHERE id = ?", (now, org_id))


def stranded_members(conn: sqlite3.Connection, org_id: int) -> list[int]:
    """Members of the company who are not super admins and are in no other
    active company: suspending it leaves them nothing to use."""
    rows = conn.execute(
        "SELECT m.user_id FROM org_members m JOIN users u ON u.id = m.user_id"
        " WHERE m.org_id = ? AND u.is_super_admin = 0 AND NOT EXISTS ("
        "   SELECT 1 FROM org_members o JOIN orgs g ON g.id = o.org_id"
        "   WHERE o.user_id = m.user_id AND o.org_id != m.org_id AND g.status = 'active')",
        (org_id,),
    ).fetchall()
    return [int(r["user_id"]) for r in rows]


def only_suspended_companies(conn: sqlite3.Connection, user_id: int) -> bool:
    """The person is in at least one company that is not deleted, and none of
    them is active (sign-in refuses them)."""
    row = conn.execute(
        "SELECT count(*) AS listed, coalesce(sum(o.status = 'active'), 0) AS active"
        " FROM org_members m JOIN orgs o ON o.id = m.org_id"
        " WHERE m.user_id = ? AND o.status != 'deleted'",
        (user_id,),
    ).fetchone()
    return bool(row["listed"]) and not row["active"]


def by_slug_not_deleted(conn: sqlite3.Connection, slug: str) -> Org | None:
    row = conn.execute(
        "SELECT id, slug, name, status FROM orgs WHERE slug = ? AND status != 'deleted'", (slug,)
    ).fetchone()
    return _org(row) if row else None


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


@dataclass(frozen=True)
class MemberRow:
    user_id: int
    name: str
    email: str
    avatar_url: str | None
    hd: str | None
    role: str
    last_seen_at: str | None


MEMBERS_CAP = 500


def members(conn: sqlite3.Connection, org_id: int) -> list[MemberRow]:
    """The company's members by name, at most MEMBERS_CAP (a company is small)."""
    rows = conn.execute(
        "SELECT u.id, u.name, u.email, u.avatar_url, u.hd, m.role, u.last_seen_at"
        " FROM org_members m JOIN users u ON u.id = m.user_id"
        " WHERE m.org_id = ? ORDER BY u.name = '', u.name COLLATE NOCASE, u.email LIMIT ?",
        (org_id, MEMBERS_CAP),
    ).fetchall()
    return [_member(row) for row in rows]


def member(conn: sqlite3.Connection, org_id: int, user_id: int) -> MemberRow | None:
    row = conn.execute(
        "SELECT u.id, u.name, u.email, u.avatar_url, u.hd, m.role, u.last_seen_at"
        " FROM org_members m JOIN users u ON u.id = m.user_id"
        " WHERE m.org_id = ? AND m.user_id = ?",
        (org_id, user_id),
    ).fetchone()
    return _member(row) if row else None


def _member(row: sqlite3.Row) -> MemberRow:
    return MemberRow(
        user_id=row["id"],
        name=row["name"],
        email=row["email"],
        avatar_url=row["avatar_url"],
        hd=row["hd"],
        role=row["role"],
        last_seen_at=row["last_seen_at"],
    )


def owner_count(conn: sqlite3.Connection, org_id: int) -> int:
    """Owners who can still act: a disabled owner cannot sign in, so does not count."""
    return int(
        conn.execute(
            "SELECT count(*) FROM org_members m JOIN users u ON u.id = m.user_id"
            " WHERE m.org_id = ? AND m.role = 'owner' AND u.disabled_at IS NULL",
            (org_id,),
        ).fetchone()[0]
    )


def set_role(conn: sqlite3.Connection, *, org_id: int, user_id: int, role: str) -> None:
    conn.execute(
        "UPDATE org_members SET role = ? WHERE org_id = ? AND user_id = ?", (role, org_id, user_id)
    )


def delete_member(conn: sqlite3.Connection, *, org_id: int, user_id: int) -> None:
    conn.execute("DELETE FROM org_members WHERE org_id = ? AND user_id = ?", (org_id, user_id))


def memberships(conn: sqlite3.Connection, user_id: int) -> list[Membership]:
    # Includes suspended companies (status is on Org) so the switcher can show them
    # as suspended; open_company still refuses them.
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
