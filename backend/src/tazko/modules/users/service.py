"""Rules for people in control.db. Emails are stored lower-cased (invites match on it)."""

from __future__ import annotations

import logging
import re
import sqlite3
from dataclasses import dataclass
from typing import Literal

from tazko.core.clock import now_iso
from tazko.core.errors import Invalid
from tazko.db import Database
from tazko.modules.audit import service as audit
from tazko.modules.users import repository as repo
from tazko.modules.users.repository import User

__all__ = [
    "GoogleAccount",
    "Refused",
    "User",
    "create_from_google",
    "get",
    "get_or_create",
    "grant_super_admin",
    "match_google_account",
    "normalize_email",
]

log = logging.getLogger(__name__)

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


@dataclass(frozen=True)
class GoogleAccount:
    """The verified claims of a Google ID token that sign-in uses."""

    sub: str
    email: str
    name: str
    avatar_url: str | None
    hd: str | None


@dataclass(frozen=True)
class Refused:
    reason: Literal[
        "not_invited", "disabled", "account_mismatch", "invite_expired", "invite_revoked"
    ]


def match_google_account(
    conn: sqlite3.Connection, account: GoogleAccount, *, ip: str | None
) -> User | Refused:
    """Find the person a verified Google account belongs to, inside the
    caller's transaction, and refresh their profile from it.

    By `sub` first, so a changed email still signs in. By email only for a
    person with no `sub` yet (made by an invite or `tazko admin`); that first
    link is audited. A person who already has another `sub` is never re-linked.
    """
    user = repo.by_sub(conn, account.sub)
    if user is None:
        try:
            address = normalize_email(account.email)
        except Invalid:
            return Refused("not_invited")
        user = repo.by_email(conn, address)
        if user is None:
            return Refused("not_invited")
        if user.google_sub is not None:
            return Refused("account_mismatch")
        if user.disabled:
            return Refused("disabled")
        repo.link_sub(conn, user.id, account.sub)
        audit.record(conn, "account.linked", actor_id=user.id, target=address, ip=ip)
    if user.disabled:
        return Refused("disabled")
    repo.update_profile(
        conn,
        user.id,
        email=_new_email(conn, user, account.email),
        name=account.name or user.name,
        avatar_url=account.avatar_url,
        hd=account.hd,
        now=now_iso(),
    )
    fresh = repo.by_id(conn, user.id)
    if fresh is None:
        raise RuntimeError("row vanished inside its own transaction")
    return fresh


def create_from_google(conn: sqlite3.Connection, account: GoogleAccount, *, ip: str | None) -> User:
    """A new person for a verified Google account, inside the caller's
    transaction. Only sign-in with a usable invite calls this."""
    address = normalize_email(account.email)
    user = repo.insert(conn, email=address, name=account.name, now=now_iso())
    repo.link_sub(conn, user.id, account.sub)
    repo.update_profile(
        conn,
        user.id,
        email=address,
        name=account.name,
        avatar_url=account.avatar_url,
        hd=account.hd,
        now=now_iso(),
    )
    audit.record(conn, "account.created", actor_id=user.id, target=address, ip=ip)
    fresh = repo.by_id(conn, user.id)
    if fresh is None:
        raise RuntimeError("row vanished inside its own transaction")
    return fresh


def _new_email(conn: sqlite3.Connection, user: User, claimed: str) -> str:
    """Follow an email change at Google, unless the new address is unusable
    or another person already has it (then keep the stored one)."""
    try:
        address = normalize_email(claimed)
    except Invalid:
        return user.email
    if address != user.email and repo.email_taken(conn, address, other_than=user.id):
        log.warning("person %s: new email belongs to another person; kept the old one", user.id)
        return user.email
    return address
