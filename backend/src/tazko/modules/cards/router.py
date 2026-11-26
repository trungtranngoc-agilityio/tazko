"""Lists and cards under /api/orgs/{slug}/projects/{project_id}/boards/{board_id}.
Every check is in the service; routes only parse and shape."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Path, Response

from tazko.core.deps import CompanyDep, CurrentUser
from tazko.modules.cards import service
from tazko.modules.cards.schemas import (
    CardIn,
    CardOut,
    CardPatch,
    CardPosition,
    ListIn,
    ListOut,
    ListPatch,
    ListPosition,
)

router = APIRouter(prefix="/api/orgs/{slug}/projects/{project_id}/boards/{board_id}")

# SQLite integers: a bigger id would crash the query instead of answering 404.
RowId = Annotated[int, Path(ge=1, le=2**63 - 1)]


def _at(company: CompanyDep, user: CurrentUser, project_id: int, board_id: int) -> service.Where:
    return service.Where(company, user.id, project_id, board_id)


def _here(company: CompanyDep, project_id: int, board_id: int) -> str:
    return f"/api/orgs/{company.org.slug}/projects/{project_id}/boards/{board_id}"


@router.get("/lists")
def lists(
    project_id: RowId, board_id: RowId, company: CompanyDep, user: CurrentUser
) -> list[ListOut]:
    """The whole board: open lists in order with their open cards. A board
    holds at most 200 open lists and 5000 open cards, so this is bounded."""
    found = service.board_lists(_at(company, user, project_id, board_id))
    return [ListOut.of(lst) for lst in found]


@router.post("/lists", status_code=201)
def create_list(
    project_id: RowId,
    board_id: RowId,
    body: ListIn,
    response: Response,
    company: CompanyDep,
    user: CurrentUser,
) -> ListOut:
    made = service.create_list(_at(company, user, project_id, board_id), body.name)
    response.headers["Location"] = f"{_here(company, project_id, board_id)}/lists/{made.row.id}"
    return ListOut.of(made)


@router.get("/lists/{list_id}")
def get_list(
    project_id: RowId, board_id: RowId, list_id: RowId, company: CompanyDep, user: CurrentUser
) -> ListOut:
    return ListOut.of(service.get_list(_at(company, user, project_id, board_id), list_id))


@router.patch("/lists/{list_id}")
def update_list(
    project_id: RowId,
    board_id: RowId,
    list_id: RowId,
    body: ListPatch,
    company: CompanyDep,
    user: CurrentUser,
) -> ListOut:
    changed = service.update_list(
        _at(company, user, project_id, board_id), list_id, name=body.name, archived=body.archived
    )
    return ListOut.of(changed)


@router.put("/lists/{list_id}/position")
def move_list(
    project_id: RowId,
    board_id: RowId,
    list_id: RowId,
    body: ListPosition,
    company: CompanyDep,
    user: CurrentUser,
) -> ListOut:
    moved = service.move_list(_at(company, user, project_id, board_id), list_id, body.after_id)
    return ListOut.of(moved)


@router.post("/lists/{list_id}/cards", status_code=201)
def create_card(
    project_id: RowId,
    board_id: RowId,
    list_id: RowId,
    body: CardIn,
    response: Response,
    company: CompanyDep,
    user: CurrentUser,
) -> CardOut:
    made = service.create_card(_at(company, user, project_id, board_id), list_id, body.title)
    response.headers["Location"] = f"{_here(company, project_id, board_id)}/cards/{made.id}"
    return CardOut.of(made)


@router.get("/cards/{card_id}")
def get_card(
    project_id: RowId, board_id: RowId, card_id: RowId, company: CompanyDep, user: CurrentUser
) -> CardOut:
    return CardOut.of(service.get_card(_at(company, user, project_id, board_id), card_id))


@router.patch("/cards/{card_id}")
def update_card(
    project_id: RowId,
    board_id: RowId,
    card_id: RowId,
    body: CardPatch,
    company: CompanyDep,
    user: CurrentUser,
) -> CardOut:
    changed = service.update_card(
        _at(company, user, project_id, board_id), card_id, title=body.title, archived=body.archived
    )
    return CardOut.of(changed)


@router.put("/cards/{card_id}/position")
def move_card(
    project_id: RowId,
    board_id: RowId,
    card_id: RowId,
    body: CardPosition,
    company: CompanyDep,
    user: CurrentUser,
) -> CardOut:
    moved = service.move_card(
        _at(company, user, project_id, board_id),
        card_id,
        list_id=body.list_id,
        after_id=body.after_id,
    )
    return CardOut.of(moved)
