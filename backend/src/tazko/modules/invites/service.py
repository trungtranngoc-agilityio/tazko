"""Company invites (M1-05). An invite lets one email into one company, is valid
for 14 days, and works once. It is accepted when that email signs in.

Making and revoking check the actor here, in the service (a super admin or an
owner of the company; None is the command line), so the M1-06 routes cannot
forget it.
"""

from __future__ import annotations

import sqlite3
from datetime import timedelta
from typing import Literal, cast

from tazko.core import clock
from tazko.core.errors import Conflict, Invalid, NotFound
from tazko.db import Database
from tazko.modules.audit import service as audit
from tazko.modules.boards import service as boards
from tazko.modules.boards.service import ProjectRole
from tazko.modules.invites import repository as repo
from tazko.modules.invites.repository import Invite, PendingAnywhere, PendingInvite
from tazko.modules.orgs import service as orgs
from tazko.modules.orgs.service import Company, Org
from tazko.modules.users import service as users
from tazko.modules.users.service import User, normalize_email

__all__ = [
    "INVITE_DAYS",
    "Invite",
    "PendingAnywhere",
    "PendingInvite",
    "accept_usable",
    "account_kind",
    "create_invite",
    "create_project_invite",
    "has_usable",
    "list_everywhere",
    "list_pending",
    "list_project_invites",
    "revoke_anywhere",
    "revoke_for_leaver",
    "revoke_invite",
    "revoke_on_project_exit",
    "revoke_project_invite",
    "use_project_invites",
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


def list_everywhere(control: Database, *, actor_id: int) -> list[PendingAnywhere]:
    """Usable invites of every company, for the console. Super admins only."""

    def run(conn: sqlite3.Connection) -> list[PendingAnywhere]:
        orgs.require_super_admin(conn, actor_id)
        return repo.pending_everywhere(conn, now=clock.now_iso())

    return control.read(run)


def revoke_anywhere(control: Database, *, invite_id: int, actor_id: int, ip: str | None) -> None:
    """Revoke any company's invite from the console's Invites page."""

    def find(conn: sqlite3.Connection) -> Org | None:
        orgs.require_super_admin(conn, actor_id)
        invite = repo.by_id(conn, invite_id)
        return orgs.org_by_id(conn, invite.org_id) if invite else None

    org = control.read(find)
    if org is None:
        raise NotFound()
    revoke_invite(control, org=org, invite_id=invite_id, actor_id=actor_id, ip=ip)


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
        # A project invite is revoked under its project, with the project's check (D41).
        if invite is None or invite.org_id != org.id or invite.project_id is not None:
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
        if invite.project_id is not None:
            # A project invite joins the company now; its project part is used
            # when they open the company (use_project_invites), so it stays pending.
            orgs.join(conn, org_id=invite.org_id, user=user, role=invite.role, ip=ip)
            continue
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


# --- project invites (M2-02 part 3, D41) ------------------------------------------------
# The project rule is asked of the company file first (boards.check_*), then the
# invite is written in control.db, where sign-in can find it.

PROJECT_ROLES = ("owner", "member", "observer")


def create_project_invite(
    control: Database,
    company: Company,
    *,
    project_id: int,
    email: str,
    role: ProjectRole,
    actor_id: int,
    ip: str | None = None,
) -> PendingInvite:
    """Invite an email to one project as `role`. Someone not yet in the company
    joins it as a plain member when they sign in; a company member gets the
    project at their next request. One pending invite per email and project."""
    address = normalize_email(email)
    if role not in PROJECT_ROLES:
        raise Invalid("role: owner, member or observer", field="role")
    org = company.org
    member_id = control.read(lambda c: orgs.member_id_by_email(c, org_id=org.id, email=address))
    project = boards.check_inviter(
        company, actor_id=actor_id, project_id=project_id, role=role, member_id=member_id
    )
    now = clock.now()

    def run(conn: sqlite3.Connection) -> PendingInvite:
        _check_room(conn, org, project_id, address, clock.iso(now))
        invite = repo.insert(
            conn,
            org_id=org.id,
            email=address,
            role="member",
            project_id=project_id,
            project_role=role,
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
            detail={"role": "member", "project": project, "project_role": role},
            ip=ip,
        )
        return repo.pending_by_id(conn, invite.id)

    return control.write(run)


def _check_room(conn: sqlite3.Connection, org: Org, project_id: int, email: str, now: str) -> None:
    """Inside the invite's write: an active company, no pending invite for this
    email and project, and room on the pending list (every invite there can be
    seen and revoked, so it never grows past what the list shows)."""
    if not orgs.is_active(conn, org.id):
        raise Conflict("company: not active", code="COMPANY_NOT_ACTIVE")
    if repo.pending(conn, org_id=org.id, email=email, now=now, project_id=project_id):
        raise Conflict(
            "email: already has a pending invite to this project",
            code="INVITE_PENDING",
            field="email",
        )
    if repo.pending_count_for_project(conn, org_id=org.id, project_id=project_id, now=now) >= (
        repo.PENDING_CAP
    ):
        raise Conflict(
            f"project: {repo.PENDING_CAP} invites are pending; revoke some first",
            code="TOO_MANY_INVITES",
        )


def list_project_invites(
    control: Database, company: Company, *, project_id: int, actor_id: int
) -> list[PendingInvite]:
    boards.check_reader(company, actor_id=actor_id, project_id=project_id)
    return control.read(
        lambda c: repo.pending_for_project(c, company.org.id, project_id, now=clock.now_iso())
    )


def revoke_project_invite(
    control: Database,
    company: Company,
    *,
    project_id: int,
    invite_id: int,
    actor_id: int,
    ip: str | None = None,
) -> None:
    """Revoke an unused invite to this project. Another project's or a
    company invite: NotFound. Used or already revoked: Conflict."""
    org = company.org
    boards.check_reader(company, actor_id=actor_id, project_id=project_id)
    invite = control.read(lambda c: repo.by_id(c, invite_id))
    if invite is None or invite.org_id != org.id or invite.project_id != project_id:
        raise NotFound()
    role = cast(ProjectRole, invite.project_role)  # invites.project_role CHECK
    boards.check_revoker(company, actor_id=actor_id, project_id=project_id, role=role)

    def run(conn: sqlite3.Connection) -> None:
        if not repo.mark_revoked(conn, invite_id, org_id=org.id, now=clock.now_iso()):
            current = repo.by_id(conn, invite_id)
            used = current is not None and current.accepted_at is not None
            raise Conflict(
                "invite: already used" if used else "invite: already revoked",
                code="INVITE_USED" if used else "INVITE_REVOKED",
            )
        audit.record(
            conn,
            "invite.revoked",
            actor_id=actor_id,
            org_id=org.id,
            target=invite.email,
            detail={"project_id": project_id},
            ip=ip,
        )

    control.write(run)


def use_project_invites(control: Database, company: Company, user: User) -> None:
    """Each time a member opens the company: use their pending project invites.
    The project is joined first, then the invite marked used; if marking fails,
    the next request finds them in the project already and only marks it.

    Each invite is checked again now (boards.join_by_invite): its maker must
    still be allowed to make it, or it is revoked; on an archived project it
    waits. A personal account on a Workspace address uses none (D26), as at
    sign-in."""
    org = company.org

    def find(conn: sqlite3.Connection) -> list[Invite]:
        domain = user.email.rpartition("@")[2]
        if user.hd is None and users.is_workspace_domain(conn, domain):
            return []
        return repo.project_invites_to_use(
            conn, org_id=org.id, email=user.email, now=clock.now_iso()
        )

    for invite in control.read(find):
        outcome, project = boards.join_by_invite(
            control,
            company,
            user_id=user.id,
            project_id=cast(int, invite.project_id),
            role=cast(ProjectRole, invite.project_role),  # invites.project_role CHECK
            invited_by=invite.created_by,
        )
        if outcome == "void":
            _revoke_void(control, invite)
        elif outcome != "waiting":
            _mark_used(control, invite, user, project)


def _revoke_void(control: Database, invite: Invite) -> None:
    """Its maker may no longer invite as that role (left, demoted, or the
    project turned members_can_invite off): revoked, by nobody."""

    def run(conn: sqlite3.Connection) -> None:
        if repo.mark_revoked(conn, invite.id, org_id=invite.org_id, now=clock.now_iso()):
            audit.record(
                conn,
                "invite.revoked",
                actor_id=None,
                org_id=invite.org_id,
                target=invite.email,
                detail={"project_id": invite.project_id, "reason": "inviter_not_allowed"},
            )

    control.write(run)


def revoke_on_project_exit(
    control: Database, company: Company, *, project_id: int, user_id: int
) -> None:
    """After someone leaves a project or is removed from it: their pending
    invite to it would bring them back at their next request."""
    member = orgs.company_member(control, company, user_id)
    if member is None:
        return
    control.write(
        lambda c: repo.revoke_unused_for_project(
            c, org_id=company.org.id, email=member.email, project_id=project_id, now=clock.now_iso()
        )
    )


def _mark_used(control: Database, invite: Invite, user: User, project: str | None) -> None:
    def run(conn: sqlite3.Connection) -> None:
        if not repo.mark_accepted(conn, invite.id, user_id=user.id, now=clock.now_iso()):
            return  # another request used it a moment ago
        audit.record(
            conn,
            "invite.accepted",
            actor_id=user.id,
            org_id=invite.org_id,
            target=user.email,
            detail={"role": invite.role, "project": project, "project_role": invite.project_role},
        )

    control.write(run)


def revoke_for_leaver(conn: sqlite3.Connection, *, org_id: int, email: str) -> int:
    """Inside the company removal's control.db transaction: their unused
    invites to the company go too. Returns how many."""
    return repo.revoke_unused_for_email(conn, org_id=org_id, email=email, now=clock.now_iso())
