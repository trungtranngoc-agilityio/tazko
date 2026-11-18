from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass


@dataclass(frozen=True)
class User:
    id: int
    email: str
    name: str
    google_sub: str | None
    avatar_url: str | None
    hd: str | None
    is_super_admin: bool
    disabled: bool


COLUMNS = "id, email, name, google_sub, avatar_url, hd, is_super_admin, disabled_at"


def _user(row: sqlite3.Row) -> User:
    return User(
        id=row["id"],
        email=row["email"],
        name=row["name"],
        google_sub=row["google_sub"],
        avatar_url=row["avatar_url"],
        hd=row["hd"],
        is_super_admin=bool(row["is_super_admin"]),
        disabled=row["disabled_at"] is not None,
    )


def by_id(conn: sqlite3.Connection, user_id: int) -> User | None:
    row = conn.execute(f"SELECT {COLUMNS} FROM users WHERE id = ?", (user_id,)).fetchone()  # noqa: S608 (COLUMNS is a constant; values are bound)
    return _user(row) if row else None


def by_email(conn: sqlite3.Connection, email: str) -> User | None:
    row = conn.execute(f"SELECT {COLUMNS} FROM users WHERE email = ?", (email,)).fetchone()  # noqa: S608 (COLUMNS is a constant; values are bound)
    return _user(row) if row else None


def insert(conn: sqlite3.Connection, *, email: str, name: str, now: str) -> User:
    cursor = conn.execute(
        "INSERT INTO users (email, name, created_at) VALUES (?, ?, ?)", (email, name, now)
    )
    user = by_id(conn, int(cursor.lastrowid or 0))
    if user is None:
        raise RuntimeError("row vanished inside its own transaction")
    return user


def set_disabled(conn: sqlite3.Connection, user_id: int, at: str | None) -> None:
    conn.execute("UPDATE users SET disabled_at = ? WHERE id = ?", (at, user_id))


def end_sessions(conn: sqlite3.Connection, user_id: int) -> None:
    """Sign a person out everywhere. The sessions table belongs to auth, but a
    disabled person's sessions must go in the same transaction that disables them."""
    conn.execute("DELETE FROM sessions WHERE user_id = ?", (user_id,))


def is_enabled_super_admin(conn: sqlite3.Connection, user_id: int) -> bool:
    row = conn.execute(
        "SELECT 1 FROM users WHERE id = ? AND is_super_admin = 1 AND disabled_at IS NULL",
        (user_id,),
    ).fetchone()
    return row is not None


@dataclass(frozen=True)
class PersonRow:
    id: int
    name: str
    email: str
    avatar_url: str | None
    hd: str | None
    is_super_admin: bool
    disabled: bool
    last_seen_at: str | None


def people_page(
    conn: sqlite3.Connection, *, query: str | None, after: int | None, limit: int
) -> list[PersonRow]:
    """By id, rows with id > after, at most `limit`. `query` matches name or
    email anywhere, case-insensitively, with LIKE wildcards taken literally."""
    pattern = None
    if query:
        escaped = query.lower().replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        pattern = f"%{escaped}%"
    rows = conn.execute(
        "SELECT id, name, email, avatar_url, hd, is_super_admin, disabled_at, last_seen_at"
        " FROM users WHERE (? IS NULL OR id > ?)"
        " AND (? IS NULL OR lower(name) LIKE ? ESCAPE '\\' OR email LIKE ? ESCAPE '\\')"
        " ORDER BY id LIMIT ?",
        (after, after, pattern, pattern, pattern, limit),
    ).fetchall()
    return [
        PersonRow(
            id=row["id"],
            name=row["name"],
            email=row["email"],
            avatar_url=row["avatar_url"],
            hd=row["hd"],
            is_super_admin=bool(row["is_super_admin"]),
            disabled=row["disabled_at"] is not None,
            last_seen_at=row["last_seen_at"],
        )
        for row in rows
    ]


def person(conn: sqlite3.Connection, user_id: int) -> PersonRow | None:
    row = conn.execute(
        "SELECT id, name, email, avatar_url, hd, is_super_admin, disabled_at, last_seen_at"
        " FROM users WHERE id = ?",
        (user_id,),
    ).fetchone()
    if row is None:
        return None
    return PersonRow(
        id=row["id"],
        name=row["name"],
        email=row["email"],
        avatar_url=row["avatar_url"],
        hd=row["hd"],
        is_super_admin=bool(row["is_super_admin"]),
        disabled=row["disabled_at"] is not None,
        last_seen_at=row["last_seen_at"],
    )


def companies_of_people(
    conn: sqlite3.Connection, user_ids: list[int]
) -> list[tuple[int, str, str, str]]:
    """(user id, company slug, company name, role) for these people, one query."""
    if not user_ids:
        return []
    rows = conn.execute(
        "SELECT m.user_id, o.slug, o.name, m.role FROM org_members m JOIN orgs o ON o.id = m.org_id"
        " WHERE m.user_id IN (SELECT value FROM json_each(?)) AND o.status != 'deleted'"
        " ORDER BY o.name COLLATE NOCASE, o.slug",
        (json.dumps(user_ids),),
    ).fetchall()
    return [(row["user_id"], row["slug"], row["name"], row["role"]) for row in rows]


def workspace_domains(conn: sqlite3.Connection) -> list[tuple[str, str]]:
    """(domain, first seen) by domain, at most 500."""
    rows = conn.execute(
        "SELECT domain, first_seen_at FROM workspace_domains ORDER BY domain LIMIT 500"
    ).fetchall()
    return [(row["domain"], row["first_seen_at"]) for row in rows]


def forget_workspace_domain(conn: sqlite3.Connection, domain: str) -> bool:
    cursor = conn.execute("DELETE FROM workspace_domains WHERE domain = ?", (domain,))
    return cursor.rowcount == 1


def set_super_admin(conn: sqlite3.Connection, user_id: int, value: bool) -> None:
    conn.execute("UPDATE users SET is_super_admin = ? WHERE id = ?", (int(value), user_id))


def by_sub(conn: sqlite3.Connection, sub: str) -> User | None:
    row = conn.execute(f"SELECT {COLUMNS} FROM users WHERE google_sub = ?", (sub,)).fetchone()  # noqa: S608 (COLUMNS is a constant; values are bound)
    return _user(row) if row else None


def link_sub(conn: sqlite3.Connection, user_id: int, sub: str) -> None:
    """Only a row with no sub yet is linked; a linked row is never changed."""
    conn.execute(
        "UPDATE users SET google_sub = ? WHERE id = ? AND google_sub IS NULL", (sub, user_id)
    )


def is_workspace_domain(conn: sqlite3.Connection, domain: str) -> bool:
    row = conn.execute("SELECT 1 FROM workspace_domains WHERE domain = ?", (domain,)).fetchone()
    return row is not None


def remember_workspace_domain(conn: sqlite3.Connection, domain: str, *, now: str) -> None:
    conn.execute(
        "INSERT INTO workspace_domains (domain, first_seen_at) VALUES (?, ?)"
        " ON CONFLICT (domain) DO NOTHING",
        (domain, now),
    )


def email_taken(conn: sqlite3.Connection, email: str, *, other_than: int) -> bool:
    row = conn.execute(
        "SELECT 1 FROM users WHERE email = ? AND id != ?", (email, other_than)
    ).fetchone()
    return row is not None


def update_profile(
    conn: sqlite3.Connection,
    user_id: int,
    *,
    email: str,
    name: str,
    avatar_url: str | None,
    hd: str | None,
    now: str,
) -> None:
    conn.execute(
        "UPDATE users SET email = ?, name = ?, avatar_url = ?, hd = ?, last_seen_at = ?"
        " WHERE id = ?",
        (email, name, avatar_url, hd, now, user_id),
    )
