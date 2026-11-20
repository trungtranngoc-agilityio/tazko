"""Rules for people in control.db. Emails are stored lower-cased (invites match on it)."""

from __future__ import annotations

import contextlib
import logging
import re
import sqlite3
from dataclasses import dataclass
from typing import Literal

from tazko.core.clock import now_iso
from tazko.core.errors import Conflict, Forbidden, Invalid, NotFound
from tazko.db import Database
from tazko.modules.audit import service as audit
from tazko.modules.users import repository as repo
from tazko.modules.users.repository import User

__all__ = [
    "Company",
    "GoogleAccount",
    "Person",
    "Refused",
    "User",
    "create_from_google",
    "forget_workspace_domain",
    "get",
    "get_or_create",
    "grant_super_admin",
    "is_workspace_domain",
    "list_workspace_domains",
    "match_google_account",
    "needs_workspace",
    "normalize_email",
    "people_page",
    "remember_workspace",
    "require_super_admin",
    "set_flags",
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


def require_super_admin(conn: sqlite3.Connection, actor_id: int | None) -> None:
    """None is the command line. Anyone else must be an enabled super admin."""
    if actor_id is not None and not repo.is_enabled_super_admin(conn, actor_id):
        raise Forbidden("only a super admin can do this")


@dataclass(frozen=True)
class Company:
    slug: str
    name: str
    role: str


@dataclass(frozen=True)
class Person:
    """A row of the console's People page."""

    row: repo.PersonRow
    companies: list[Company]

    @property
    def account(self) -> Literal["workspace", "personal"] | None:
        if self.row.last_seen_at is None:
            return None
        return "workspace" if self.row.hd else "personal"


def people_page(
    control: Database, *, actor_id: int, query: str | None, after: int | None, limit: int
) -> tuple[list[Person], int | None]:
    """One page of everyone, by id, and the cursor for the next page (None at the end)."""

    def run(conn: sqlite3.Connection) -> tuple[list[Person], int | None]:
        require_super_admin(conn, actor_id)
        rows = repo.people_page(conn, query=query, after=after, limit=limit + 1)
        more = len(rows) > limit
        rows = rows[:limit]
        companies: dict[int, list[Company]] = {r.id: [] for r in rows}
        for user_id, slug, name, role in repo.companies_of_people(conn, list(companies)):
            companies[user_id].append(Company(slug=slug, name=name, role=role))
        people = [Person(row=r, companies=companies[r.id]) for r in rows]
        return people, (rows[-1].id if more else None)

    return control.read(run)


def set_flags(
    control: Database,
    *,
    user_id: int,
    actor_id: int,
    ip: str | None,
    is_super_admin: bool | None = None,
    active: bool | None = None,
) -> Person:
    """Grant or revoke super admin, disable or re-enable, from the console.

    A super admin never changes themselves (409 SELF_CHANGE), so the console
    always keeps one who can sign in. Disabling ends every session of that
    person in the same transaction; each change is audit-logged."""

    def run(conn: sqlite3.Connection) -> Person:
        require_super_admin(conn, actor_id)
        found = repo.person(conn, user_id)
        if found is None:
            raise NotFound()
        if user_id == actor_id:
            raise Conflict("you cannot change your own access", code="SELF_CHANGE")
        if is_super_admin is not None and is_super_admin != found.is_super_admin:
            _set_super_admin(conn, found, is_super_admin, actor_id=actor_id, ip=ip)
        if active is not None and active == found.disabled:
            _set_active(conn, found, active, actor_id=actor_id, ip=ip)
        fresh = repo.person(conn, user_id)
        if fresh is None:
            raise RuntimeError("row vanished inside its own transaction")
        companies = [
            Company(slug=slug, name=name, role=role)
            for _, slug, name, role in repo.companies_of_people(conn, [user_id])
        ]
        return Person(row=fresh, companies=companies)

    return control.write(run)


def _set_super_admin(
    conn: sqlite3.Connection, found: repo.PersonRow, value: bool, *, actor_id: int, ip: str | None
) -> None:
    repo.set_super_admin(conn, found.id, value)
    action = "super_admin.granted" if value else "super_admin.revoked"
    audit.record(conn, action, actor_id=actor_id, target=found.email, ip=ip)


def _set_active(
    conn: sqlite3.Connection, found: repo.PersonRow, value: bool, *, actor_id: int, ip: str | None
) -> None:
    repo.set_disabled(conn, found.id, None if value else now_iso())
    if not value:
        repo.end_sessions(conn, found.id)  # signed out at once
    action = "person.enabled" if value else "person.disabled"
    audit.record(conn, action, actor_id=actor_id, target=found.email, ip=ip)


def list_workspace_domains(control: Database, *, actor_id: int) -> list[tuple[str, str]]:
    def run(conn: sqlite3.Connection) -> list[tuple[str, str]]:
        require_super_admin(conn, actor_id)
        return repo.workspace_domains(conn)

    return control.read(run)


def forget_workspace_domain(
    control: Database, *, domain: str, actor_id: int, ip: str | None
) -> None:
    """For a company that left Google Workspace: personal accounts on its
    addresses can link and use invites again (D26). Unknown domain: NotFound."""
    name = domain.lower()

    def run(conn: sqlite3.Connection) -> None:
        require_super_admin(conn, actor_id)
        first_seen = repo.forget_workspace_domain(conn, name)
        if first_seen is None:
            raise NotFound()
        # When it was first seen, so a removal followed by a takeover can be traced.
        audit.record(
            conn,
            "workspace_domain.removed",
            actor_id=actor_id,
            target=name,
            detail={"first_seen_at": first_seen},
            ip=ip,
        )

    control.write(run)


def end_sessions(conn: sqlite3.Connection, user_id: int) -> None:
    """Sign the person out everywhere, inside the caller's transaction."""
    repo.end_sessions(conn, user_id)


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
        "not_invited",
        "disabled",
        "account_mismatch",
        "invite_expired",
        "invite_revoked",
        "workspace_required",
        "company_suspended",
    ]


def is_workspace_domain(conn: sqlite3.Connection, domain: str) -> bool:
    return repo.is_workspace_domain(conn, domain.lower())


def remember_workspace(conn: sqlite3.Connection, account: GoogleAccount) -> None:
    """After a sign-in with a Workspace account: its hd and its address's own
    domain (an alias domain reports the main one as hd) are Workspace domains."""
    if not account.hd:
        return
    domains = {account.hd.lower()}
    with contextlib.suppress(Invalid):  # an unusable address adds only the hd
        domains.add(normalize_email(account.email).rpartition("@")[2])
    now = now_iso()
    for domain in domains:
        repo.remember_workspace_domain(conn, domain, now=now)


def needs_workspace(conn: sqlite3.Connection, account: GoogleAccount, address: str) -> bool:
    """A personal Google account (no `hd`) on an address of a known Workspace
    domain may not claim that address (D26). A former employee can keep such
    an account on their old work address, and Google still calls it verified.

    A domain is known once someone signed in from it with a Workspace account
    (remember_workspace); we cannot ask Google about a domain we have not seen.
    Checking for no `hd`, rather than a different one, keeps Workspace alias
    domains working (their `hd` is the main domain)."""
    return account.hd is None and is_workspace_domain(conn, address.rpartition("@")[2])


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
        if needs_workspace(conn, account, address):
            return Refused("workspace_required")
        repo.link_sub(conn, user.id, account.sub)
        audit.record(conn, "account.linked", actor_id=user.id, target=address, ip=ip)
    if user.disabled:
        return Refused("disabled")
    repo.update_profile(
        conn,
        user.id,
        email=_new_email(conn, user, account),
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


def _new_email(conn: sqlite3.Connection, user: User, account: GoogleAccount) -> str:
    """Follow an email change at Google, unless the new address is unusable,
    another person already has it, or it is a Workspace address and this is a
    personal account (D26); then keep the stored one."""
    try:
        address = normalize_email(account.email)
    except Invalid:
        return user.email
    if address == user.email:
        return address
    if repo.email_taken(conn, address, other_than=user.id):
        log.warning("person %s: new email belongs to another person; kept the old one", user.id)
        return user.email
    if needs_workspace(conn, account, address):
        log.warning(
            "person %s: personal account moved to a Workspace address; kept the old one", user.id
        )
        return user.email
    return address
