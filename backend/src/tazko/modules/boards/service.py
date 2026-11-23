"""Projects and project members (M2-02). Every rule is asked of access.decide
inside the write transaction, so a check and its change cannot be split by
another request (one writer thread per company). Every change writes one
events row in the same transaction (D38)."""

from __future__ import annotations

import json
import logging
import sqlite3
from dataclasses import dataclass
from typing import cast

from tazko.core.clock import now_iso
from tazko.core.errors import Conflict, Forbidden, Invalid, NotFound
from tazko.db import Database
from tazko.modules.audit import service as audit
from tazko.modules.boards import repository as repo
from tazko.modules.boards.access import Action, Decision, ProjectRole, Standing, decide
from tazko.modules.boards.repository import Member, Project, Summary
from tazko.modules.orgs import service as orgs
from tazko.modules.orgs.service import Company, MemberRow

__all__ = ["Member", "Project", "Summary"]

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class Seen:
    """A project as one person sees it: `role` is theirs, None if not in it."""

    project: Project
    role: ProjectRole | None


def _judge(
    conn: sqlite3.Connection, company: Company, actor_id: int, project_id: int, action: Action
) -> tuple[Seen | None, Decision]:
    project = repo.get(conn, project_id)
    if project is None:
        return None, "hide"
    role = cast(ProjectRole | None, repo.role_of(conn, project_id, actor_id))
    standing = Standing("owner" if company.role == "owner" else "member", role)
    verdict = decide(
        standing,
        action,
        archived=project.archived_at is not None,
        members_can_invite=project.members_can_invite,
        members_can_create_boards=project.members_can_create_boards,
    )
    return Seen(project, role), verdict


def _require(
    conn: sqlite3.Connection, company: Company, actor_id: int, project_id: int, action: Action
) -> Seen:
    seen, verdict = _judge(conn, company, actor_id, project_id, action)
    if seen is None or verdict == "hide":
        raise NotFound()
    if verdict == "forbid":
        raise Forbidden("your role in this project does not allow this")
    if verdict == "archived":
        raise Conflict("the project is archived", code="PROJECT_ARCHIVED")
    return seen


def _event(conn: sqlite3.Connection, kind: str, actor_id: int, **payload: object) -> None:
    repo.add_event(conn, type=kind, actor_id=actor_id, payload=json.dumps(payload), now=now_iso())


def _company_member(control: Database, company: Company, user_id: int, field: str) -> MemberRow:
    """Read only: the person must be in the company. Their copy in the company
    file is made inside the write, after the permission check (orgs.copy_person)."""
    found = orgs.company_member(control, company, user_id)
    if found is None:
        raise Invalid(
            f"{field}: not a member of the company", code="NOT_A_COMPANY_MEMBER", field=field
        )
    return found


# --- projects ----------------------------------------------------------------------


def create(
    control: Database,
    company: Company,
    *,
    actor_id: int,
    name: str,
    description: str,
    color: str | None,
    owner_id: int,
) -> Seen:
    """Only company owners create projects, each with its first owner."""
    if company.role != "owner":
        raise Forbidden("only an owner of the company can create a project")
    owner = _company_member(control, company, owner_id, "owner_id")

    def run(conn: sqlite3.Connection) -> Seen:
        orgs.copy_person(conn, owner)
        now = now_iso()
        project_id = repo.insert(
            conn, name=name, description=description, color=color, created_by=actor_id, now=now
        )
        repo.add_member(conn, project_id=project_id, person_id=owner_id, role="owner", now=now)
        _event(conn, "project.created", actor_id, project_id=project_id, owner_id=owner_id)
        project = repo.get(conn, project_id)
        if project is None:
            raise RuntimeError("row vanished inside its own transaction")
        return Seen(project, "owner" if owner_id == actor_id else None)

    seen = company.tenant.db.write(run)
    _audit_company_owner(control, company, actor_id, owner, seen.project.name, "owner", None)
    return seen


def mine(company: Company, *, actor_id: int) -> list[Seen]:
    rows = company.tenant.db.read(lambda c: repo.of_person(c, actor_id))
    return [Seen(project, cast(ProjectRole, role)) for project, role in rows]


def manage_view(company: Company) -> list[Summary]:
    if company.role != "owner":
        raise Forbidden("only an owner of the company can manage projects")
    return company.tenant.db.read(repo.summaries)


def get(company: Company, *, actor_id: int, project_id: int) -> Seen:
    return company.tenant.db.read(lambda c: _require(c, company, actor_id, project_id, "view"))


def update(
    company: Company,
    *,
    actor_id: int,
    project_id: int,
    changes: dict[str, object],
    archived: bool | None,
) -> Seen:
    """Settings need a project owner; archiving and restoring need a company
    owner; the name either of them."""

    def run(conn: sqlite3.Connection) -> Seen:
        current = _require(conn, company, actor_id, project_id, "view").project
        if archived is not None and archived != (current.archived_at is not None):
            _require(conn, company, actor_id, project_id, "manage")
            at = now_iso() if archived else None
            repo.set_archived(conn, project_id, at)
            _event(
                conn,
                "project.archived" if archived else "project.restored",
                actor_id,
                project_id=project_id,
            )
        if changes:
            _require_settings(conn, company, actor_id, project_id, set(changes))
            repo.update(conn, project_id, changes)
            _event(conn, "project.updated", actor_id, project_id=project_id, fields=sorted(changes))
        return _require(conn, company, actor_id, project_id, "view")

    return company.tenant.db.write(run)


def _require_settings(
    conn: sqlite3.Connection, company: Company, actor_id: int, project_id: int, fields: set[str]
) -> None:
    """The name is Manage projects' rename too; every other field is a project owner's."""
    if fields == {"name"} and _judge(conn, company, actor_id, project_id, "manage")[1] == "allow":
        return
    _require(conn, company, actor_id, project_id, "edit_settings")


def delete(company: Company, *, actor_id: int, project_id: int) -> None:
    """To trash: hidden from everyone at once, removed for good after 30 days."""

    def run(conn: sqlite3.Connection) -> None:
        _require(conn, company, actor_id, project_id, "manage")
        repo.mark_deleted(conn, project_id, now_iso())
        _event(conn, "project.deleted", actor_id, project_id=project_id)

    company.tenant.db.write(run)


# --- members ------------------------------------------------------------------------


def members(company: Company, *, actor_id: int, project_id: int) -> list[Member]:
    def run(conn: sqlite3.Connection) -> list[Member]:
        _require(conn, company, actor_id, project_id, "list_members")
        return repo.members(conn, project_id)

    return company.tenant.db.read(run)


def add_member(
    control: Database,
    company: Company,
    *,
    actor_id: int,
    project_id: int,
    user_id: int,
    role: ProjectRole,
    ip: str | None,
) -> Member:
    """Add a company member. A company owner joining is audit-logged."""
    target = _company_member(control, company, user_id, "user_id")

    def run(conn: sqlite3.Connection) -> tuple[Member, str]:
        seen = _require(
            conn,
            company,
            actor_id,
            project_id,
            "manage_owners" if role == "owner" else "add_member",
        )
        if repo.role_of(conn, project_id, user_id) is not None:
            raise Conflict("already in the project", code="ALREADY_PROJECT_MEMBER")
        orgs.copy_person(conn, target)
        repo.add_member(conn, project_id=project_id, person_id=user_id, role=role, now=now_iso())
        _event(
            conn,
            "project.member_added",
            actor_id,
            project_id=project_id,
            user_id=user_id,
            role=role,
        )
        added = repo.member(conn, project_id, user_id)
        if added is None:
            raise RuntimeError("row vanished inside its own transaction")
        return added, seen.project.name

    added, name = company.tenant.db.write(run)
    _audit_company_owner(control, company, actor_id, target, name, role, ip)
    return added


def _audit_company_owner(
    control: Database,
    company: Company,
    actor_id: int,
    target: MemberRow,
    project: str,
    role: str,
    ip: str | None,
) -> None:
    """A company owner who joins a project can open its boards (build plan,
    Projects), so it is audit-logged however they join: by adding themselves
    (project.self_added, target the project), by being added, or by a project
    made with them as owner (project.company_owner_added, target their email)."""
    if target.role != "owner":
        return
    itself = target.user_id == actor_id
    action = "project.self_added" if itself else "project.company_owner_added"

    def run(conn: sqlite3.Connection) -> None:
        audit.record(
            conn,
            action,
            actor_id=actor_id,
            org_id=company.org.id,
            target=project if itself else target.email,
            detail={"role": role} if itself else {"role": role, "project": project},
            ip=ip,
        )

    try:
        control.write(run)
    except Exception:
        # The person is in; the company file's events row has it. Log, do not fail (D39).
        log.exception("audit row %s not written", action)


def change_role(
    company: Company, *, actor_id: int, project_id: int, user_id: int, role: ProjectRole
) -> Member:
    def run(conn: sqlite3.Connection) -> Member:
        found = _target(conn, company, actor_id, project_id, user_id, also=role)
        if found.role != role:
            _keep_an_owner(conn, project_id, found, role)
            repo.set_role(conn, project_id=project_id, person_id=user_id, role=role)
            _event(
                conn,
                "project.role_changed",
                actor_id,
                project_id=project_id,
                user_id=user_id,
                role=role,
                previous=found.role,
            )
        changed = repo.member(conn, project_id, user_id)
        if changed is None:
            raise RuntimeError("row vanished inside its own transaction")
        return changed

    return company.tenant.db.write(run)


def remove_member(company: Company, *, actor_id: int, project_id: int, user_id: int) -> None:
    """D6: they come off the project's card assignees, watchers and restricted
    boards; what they made stays."""

    def run(conn: sqlite3.Connection) -> None:
        if user_id == actor_id:  # leaving: anyone in the project may; the UI asks first (D4)
            found = _require_member(conn, company, actor_id, project_id, user_id)
        else:
            found = _target(conn, company, actor_id, project_id, user_id, also=None)
        _keep_an_owner(conn, project_id, found, None)
        repo.remove_member(conn, project_id=project_id, person_id=user_id)
        _event(conn, "project.member_removed", actor_id, project_id=project_id, user_id=user_id)

    company.tenant.db.write(run)


def _target(
    conn: sqlite3.Connection,
    company: Company,
    actor_id: int,
    project_id: int,
    user_id: int,
    *,
    also: ProjectRole | None,
) -> Member:
    """The member to change, after checking the actor may touch their role
    (owners are managed by company owners too)."""
    found = _require_member(conn, company, actor_id, project_id, user_id)
    owners = "owner" in (found.role, also)
    _require(conn, company, actor_id, project_id, "manage_owners" if owners else "manage_members")
    return found


def _keep_an_owner(
    conn: sqlite3.Connection, project_id: int, found: Member, role: ProjectRole | None
) -> None:
    """KNOWN-DEVIATIONS #5: a project always keeps an owner."""
    if found.role == "owner" and role != "owner" and repo.owner_count(conn, project_id) == 1:
        raise Conflict("the project needs at least one owner", code="LAST_OWNER")


def _require_member(
    conn: sqlite3.Connection, company: Company, actor_id: int, project_id: int, user_id: int
) -> Member:
    _require(conn, company, actor_id, project_id, "list_members")
    found = repo.member(conn, project_id, user_id)
    if found is None:
        raise NotFound()
    return found


def leave_company(conn: sqlite3.Connection, *, person_id: int, actor_id: int | None) -> None:
    """Inside the caller's transaction on the company file: someone removed
    from the company leaves each of its projects (D6), one event per project.
    A project they owned alone keeps no owner; company owners add one (D39)."""
    for project_id in repo.projects_of_any_state(conn, person_id):
        repo.remove_member(conn, project_id=project_id, person_id=person_id)
        repo.add_event(
            conn,
            type="project.member_removed",
            actor_id=actor_id,
            payload=json.dumps(
                {"project_id": project_id, "user_id": person_id, "reason": "left_company"}
            ),
            now=now_iso(),
        )
