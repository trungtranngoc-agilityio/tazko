"""Boards under /api/orgs/{slug}/projects/{project_id}/boards. Every check is
in the service; routes only parse and shape."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Path, Response

from tazko.core.deps import CompanyDep, CurrentUser
from tazko.modules.boards import service
from tazko.modules.boards.schemas import AccessIn, BoardIn, BoardOut, BoardPatch

router = APIRouter(prefix="/api/orgs/{slug}/projects")
starred_router = APIRouter(prefix="/api/orgs/{slug}")

# SQLite integers: a bigger id would crash the query instead of answering 404.
ProjectId = Annotated[int, Path(ge=1, le=2**63 - 1)]
BoardId = Annotated[int, Path(ge=1, le=2**63 - 1)]


@starred_router.get("/starred-boards")
def starred_boards(company: CompanyDep, user: CurrentUser) -> list[BoardOut]:
    """The open boards you starred and may still open, across your projects; at most 500, by name."""
    return [BoardOut.of(seen) for seen in service.starred(company, actor_id=user.id)]


@router.get("/{project_id}/boards")
def boards(project_id: ProjectId, company: CompanyDep, user: CurrentUser) -> list[BoardOut]:
    """The boards you may see, closed ones included; at most 500, by name.
    A restricted board you are not on does not appear."""
    rows = service.boards(company, actor_id=user.id, project_id=project_id)
    return [BoardOut.of(row) for row in rows]


@router.post("/{project_id}/boards", status_code=201)
def create_board(
    project_id: ProjectId, body: BoardIn, response: Response, company: CompanyDep, user: CurrentUser
) -> BoardOut:
    seen = service.create_board(
        company, actor_id=user.id, project_id=project_id, name=body.name, background=body.background
    )
    response.headers["Location"] = (
        f"/api/orgs/{company.org.slug}/projects/{project_id}/boards/{seen.board.id}"
    )
    return BoardOut.of(seen)


@router.get("/{project_id}/boards/{board_id}")
def board(
    project_id: ProjectId, board_id: BoardId, company: CompanyDep, user: CurrentUser
) -> BoardOut:
    seen = service.get_board(company, actor_id=user.id, project_id=project_id, board_id=board_id)
    return BoardOut.of(seen)


@router.patch("/{project_id}/boards/{board_id}")
def update_board(
    project_id: ProjectId,
    board_id: BoardId,
    body: BoardPatch,
    company: CompanyDep,
    user: CurrentUser,
) -> BoardOut:
    seen = service.update_board(
        company,
        actor_id=user.id,
        project_id=project_id,
        board_id=board_id,
        changes=body.changes(),
        archived=body.archived,
    )
    return BoardOut.of(seen)


@router.put("/{project_id}/boards/{board_id}/access")
def set_access(
    project_id: ProjectId,
    board_id: BoardId,
    body: AccessIn,
    company: CompanyDep,
    user: CurrentUser,
) -> BoardOut:
    seen = service.set_access(
        company,
        actor_id=user.id,
        project_id=project_id,
        board_id=board_id,
        restricted=body.restricted,
        people=body.people,
    )
    return BoardOut.of(seen)


@router.put("/{project_id}/boards/{board_id}/star", status_code=204)
def star(
    project_id: ProjectId, board_id: BoardId, company: CompanyDep, user: CurrentUser
) -> Response:
    service.star(company, actor_id=user.id, project_id=project_id, board_id=board_id, on=True)
    return Response(status_code=204)


@router.delete("/{project_id}/boards/{board_id}/star", status_code=204)
def unstar(
    project_id: ProjectId, board_id: BoardId, company: CompanyDep, user: CurrentUser
) -> Response:
    service.star(company, actor_id=user.id, project_id=project_id, board_id=board_id, on=False)
    return Response(status_code=204)
