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
