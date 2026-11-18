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
from tazko.modules.orgs.repository import MemberRow, Membership, Org
from tazko.modules.users import service as users
from tazko.modules.users.service import User

__all__ = [
    "Company",
    "MemberRow",
    "Membership",
    "Org",
    "add_member",
    "change_role",
    "companies_of",
    "create_company",
    "has_member_email",
    "is_active",
    "join",
    "list_members",
    "open_company",
    "remove_member",
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
        _require_super_admin(conn, actor_id)
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
        require_manager(conn, org_id=org.id, actor_id=actor_id)
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


def _require_super_admin(conn: sqlite3.Connection, actor_id: int | None) -> None:
    if actor_id is None:
        return
    if not repo.is_enabled_super_admin(conn, actor_id):
        raise Forbidden("only a super admin can do this")


def list_members(control: Database, company: Company, *, actor_id: int) -> list[MemberRow]:
    def run(conn: sqlite3.Connection) -> list[MemberRow]:
        require_manager(conn, org_id=company.org.id, actor_id=actor_id)
        return repo.members(conn, company.org.id)

    return control.read(run)


def change_role(
    control: Database,
    company: Company,
    *,
    user_id: int,
    role: Role,
    actor_id: int | None,
    ip: str | None,
) -> MemberRow:
    """Change a member's role. The last owner is never demoted (409 LAST_OWNER);
    the check and the change are one transaction, so two owners demoting each
    other at once cannot leave the company without one."""
    org = company.org

    def run(conn: sqlite3.Connection) -> MemberRow:
        require_manager(conn, org_id=org.id, actor_id=actor_id)
        found = repo.member(conn, org.id, user_id)
        if found is None:
            raise NotFound()
        if found.role == role:
            return found
        if found.role == "owner" and repo.owner_count(conn, org.id) == 1:
            raise Conflict("the company needs at least one owner", code="LAST_OWNER")
        repo.set_role(conn, org_id=org.id, user_id=user_id, role=role)
        audit.record(
            conn,
            "member.role_changed",
            actor_id=actor_id,
            org_id=org.id,
            target=found.email,
            detail={"from": found.role, "to": role},
            ip=ip,
        )
        changed = repo.member(conn, org.id, user_id)
        if changed is None:
            raise RuntimeError("row vanished inside its own transaction")
        return changed

    changed = control.write(run)
    _company_event(
        company.tenant, "member.role_changed", actor_id, {"user_id": user_id, "role": role}
    )
    return changed


def remove_member(
    control: Database, company: Company, *, user_id: int, actor_id: int | None, ip: str | None
) -> None:
    """Take a person out of the company. Never the last owner (409 LAST_OWNER,
    KNOWN-DEVIATIONS #5). Their copy in the company file stays, so their name
    still shows on what they did."""
    org = company.org

    def run(conn: sqlite3.Connection) -> None:
        require_manager(conn, org_id=org.id, actor_id=actor_id)
        found = repo.member(conn, org.id, user_id)
        if found is None:
            raise NotFound()
        if found.role == "owner" and repo.owner_count(conn, org.id) == 1:
            raise Conflict("the company needs at least one owner", code="LAST_OWNER")
        repo.delete_member(conn, org_id=org.id, user_id=user_id)
        audit.record(
            conn,
            "member.removed",
            actor_id=actor_id,
            org_id=org.id,
            target=found.email,
            detail={"role": found.role},
            ip=ip,
        )

    control.write(run)
    _company_event(company.tenant, "member.removed", actor_id, {"user_id": user_id})


def _company_event(
    tenant: Tenant, kind: str, actor_id: int | None, payload: dict[str, object]
) -> None:
    """The company file's own record of a membership change (a second file, so a
    second transaction, after the control.db change committed)."""

    def run(conn: sqlite3.Connection) -> None:
        repo.add_event(
            conn, type=kind, actor_id=actor_id, payload=json.dumps(payload), now=now_iso()
        )

    tenant.db.write(run)


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
