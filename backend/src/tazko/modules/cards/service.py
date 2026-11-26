"""Lists and cards on a board. Reading needs only the board; every change
needs `edit_cards` (project owners and members, never observers), an open
project and an open board. A board someone may not see answers 404 to all of it."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass

from tazko.core.clock import now_iso
from tazko.core.errors import Conflict, Invalid, NotFound
from tazko.db import events, rank
from tazko.modules.boards import service as boards
from tazko.modules.cards import repository as repo
from tazko.modules.cards.repository import Card, List
from tazko.modules.orgs.service import Company

__all__ = ["Card", "List", "ListWithCards", "Where"]


@dataclass(frozen=True)
class ListWithCards:
    row: List
    cards: list[Card]


@dataclass(frozen=True)
class Where:
    """The company, the person and the board a call is about."""

    company: Company
    actor_id: int
    project_id: int
    board_id: int


def _open(conn: sqlite3.Connection, at: Where) -> None:
    boards.require_board(conn, at.company, at.actor_id, at.project_id, at.board_id, "open_boards")


def _edit(conn: sqlite3.Connection, at: Where) -> None:
    _, board = boards.require_board(
        conn, at.company, at.actor_id, at.project_id, at.board_id, "edit_cards"
    )
    if board.archived_at is not None:
        raise Conflict("the board is closed", code="BOARD_CLOSED")


def _list(conn: sqlite3.Connection, board_id: int, list_id: int) -> List:
    found = repo.list_of(conn, board_id, list_id)
    if found is None:
        raise NotFound()
    return found


def _card(conn: sqlite3.Connection, board_id: int, card_id: int) -> Card:
    found = repo.card_of(conn, board_id, card_id)
    if found is None:
        raise NotFound()
    return found


def _with_cards(conn: sqlite3.Connection, found: List) -> ListWithCards:
    return ListWithCards(found, repo.cards_of_list(conn, found.id))


def _live_card(conn: sqlite3.Connection, board_id: int, card_id: int) -> Card:
    """A card whose list is open: a card in an archived list is out of sight
    and changes only when its list is restored."""
    found = _card(conn, board_id, card_id)
    if _list(conn, board_id, found.list_id).archived_at is not None:
        raise Conflict("list: archived; restore it first", code="LIST_ARCHIVED")
    return found


def _check_after(conn: sqlite3.Connection, board_id: int, kind: str, after_id: int | None) -> None:
    """A move goes next to something the screen shows, never an archived row."""
    if after_id is None:
        return
    found = (
        repo.list_of(conn, board_id, after_id)
        if kind == "list"
        else repo.card_of(conn, board_id, after_id)
    )
    if found is not None and found.archived_at is not None:
        raise Invalid(f"after_id: an archived {kind}", field="after_id")


def _room_for_lists(conn: sqlite3.Connection, board_id: int) -> None:
    if repo.count_open_lists(conn, board_id) >= repo.OPEN_LISTS_CAP:
        raise Conflict(
            f"board: holds {repo.OPEN_LISTS_CAP} open lists; archive some first",
            code="TOO_MANY_LISTS",
        )


def _room_for_cards(conn: sqlite3.Connection, board_id: int) -> None:
    if repo.count_open_cards(conn, board_id) >= repo.OPEN_CARDS_CAP:
        raise Conflict(
            f"board: holds {repo.OPEN_CARDS_CAP} open cards; archive some first",
            code="TOO_MANY_CARDS",
        )


def _open_list(conn: sqlite3.Connection, board_id: int, list_id: int, field: str) -> List:
    """A list of this board that takes cards. Named in a body it is a field
    error; named in the path (`field` "path") it is 404."""
    found = repo.list_of(conn, board_id, list_id)
    if found is None and field == "path":
        raise NotFound()
    if found is None:
        raise Invalid(f"{field}: not a list of this board", field=field)
    if found.archived_at is not None:
        raise Conflict("list: archived", code="LIST_ARCHIVED")
    return found


# --- reading -----------------------------------------------------------------------------


def board_lists(at: Where) -> list[ListWithCards]:
    """The open lists in order, each with its open cards in order: two queries."""

    def run(conn: sqlite3.Connection) -> list[ListWithCards]:
        _open(conn, at)
        by_list: dict[int, list[Card]] = {}
        for card in repo.open_cards(conn, at.board_id):
            by_list.setdefault(card.list_id, []).append(card)
        lists = repo.open_lists(conn, at.board_id)
        return [ListWithCards(lst, by_list.get(lst.id, [])) for lst in lists]

    return at.company.tenant.db.read(run)


def get_list(at: Where, list_id: int) -> ListWithCards:
    def run(conn: sqlite3.Connection) -> ListWithCards:
        _open(conn, at)
        return _with_cards(conn, _list(conn, at.board_id, list_id))

    return at.company.tenant.db.read(run)


def get_card(at: Where, card_id: int) -> Card:
    def run(conn: sqlite3.Connection) -> Card:
        _open(conn, at)
        return _card(conn, at.board_id, card_id)

    return at.company.tenant.db.read(run)


# --- lists -------------------------------------------------------------------------------


def create_list(at: Where, name: str) -> ListWithCards:
    """A new list goes after every other list of the board."""

    def run(conn: sqlite3.Connection) -> ListWithCards:
        _edit(conn, at)
        _room_for_lists(conn, at.board_id)
        key = rank.at_end(conn, "list", at.board_id)
        list_id = repo.insert_list(conn, board_id=at.board_id, name=name, rank=key, now=now_iso())
        events.add(conn, "list.created", at.actor_id, board_id=at.board_id, list_id=list_id)
        return _with_cards(conn, _list(conn, at.board_id, list_id))

    return at.company.tenant.db.write(run)


def update_list(
    at: Where, list_id: int, *, name: str | None, archived: bool | None
) -> ListWithCards:
    """Rename, archive or restore. Archiving hides the list with its cards;
    the cards keep their own state and come back with it."""

    def run(conn: sqlite3.Connection) -> ListWithCards:
        _edit(conn, at)
        found = _list(conn, at.board_id, list_id)
        if found.archived_at is not None and name is not None and archived is not False:
            raise Conflict("list: archived; restore it first", code="LIST_ARCHIVED")
        if name is not None and name != found.name:
            repo.rename_list(conn, list_id, name)
            events.add(
                conn,
                "list.updated",
                at.actor_id,
                board_id=at.board_id,
                list_id=list_id,
                fields=["name"],
            )
        if archived is not None and archived != (found.archived_at is not None):
            if not archived:
                _room_for_lists(conn, at.board_id)
            repo.set_list_archived(conn, list_id, now_iso() if archived else None)
            kind = "list.archived" if archived else "list.restored"
            events.add(conn, kind, at.actor_id, board_id=at.board_id, list_id=list_id)
        return _with_cards(conn, _list(conn, at.board_id, list_id))

    return at.company.tenant.db.write(run)


def move_list(at: Where, list_id: int, after_id: int | None) -> ListWithCards:
    """Put the list right after `after_id` on its board (None: first)."""

    def run(conn: sqlite3.Connection) -> ListWithCards:
        _edit(conn, at)
        if _list(conn, at.board_id, list_id).archived_at is not None:
            raise Conflict("list: archived; restore it first", code="LIST_ARCHIVED")
        _check_after(conn, at.board_id, "list", after_id)
        try:
            rank.move(conn, "list", list_id, at.board_id, after_id)
        except LookupError:
            raise Invalid("after_id: not another list of this board", field="after_id") from None
        events.add(
            conn,
            "list.moved",
            at.actor_id,
            board_id=at.board_id,
            list_id=list_id,
            after_id=after_id,
        )
        return _with_cards(conn, _list(conn, at.board_id, list_id))

    return at.company.tenant.db.write(run)


# --- cards -------------------------------------------------------------------------------


def create_card(at: Where, list_id: int, title: str) -> Card:
    """A new card goes at the bottom of its list."""

    def run(conn: sqlite3.Connection) -> Card:
        _edit(conn, at)
        _open_list(conn, at.board_id, list_id, "path")
        _room_for_cards(conn, at.board_id)
        key = rank.at_end(conn, "card", list_id)
        card_id = repo.insert_card(
            conn, list_id=list_id, title=title, rank=key, created_by=at.actor_id, now=now_iso()
        )
        events.add(
            conn,
            "card.created",
            at.actor_id,
            board_id=at.board_id,
            card_id=card_id,
            list_id=list_id,
        )
        return _card(conn, at.board_id, card_id)

    return at.company.tenant.db.write(run)


def update_card(at: Where, card_id: int, *, title: str | None, archived: bool | None) -> Card:
    """Rename, archive or restore. An archived card is renamed only as it is restored."""

    def run(conn: sqlite3.Connection) -> Card:
        _edit(conn, at)
        found = _live_card(conn, at.board_id, card_id)
        if found.archived_at is not None and title is not None and archived is not False:
            raise Conflict("card: archived; restore it first", code="CARD_ARCHIVED")
        now = now_iso()
        if title is not None and title != found.title:
            repo.rename_card(conn, card_id, title, now)
            events.add(
                conn,
                "card.updated",
                at.actor_id,
                board_id=at.board_id,
                card_id=card_id,
                fields=["title"],
            )
        if archived is not None and archived != (found.archived_at is not None):
            if not archived:
                _room_for_cards(conn, at.board_id)
            repo.set_card_archived(conn, card_id, now if archived else None, now)
            kind = "card.archived" if archived else "card.restored"
            events.add(conn, kind, at.actor_id, board_id=at.board_id, card_id=card_id)
        return _card(conn, at.board_id, card_id)

    return at.company.tenant.db.write(run)


def move_card(at: Where, card_id: int, *, list_id: int, after_id: int | None) -> Card:
    """Put the card into `list_id` of the same board, right after `after_id`
    (None: on top). An archived card is restored before it moves, and a
    card in an archived list stays there until the list is restored."""

    def run(conn: sqlite3.Connection) -> Card:
        _edit(conn, at)
        found = _live_card(conn, at.board_id, card_id)
        if found.archived_at is not None:
            raise Conflict("card: archived; restore it first", code="CARD_ARCHIVED")
        _open_list(conn, at.board_id, list_id, "list_id")
        _check_after(conn, at.board_id, "card", after_id)
        try:
            rank.move(conn, "card", card_id, list_id, after_id)
        except LookupError:
            raise Invalid("after_id: not another card of that list", field="after_id") from None
        repo.touch_card(conn, card_id, now_iso())
        events.add(
            conn,
            "card.moved",
            at.actor_id,
            board_id=at.board_id,
            card_id=card_id,
            from_list=found.list_id,
            to_list=list_id,
            after_id=after_id,
        )
        return _card(conn, at.board_id, card_id)

    return at.company.tenant.db.write(run)
