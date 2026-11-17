"""Companies and memberships, and the only way to reach a company's file.

`open_company` checks membership in control.db before it hands out a Tenant,
so a handler can never touch a company the caller is not in. Unknown,
suspended and not-a-member all answer NotFound: the caller learns nothing
about companies they are not in.

TODO(M1-06): change role, remove member (never the last owner, KNOWN-DEVIATIONS #5).
TODO(M1-07): suspend, resume, delete to trash/.
"""

from __future__ import annotations

import json
import logging
import sqlite3
from dataclasses import dataclass
from typing import Literal

from tazko.core.clock import now_iso
from tazko.core.errors import AppError, Conflict, Forbidden, Invalid, NotFound
from tazko.db import Database
from tazko.db.tenant import Tenant, Tenants, valid_slug
from tazko.modules.audit import service as audit
from tazko.modules.orgs import repository as repo
from tazko.modules.orgs.repository import Membership, Org
from tazko.modules.users import service as users
from tazko.modules.users.service import User

__all__ = [
    "Company",
    "Membership",
    "Org",
    "add_member",
    "companies_of",
    "create_company",
    "has_member_email",
    "is_active",
    "join",
    "open_company",
    "require_manager",
]

log = logging.getLogger(__name__)

Role = Literal["owner", "member"]


@dataclass(frozen=True)
class Company:
    """A company opened for one person: their role and the company's own file."""

    org: Org
    role: str
    tenant: Tenant


def create_company(
    control: Database, tenants: Tenants, *, slug: str, name: str, actor_id: int | None
) -> Org:
    """Add the row, make data/orgs/<slug>/ with a migrated database, and audit it.

    The folder is made inside the control.db transaction, so a failure there
    leaves no row behind.
    """
    if not valid_slug(slug):
        raise Invalid("slug: use 1 to 40 lowercase letters, digits or inner hyphens", field="slug")
    name = name.strip()
    if not 1 <= len(name) <= 100:
        raise Invalid("name: 1 to 100 characters", field="name")

    def run(conn: sqlite3.Connection) -> Org:
        if repo.by_slug(conn, slug) or tenants.folder(slug).exists():
            raise Conflict("slug: already taken", code="SLUG_TAKEN", field="slug")
        org = repo.insert(conn, slug=slug, name=name, now=now_iso())
        audit.record(conn, "company.created", actor_id=actor_id, org_id=org.id, target=slug)
        tenants.create(slug)
        return org

    return control.write(run)


def add_member(
    control: Database,
    tenants: Tenants,
    *,
    org: Org,
    user: User,
    role: Role,
    actor_id: int | None,
) -> None:
    """Add (or change the role of) a member, and copy the person into the company file."""

    def membership(conn: sqlite3.Connection) -> None:
        repo.upsert_member(conn, org_id=org.id, user_id=user.id, role=role, now=now_iso())
        audit.record(
            conn,
            "member.added",
            actor_id=actor_id,
            org_id=org.id,
            target=user.email,
            detail={"role": role},
        )

    control.write(membership)

    # A second file, so a second transaction. The copy is an upsert: running it
    # again after a crash between the two writes repairs it (open_company does).
    _copy_person(tenants.get(org.slug), user, role=role, actor_id=actor_id, event="member.added")


def is_active(conn: sqlite3.Connection, org_id: int) -> bool:
    return repo.is_active(conn, org_id)


def has_member_email(conn: sqlite3.Connection, *, org_id: int, email: str) -> bool:
    return repo.has_member_email(conn, org_id=org_id, email=email)


def require_manager(conn: sqlite3.Connection, *, org_id: int, actor_id: int | None) -> None:
    """The actor may manage this company's people: a super admin or an owner.
    None is the command line or the system. A member gets Forbidden; anyone
    else NotFound, so they learn nothing about the company."""
    if actor_id is None:
        return
    found = repo.standing(conn, org_id=org_id, user_id=actor_id)
    if found is None:
        raise NotFound()
    is_super_admin, role = found
    if is_super_admin or role == "owner":
        return
    if role is None:
        raise NotFound()
    raise Forbidden("only an owner of the company can do this")


def join(conn: sqlite3.Connection, *, org_id: int, user: User, role: str, ip: str | None) -> bool:
    """Make the person a member inside the caller's control.db transaction
    (invite accepted at sign-in). An existing membership keeps its role.
    Their copy in the company file is made the first time they open it."""
    added = repo.insert_member_if_absent(
        conn, org_id=org_id, user_id=user.id, role=role, now=now_iso()
    )
    if added:
        audit.record(
            conn,
            "member.added",
            actor_id=user.id,
            org_id=org_id,
            target=user.email,
            detail={"role": role, "via": "invite"},
            ip=ip,
        )
    return added


def _copy_person(
    tenant: Tenant,
    user: User,
    *,
    role: str,
    actor_id: int | None,
    event: str,
    only_if_missing: bool = False,
) -> None:
    def run(conn: sqlite3.Connection) -> None:
        # Two first requests can both see the person missing; the writer
        # thread runs them one after the other, so check again here.
        if only_if_missing and repo.has_person(conn, user.id):
            return
        now = now_iso()
        repo.upsert_person(
            conn,
            user_id=user.id,
            name=user.name,
            email=user.email,
            avatar_url=user.avatar_url,
            now=now,
        )
        repo.add_event(
            conn,
            type=event,
            actor_id=actor_id,
            payload=json.dumps({"user_id": user.id, "role": role}),
            now=now,
        )

    tenant.db.write(run)


def companies_of(control: Database, user_id: int) -> list[Membership]:
    """The companies a person belongs to (for the switcher), by name."""
    return control.read(lambda c: repo.memberships(c, user_id))


def open_company(control: Database, tenants: Tenants, *, user_id: int, slug: str) -> Company:
    if not valid_slug(slug):
        raise NotFound()
    membership = control.read(lambda c: repo.active_membership(c, user_id, slug))
    if membership is None:
        raise NotFound()
    try:
        tenant = tenants.get(slug)
    except FileNotFoundError:
        log.error("company %s has a row but no database file", slug)
        raise AppError() from None
    if not tenant.db.read(lambda c: repo.has_person(c, user_id)):
        # Joined through an invite (control.db only) or a crash between the two
        # writes of add_member: copy the person in now. The one case where a GET
        # writes (D25): it only repairs the copy, never changes what they see.
        user = users.get(control, user_id)
        if user is None:
            raise NotFound()
        _copy_person(
            tenant,
            user,
            role=membership.role,
            actor_id=user_id,
            event="member.joined",
            only_if_missing=True,
        )
    return Company(org=membership.org, role=membership.role, tenant=tenant)
