"""Rules for people in control.db. Emails are stored lower-cased (invites match on it)."""

from __future__ import annotations

import re
import sqlite3

from tazko.core.clock import now_iso
from tazko.core.errors import Invalid
from tazko.db import Database
from tazko.modules.audit import service as audit
from tazko.modules.users import repository as repo
from tazko.modules.users.repository import User

__all__ = ["User", "get", "get_or_create", "grant_super_admin", "normalize_email"]

EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def normalize_email(email: str) -> str:
    """The one way to compare emails (sign-in, invites, `tazko admin`).

    ASCII only: Unicode case folding maps some letters onto ASCII ones (the
    Kelvin sign lower-cases to "k") and invisible characters make look-alike
    addresses, either of which could land a sign-in on someone else's row.
    """
    value = email.strip()
    if not value.isascii() or not value.isprintable():
        raise Invalid("email: use plain ASCII letters, digits and symbols", field="email")
    value = value.lower()
    if len(value) > 254 or not EMAIL.fullmatch(value):
        raise Invalid("email: not a valid email address", field="email")
    return value


def get(control: Database, user_id: int) -> User | None:
    return control.read(lambda c: repo.by_id(c, user_id))


def get_or_create(control: Database, email: str, *, name: str = "") -> User:
    address = normalize_email(email)

    def run(conn: sqlite3.Connection) -> User:
        return repo.by_email(conn, address) or repo.insert(
            conn, email=address, name=name, now=now_iso()
        )

    return control.write(run)


def grant_super_admin(control: Database, email: str, *, actor_id: int | None) -> tuple[User, bool]:
    """Create the person if needed and set the flag. Returns (person, created)."""
    address = normalize_email(email)

    def run(conn: sqlite3.Connection) -> tuple[User, bool]:
        existing = repo.by_email(conn, address)
        user = existing or repo.insert(conn, email=address, name="", now=now_iso())
        if not user.is_super_admin:
            repo.set_super_admin(conn, user.id, True)
            audit.record(conn, "super_admin.granted", actor_id=actor_id, target=address)
        fresh = repo.by_id(conn, user.id)
        if fresh is None:
            raise RuntimeError("row vanished inside its own transaction")
        return fresh, existing is None

    return control.write(run)
