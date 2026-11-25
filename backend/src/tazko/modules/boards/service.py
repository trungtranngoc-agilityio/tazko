"""Projects and project members (M2-02). Every rule is asked of access.decide
inside the write transaction, so a check and its change cannot be split by
another request (one writer thread per company). Every change writes one
events row in the same transaction (D38)."""

from __future__ import annotations

import json
import logging
import sqlite3
from dataclasses import dataclass
from typing import Literal, cast

from tazko.core.clock import now_iso
from tazko.core.errors import Conflict, Forbidden, Invalid, NotFound
from tazko.db import Database
from tazko.modules.audit import service as audit
from tazko.modules.boards import repository as repo
from tazko.modules.boards.access import Action, Decision, ProjectRole, Standing, decide, sees_board
from tazko.modules.boards.repository import Board, Member, Project, Summary
from tazko.modules.orgs import service as orgs
from tazko.modules.orgs.service import Company, MemberRow

__all__ = ["Board", "Member", "Project", "ProjectRole", "Summary"]

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
    if verdict == "forbid" and action == "open_boards" and seen.role is None:
        # A company owner who manages the project but is not in it (build plan, Projects).
        raise Forbidden("add yourself to the project to open its boards", code="NOT_IN_PROJECT")
    if verdict == "forbid":
        raise Forbidden("your role in this project does not allow this")
    if verdict == "archived":
        raise Conflict("the project is archived", code="PROJECT_ARCHIVED")
    return seen


def _event(
    conn: sqlite3.Connection,
    kind: str,
    actor_id: int,
    *,
    board_id: int | None = None,
    **payload: object,
) -> None:
    repo.add_event(
        conn,
        type=kind,
        actor_id=actor_id,
        board_id=board_id,
        payload=json.dumps(payload),
        now=now_iso(),
    )


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
    joining_owner = user_id == actor_id and company.role == "owner"

    def run(conn: sqlite3.Connection) -> tuple[Member, str]:
        seen = _require(
            conn,
            company,
            actor_id,
            project_id,
            # A company owner may join with any role: they could join as owner anyway.
            "manage_owners" if role == "owner" or joining_owner else "add_member",
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


# --- project invites (part 3, D41): the invite lives in control.db ---------------------------


def _invite_action(role: ProjectRole) -> Action:
    """Inviting someone as `role` needs the same right as adding them."""
    return "manage_owners" if role == "owner" else "add_member"


def check_inviter(
    company: Company, *, actor_id: int, project_id: int, role: ProjectRole, member_id: int | None
) -> str:
    """May the actor invite someone as `role`? `member_id`: the company member
    with that email, if any, who must not be in the project already. Returns
    the project's name."""

    def run(conn: sqlite3.Connection) -> str:
        seen = _require(conn, company, actor_id, project_id, _invite_action(role))
        if member_id is not None and repo.role_of(conn, project_id, member_id) is not None:
            raise Conflict("already in the project", code="ALREADY_PROJECT_MEMBER", field="email")
        return seen.project.name

    return company.tenant.db.read(run)


def check_revoker(company: Company, *, actor_id: int, project_id: int, role: ProjectRole) -> None:
    company.tenant.db.read(
        lambda c: _require(c, company, actor_id, project_id, _invite_action(role))
    )


def check_reader(company: Company, *, actor_id: int, project_id: int) -> None:
    """Pending invites show to everyone in the project, as its members do."""
    company.tenant.db.read(lambda c: _require(c, company, actor_id, project_id, "list_members"))


# What using an invite came to: "joined"; "in_project" already; "gone", the
# project was deleted; "waiting", it is archived (used once restored); "void",
# the inviter may no longer invite as that role (D41).
JoinOutcome = Literal["joined", "in_project", "gone", "waiting", "void"]


def _inviter_still_may(
    conn: sqlite3.Connection,
    project: Project,
    inviter: MemberRow | None,
    role: ProjectRole,
) -> bool:
    """The invite is only as good as its maker's right today: still in the
    company, still allowed to add someone as `role`, switches included."""
    if inviter is None:
        return False
    standing = Standing(
        "owner" if inviter.role == "owner" else "member",
        cast(ProjectRole | None, repo.role_of(conn, project.id, inviter.user_id)),
    )
    verdict = decide(
        standing,
        _invite_action(role),
        members_can_invite=project.members_can_invite,
        members_can_create_boards=project.members_can_create_boards,
    )
    return verdict == "allow"


def join_by_invite(
    control: Database,
    company: Company,
    *,
    user_id: int,
    project_id: int,
    role: ProjectRole,
    invited_by: int | None,
) -> tuple[JoinOutcome, str | None]:
    """The invited company member joins the project. Returns what happened and
    the project's name. A company owner joining is audit-logged as being added
    by the inviter."""
    target = orgs.company_member(control, company, user_id)
    inviter = orgs.company_member(control, company, invited_by) if invited_by else None
    if target is None:
        return "gone", None

    def run(conn: sqlite3.Connection) -> tuple[JoinOutcome, str | None]:
        project = repo.get(conn, project_id)
        if project is None:
            return "gone", None
        if repo.role_of(conn, project_id, user_id) is not None:
            return "in_project", project.name
        if project.archived_at is not None:
            return "waiting", project.name
        if not _inviter_still_may(conn, project, inviter, role):
            return "void", project.name
        orgs.copy_person(conn, target)
        repo.add_member(conn, project_id=project_id, person_id=user_id, role=role, now=now_iso())
        _event(
            conn,
            "project.member_added",
            user_id,
            project_id=project_id,
            user_id=user_id,
            role=role,
            via="invite",
            invited_by=invited_by,
        )
        return "joined", project.name

    outcome, name = company.tenant.db.write(run)
    if outcome == "joined" and name is not None:
        _audit_company_owner(control, company, invited_by, target, name, role, None)
    return outcome, name


def _audit_company_owner(
    control: Database,
    company: Company,
    actor_id: int | None,
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
    _audit(
        control,
        company,
        "project.self_added" if itself else "project.company_owner_added",
        actor_id,
        project if itself else target.email,
        {"role": role} if itself else {"role": role, "project": project},
        ip,
    )


def _audit(
    control: Database,
    company: Company,
    action: str,
    actor_id: int | None,
    target: str,
    detail: dict[str, object],
    ip: str | None,
) -> None:
    """After the company file committed: logged, not failed, if it cannot be written (D39)."""

    def run(conn: sqlite3.Connection) -> None:
        audit.record(
            conn,
            action,
            actor_id=actor_id,
            org_id=company.org.id,
            target=target,
            detail=detail,
            ip=ip,
        )

    try:
        control.write(run)
    except Exception:
        log.exception("audit row %s not written", action)


def change_role(
    control: Database,
    company: Company,
    *,
    actor_id: int,
    project_id: int,
    user_id: int,
    role: ProjectRole,
    ip: str | None,
) -> Member:
    """A company owner making themselves a project owner is audit-logged: a
    project owner sees every restricted board (D40)."""

    def run(conn: sqlite3.Connection) -> tuple[Member, str, bool]:
        found = _target(conn, company, actor_id, project_id, user_id, also=role)
        promoted = found.role != "owner" and role == "owner"
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
        project = repo.get(conn, project_id)
        return changed, project.name if project else "", promoted

    changed, name, promoted = company.tenant.db.write(run)
    if promoted and user_id == actor_id and company.role == "owner":
        _audit(control, company, "project.self_promoted", actor_id, name, {"role": role}, ip)
    return changed


def remove_member(
    control: Database, company: Company, *, actor_id: int, project_id: int, user_id: int
) -> None:
    """D6: they come off the project's card assignees, watchers and restricted
    boards; what they made stays. A pending invite to the project goes too,
    so it cannot bring them back (D41)."""

    def run(conn: sqlite3.Connection) -> None:
        if user_id == actor_id:  # leaving: anyone in the project may; the UI asks first (D4)
            found = _require_member(conn, company, actor_id, project_id, user_id)
        else:
            found = _target(conn, company, actor_id, project_id, user_id, also=None)
        _keep_an_owner(conn, project_id, found, None)
        repo.remove_member(conn, project_id=project_id, person_id=user_id)
        _event(conn, "project.member_removed", actor_id, project_id=project_id, user_id=user_id)

    company.tenant.db.write(run)
    from tazko.modules.invites import service as invites  # it imports this module

    invites.revoke_on_project_exit(control, company, project_id=project_id, user_id=user_id)


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


# --- boards (M2-02 part 2) ----------------------------------------------------------------


@dataclass(frozen=True)
class SeenBoard:
    """A board as one person sees it. `access` (the restricted list) is shown
    to project owners only, who manage it."""

    board: Board
    starred: bool
    access: list[int] | None


def _require_board(
    conn: sqlite3.Connection,
    company: Company,
    actor_id: int,
    project_id: int,
    board_id: int,
    action: Action,
) -> tuple[Seen, Board]:
    """In this order, so a hidden board answers 404 to everything (KNOWN-DEVIATIONS #1):
    may open the project's boards, then may see this one, then may do `action`."""
    seen = _require(conn, company, actor_id, project_id, "open_boards")
    board = repo.board(conn, project_id, board_id)
    if board is None or not sees_board(
        seen.role, restricted=board.restricted, listed=repo.listed(conn, board_id, actor_id)
    ):
        raise NotFound()
    if action != "open_boards":
        _require(conn, company, actor_id, project_id, action)
    return seen, board


def _reload_board(conn: sqlite3.Connection, project_id: int, board_id: int) -> Board:
    board = repo.board(conn, project_id, board_id)
    if board is None:
        raise RuntimeError("row vanished inside its own transaction")
    return board


def _seen_board(conn: sqlite3.Connection, seen: Seen, board: Board, actor_id: int) -> SeenBoard:
    access = repo.access_list(conn, board.id) if seen.role == "owner" and board.restricted else None
    return SeenBoard(board, repo.starred(conn, board.id, actor_id), access)


def boards(company: Company, *, actor_id: int, project_id: int) -> list[SeenBoard]:
    def run(conn: sqlite3.Connection) -> list[SeenBoard]:
        seen = _require(conn, company, actor_id, project_id, "open_boards")
        owner = seen.role == "owner"
        rows = repo.boards_seen(conn, project_id, actor_id, every_restricted=owner)
        lists = repo.access_lists(conn, project_id) if owner else {}
        return [
            SeenBoard(b, starred, lists.get(b.id, []) if owner and b.restricted else None)
            for b, starred in rows
        ]

    return company.tenant.db.read(run)


def create_board(
    company: Company, *, actor_id: int, project_id: int, name: str, background: str | None
) -> SeenBoard:
    """A new board is open to the whole project and takes the project's
    default background unless given one."""

    def run(conn: sqlite3.Connection) -> SeenBoard:
        _require(conn, company, actor_id, project_id, "open_boards")
        seen = _require(conn, company, actor_id, project_id, "create_board")
        board_id = repo.insert_board(
            conn,
            project_id=project_id,
            name=name,
            background=background or seen.project.default_background,
            created_by=actor_id,
            now=now_iso(),
        )
        _event(conn, "board.created", actor_id, board_id=board_id, project_id=project_id)
        return _seen_board(conn, seen, _reload_board(conn, project_id, board_id), actor_id)

    return company.tenant.db.write(run)


def get_board(company: Company, *, actor_id: int, project_id: int, board_id: int) -> SeenBoard:
    def run(conn: sqlite3.Connection) -> SeenBoard:
        seen, board = _require_board(conn, company, actor_id, project_id, board_id, "open_boards")
        return _seen_board(conn, seen, board, actor_id)

    return company.tenant.db.read(run)


def update_board(
    company: Company,
    *,
    actor_id: int,
    project_id: int,
    board_id: int,
    changes: dict[str, object],
    archived: bool | None,
) -> SeenBoard:
    """Rename, change the background, close ("archive") or reopen: project
    owners and members."""

    def run(conn: sqlite3.Connection) -> SeenBoard:
        seen, board = _require_board(conn, company, actor_id, project_id, board_id, "edit_board")
        if changes:
            repo.update_board(conn, board_id, changes)
            _event(conn, "board.updated", actor_id, board_id=board_id, fields=sorted(changes))
        if archived is not None and archived != (board.archived_at is not None):
            repo.set_board_archived(conn, board_id, now_iso() if archived else None)
            _event(
                conn,
                "board.archived" if archived else "board.restored",
                actor_id,
                board_id=board_id,
            )
        return _seen_board(conn, seen, _reload_board(conn, project_id, board_id), actor_id)

    return company.tenant.db.write(run)


def set_access(
    company: Company,
    *,
    actor_id: int,
    project_id: int,
    board_id: int,
    restricted: bool,
    people: list[int],
) -> SeenBoard:
    """Project owners restrict a board to chosen project members, or open it
    to the whole project again (the list is then cleared)."""

    if not restricted and people:
        raise Invalid("people: an open board has no list", field="people")
    listed = sorted(set(people))

    def run(conn: sqlite3.Connection) -> SeenBoard:
        seen, board = _require_board(
            conn, company, actor_id, project_id, board_id, "restrict_board"
        )
        outside = [p for p in listed if repo.role_of(conn, project_id, p) is None]
        if outside:
            raise Invalid(
                f"people: not in the project: {outside}",
                code="NOT_A_PROJECT_MEMBER",
                field="people",
            )
        unchanged = board.restricted == restricted and repo.access_list(conn, board_id) == listed
        if not unchanged:
            repo.set_access(conn, board_id, restricted=restricted, people=listed)
            _event(
                conn,
                "board.access_changed",
                actor_id,
                board_id=board_id,
                restricted=restricted,
                people=listed,
            )
        return _seen_board(conn, seen, _reload_board(conn, project_id, board_id), actor_id)

    return company.tenant.db.write(run)


def star(company: Company, *, actor_id: int, project_id: int, board_id: int, on: bool) -> None:
    """Personal: anyone who may open the board, observers too, also on an
    archived project. Starring twice changes nothing."""

    def run(conn: sqlite3.Connection) -> None:
        _require_board(conn, company, actor_id, project_id, board_id, "open_boards")
        if repo.set_star(conn, board_id, actor_id, on=on, now=now_iso()):
            _event(conn, "board.starred" if on else "board.unstarred", actor_id, board_id=board_id)

    company.tenant.db.write(run)
