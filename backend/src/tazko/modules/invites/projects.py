"""Invites to one project. The invite lives in control.db, where sign-in
finds it; who may make, see or revoke one is the project's rule
(projects.check_*), asked of the company file first."""

from __future__ import annotations

import sqlite3
from datetime import timedelta
from typing import cast

from tazko.core import clock
from tazko.core.errors import Conflict, Invalid, NotFound
from tazko.db import Database
from tazko.modules.audit import service as audit
from tazko.modules.invites import repository as repo
from tazko.modules.invites.repository import Invite, PendingInvite
from tazko.modules.invites.service import INVITE_DAYS
from tazko.modules.orgs import service as orgs
from tazko.modules.orgs.service import Company, Org
from tazko.modules.projects import service as projects
from tazko.modules.projects.service import ProjectRole
from tazko.modules.users import service as users
from tazko.modules.users.service import User, normalize_email

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
    project = projects.check_inviter(
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
    projects.check_reader(company, actor_id=actor_id, project_id=project_id)
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
    projects.check_reader(company, actor_id=actor_id, project_id=project_id)
    invite = control.read(lambda c: repo.by_id(c, invite_id))
    if invite is None or invite.org_id != org.id or invite.project_id != project_id:
        raise NotFound()
    role = cast(ProjectRole, invite.project_role)  # invites.project_role CHECK
    projects.check_revoker(company, actor_id=actor_id, project_id=project_id, role=role)

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

    Each invite is checked again now (projects.join_by_invite): its maker must
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
        outcome, project = projects.join_by_invite(
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
