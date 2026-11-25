"""Boards in a project: create, rename, close, restrict to chosen project
members, and personal stars. Who may open a project's boards is the
projects module's rule; who may see one board is access.sees_board."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass

from tazko.core.clock import now_iso
from tazko.core.errors import Invalid, NotFound
from tazko.db import events
from tazko.modules.boards import repository as repo
from tazko.modules.boards.repository import Board
from tazko.modules.orgs.service import Company
from tazko.modules.projects import service as projects
from tazko.modules.projects.access import Action, sees_board
from tazko.modules.projects.service import Seen

__all__ = ["Board", "SeenBoard"]


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
    """In this order, so a hidden board answers 404 to everything:
    may open the project's boards, then may see this one, then may do `action`."""
    seen = projects.require(conn, company, actor_id, project_id, "open_boards")
    board = repo.board(conn, project_id, board_id)
    if board is None or not sees_board(
        seen.role, restricted=board.restricted, listed=repo.listed(conn, board_id, actor_id)
    ):
        raise NotFound()
    if action != "open_boards":
        projects.require(conn, company, actor_id, project_id, action)
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
        seen = projects.require(conn, company, actor_id, project_id, "open_boards")
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
        projects.require(conn, company, actor_id, project_id, "open_boards")
        seen = projects.require(conn, company, actor_id, project_id, "create_board")
        board_id = repo.insert_board(
            conn,
            project_id=project_id,
            name=name,
            background=background or seen.project.default_background,
            created_by=actor_id,
            now=now_iso(),
        )
        events.add(conn, "board.created", actor_id, board_id=board_id, project_id=project_id)
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
            events.add(conn, "board.updated", actor_id, board_id=board_id, fields=sorted(changes))
        if archived is not None and archived != (board.archived_at is not None):
            repo.set_board_archived(conn, board_id, now_iso() if archived else None)
            events.add(
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
        outside = [p for p in listed if projects.role_of(conn, project_id, p) is None]
        if outside:
            raise Invalid(
                f"people: not in the project: {outside}",
                code="NOT_A_PROJECT_MEMBER",
                field="people",
            )
        unchanged = board.restricted == restricted and repo.access_list(conn, board_id) == listed
        if not unchanged:
            repo.set_access(conn, board_id, restricted=restricted, people=listed)
            events.add(
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
            events.add(
                conn, "board.starred" if on else "board.unstarred", actor_id, board_id=board_id
            )

    company.tenant.db.write(run)
