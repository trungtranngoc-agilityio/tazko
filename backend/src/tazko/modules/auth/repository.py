"""Sessions in control.db. The cookie holds a random token; only its SHA-256 is stored."""

from __future__ import annotations

import sqlite3

from tazko.modules.users.service import User


def insert_session(
    conn: sqlite3.Connection,
    *,
    token_hash: str,
    user_id: int,
    now: str,
    expires_at: str,
    ip: str | None,
    user_agent: str | None,
) -> None:
    conn.execute(
        "INSERT INTO sessions (token_hash, user_id, created_at, last_used_at, expires_at, ip,"
        " user_agent) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (token_hash, user_id, now, now, expires_at, ip, user_agent),
    )


def delete_session(conn: sqlite3.Connection, token_hash: str) -> None:
    conn.execute("DELETE FROM sessions WHERE token_hash = ?", (token_hash,))


def session_user(conn: sqlite3.Connection, token_hash: str, *, now: str) -> tuple[User, str] | None:
    """The person of a live session and when the session was last used.
    Expired sessions and disabled people find nothing."""
    row = conn.execute(
        "SELECT u.id, u.email, u.name, u.google_sub, u.avatar_url, u.hd, u.is_super_admin,"
        " s.last_used_at FROM sessions s JOIN users u ON u.id = s.user_id"
        " WHERE s.token_hash = ? AND s.expires_at > ? AND u.disabled_at IS NULL",
        (token_hash, now),
    ).fetchone()
    if row is None:
        return None
    user = User(
        id=row["id"],
        email=row["email"],
        name=row["name"],
        google_sub=row["google_sub"],
        avatar_url=row["avatar_url"],
        hd=row["hd"],
        is_super_admin=bool(row["is_super_admin"]),
        disabled=False,
    )
    return user, row["last_used_at"]


def touch_session(conn: sqlite3.Connection, token_hash: str, *, now: str, expires_at: str) -> None:
    conn.execute(
        "UPDATE sessions SET last_used_at = ?, expires_at = ? WHERE token_hash = ?",
        (now, expires_at, token_hash),
    )
