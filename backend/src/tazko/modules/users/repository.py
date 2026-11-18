from __future__ import annotations

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
