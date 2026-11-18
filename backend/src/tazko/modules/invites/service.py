"""Company invites (M1-05). An invite lets one email into one company, is valid
for 14 days, and works once. It is accepted when that email signs in.

Making and revoking check the actor here, in the service (a super admin or an
owner of the company; None is the command line), so the M1-06 routes cannot
forget it.
"""

from __future__ import annotations

import sqlite3
from datetime import timedelta
from typing import Literal

from tazko.core import clock
from tazko.core.errors import Conflict, Invalid, NotFound
from tazko.db import Database
from tazko.modules.audit import service as audit
from tazko.modules.invites import repository as repo
from tazko.modules.invites.repository import Invite, PendingInvite
from tazko.modules.orgs import service as orgs
from tazko.modules.orgs.service import Company, Org
from tazko.modules.users.service import User, normalize_email

__all__ = [
    "INVITE_DAYS",
    "Invite",
    "PendingInvite",
    "accept_usable",
    "account_kind",
    "create_invite",
    "has_usable",
    "list_pending",
    "revoke_invite",
    "why_unusable",
]

INVITE_DAYS = 14
# Addresses on these domains are always personal Google accounts.
PERSONAL_DOMAINS = frozenset({"gmail.com", "googlemail.com"})
AccountKind = Literal["workspace", "personal"]
ROLES = ("owner", "member")
Role = Literal["owner", "member"]


def create_invite(
    control: Database,
    *,
    org: Org,
    email: str,
    role: Role,
    actor_id: int | None,
    ip: str | None = None,
) -> PendingInvite:
    """One pending invite per email and company: a second one is a conflict
    (revoke the first to change its role). Returns it as the pending list shows it."""
    address = normalize_email(email)
    if role not in ROLES:
        raise Invalid("role: owner or member", field="role")
    now = clock.now()

    def run(conn: sqlite3.Connection) -> PendingInvite:
        orgs.require_manager(conn, org_id=org.id, actor_id=actor_id)
        if not orgs.is_active(conn, org.id):
            raise Conflict("company: not active", code="COMPANY_NOT_ACTIVE")
        if orgs.has_member_email(conn, org_id=org.id, email=address):
            raise Conflict(
                "email: already a member of the company", code="ALREADY_MEMBER", field="email"
            )
        if repo.pending(conn, org_id=org.id, email=address, now=clock.iso(now)):
            raise Conflict(
                "email: already has a pending invite", code="INVITE_PENDING", field="email"
            )
        invite = repo.insert(
            conn,
            org_id=org.id,
            email=address,
            role=role,
            created_by=actor_id,
            now=clock.iso(now),
            expires_at=clock.iso(now + timedelta(days=INVITE_DAYS)),
        )
        audit.record(
            conn,
            "invite.created",
            actor_id=actor_id,
            org_id=org.id,
            target=address,
            detail={"role": role},
            ip=ip,
        )
        return repo.pending_by_id(conn, invite.id)

    return control.write(run)


def account_kind(invite: PendingInvite) -> AccountKind | None:
    """What kind of Google account the address will sign in with, when we can
    tell: a known Workspace domain (D26), or a consumer Gmail domain."""
    if invite.workspace:
        return "workspace"
    if invite.email.rpartition("@")[2] in PERSONAL_DOMAINS:
        return "personal"
    return None


def list_pending(control: Database, company: Company, *, actor_id: int) -> list[PendingInvite]:
    """The company's usable invites, newest first. Owners and super admins only."""

    def run(conn: sqlite3.Connection) -> list[PendingInvite]:
        orgs.require_manager(conn, org_id=company.org.id, actor_id=actor_id)
        return repo.pending_for_org(conn, company.org.id, now=clock.now_iso())

    return control.read(run)


def revoke_invite(
    control: Database,
    *,
    org: Org,
    invite_id: int,
    actor_id: int | None,
    ip: str | None = None,
) -> None:
    """Revoke an invite of this company that nobody used yet. Unknown or
    another company's: NotFound. Used or already revoked: Conflict."""

    def run(conn: sqlite3.Connection) -> None:
        orgs.require_manager(conn, org_id=org.id, actor_id=actor_id)
        invite = repo.by_id(conn, invite_id)
        if invite is None or invite.org_id != org.id:
            raise NotFound()
        if invite.accepted_at:
            raise Conflict("invite: already used", code="INVITE_USED")
        if invite.revoked_at:
            raise Conflict("invite: already revoked", code="INVITE_REVOKED")
        repo.mark_revoked(conn, invite_id, org_id=org.id, now=clock.now_iso())
        audit.record(
            conn,
            "invite.revoked",
            actor_id=actor_id,
            org_id=invite.org_id,
            target=invite.email,
            ip=ip,
        )

    control.write(run)


# --- at sign-in, inside the sign-in transaction ---------------------------------------


def has_usable(conn: sqlite3.Connection, email: str) -> bool:
    return bool(repo.usable(conn, email, now=clock.now_iso()))


def why_unusable(
    conn: sqlite3.Connection, email: str
) -> Literal["invite_expired", "invite_revoked"] | None:
    """Why the newest unused invite for this email cannot be used, for the
    refusal audit row. None: there is none, or it is for a company that is
    not active (that is the company's state, not the invite's)."""
    invite = repo.latest_unused(conn, email)
    if invite is None:
        return None
    if invite.revoked_at:
        return "invite_revoked"
    if invite.expires_at <= clock.now_iso():
        return "invite_expired"
    return None


def accept_usable(conn: sqlite3.Connection, user: User, *, ip: str | None) -> list[Invite]:
    """Use every usable invite for this person's email: each one makes them a
    member of its company (an existing membership keeps its role) and is marked
    used, so it never works again. Returns the invites used."""
    now = clock.now_iso()
    used = []
    for invite in repo.usable(conn, user.email, now=now):
        if not repo.mark_accepted(conn, invite.id, user_id=user.id, now=now):
            continue
        orgs.join(conn, org_id=invite.org_id, user=user, role=invite.role, ip=ip)
        audit.record(
            conn,
            "invite.accepted",
            actor_id=user.id,
            org_id=invite.org_id,
            target=user.email,
            detail={"role": invite.role},
            ip=ip,
        )
        used.append(invite)
    return used
