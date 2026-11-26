"""SQL for lists and cards, in the company's own file. Ranks are written by
tazko.db.rank; every lookup here is scoped to one board."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass

# Fixed caps instead of paging: the board is read whole, so these bound that read.
OPEN_LISTS_CAP = 200
OPEN_CARDS_CAP = 5000
CARD_COLUMNS = (
    "c.id, c.list_id, c.title, c.rank, c.due_at, c.done_at, c.cover_color,"
    " c.created_at, c.updated_at, c.archived_at"
)


@dataclass(frozen=True)
class List:
    id: int
    board_id: int
    name: str
    rank: str
    created_at: str
    archived_at: str | None


@dataclass(frozen=True)
class Card:
    id: int
    list_id: int
    title: str
    rank: str
    due_at: str | None
    done_at: str | None
    cover_color: str | None
    created_at: str
    updated_at: str
    archived_at: str | None


def _list(row: sqlite3.Row) -> List:
    return List(
        id=row["id"],
        board_id=row["board_id"],
        name=row["name"],
        rank=row["rank"],
        created_at=row["created_at"],
        archived_at=row["archived_at"],
    )


def _card(row: sqlite3.Row) -> Card:
    return Card(
        id=row["id"],
        list_id=row["list_id"],
        title=row["title"],
        rank=row["rank"],
        due_at=row["due_at"],
        done_at=row["done_at"],
        cover_color=row["cover_color"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
        archived_at=row["archived_at"],
    )


def list_of(conn: sqlite3.Connection, board_id: int, list_id: int) -> List | None:
    """The list, only if it is on this board."""
    row = conn.execute(
        "SELECT id, board_id, name, rank, created_at, archived_at FROM lists"
        " WHERE id = ? AND board_id = ?",
        (list_id, board_id),
    ).fetchone()
    return _list(row) if row else None


def card_of(conn: sqlite3.Connection, board_id: int, card_id: int) -> Card | None:
    """The card, only if it is on this board."""
    row = conn.execute(
        f"SELECT {CARD_COLUMNS} FROM cards c JOIN lists l ON l.id = c.list_id"  # noqa: S608 (CARD_COLUMNS is a constant; values are bound)
        " WHERE c.id = ? AND l.board_id = ?",
        (card_id, board_id),
    ).fetchone()
    return _card(row) if row else None


def open_lists(conn: sqlite3.Connection, board_id: int) -> list[List]:
    rows = conn.execute(
        "SELECT id, board_id, name, rank, created_at, archived_at FROM lists"
        " WHERE board_id = ? AND archived_at IS NULL ORDER BY rank LIMIT ?",
        (board_id, OPEN_LISTS_CAP),
    )
    return [_list(row) for row in rows]


def open_cards(conn: sqlite3.Connection, board_id: int) -> list[Card]:
    """The open cards of the board's open lists, by list and rank."""
    rows = conn.execute(
        f"SELECT {CARD_COLUMNS} FROM cards c JOIN lists l ON l.id = c.list_id"  # noqa: S608 (CARD_COLUMNS is a constant; values are bound)
        " WHERE l.board_id = ? AND l.archived_at IS NULL AND c.archived_at IS NULL"
        " ORDER BY c.list_id, c.rank LIMIT ?",
        (board_id, OPEN_CARDS_CAP),
    )
    return [_card(row) for row in rows]


def cards_of_list(conn: sqlite3.Connection, list_id: int) -> list[Card]:
    """The open cards of one list, whatever the list's own state, by rank."""
    rows = conn.execute(
        f"SELECT {CARD_COLUMNS} FROM cards c"  # noqa: S608 (CARD_COLUMNS is a constant; values are bound)
        " WHERE c.list_id = ? AND c.archived_at IS NULL ORDER BY c.rank LIMIT ?",
        (list_id, OPEN_CARDS_CAP),
    )
    return [_card(row) for row in rows]


def count_open_lists(conn: sqlite3.Connection, board_id: int) -> int:
    row = conn.execute(
        "SELECT count(*) FROM lists WHERE board_id = ? AND archived_at IS NULL", (board_id,)
    ).fetchone()
    return int(row[0])


def count_open_cards(conn: sqlite3.Connection, board_id: int) -> int:
    """Open cards on any list of the board, so restoring a list never goes past the cap."""
    row = conn.execute(
        "SELECT count(*) FROM cards c JOIN lists l ON l.id = c.list_id"
        " WHERE l.board_id = ? AND c.archived_at IS NULL",
        (board_id,),
    ).fetchone()
    return int(row[0])


def insert_list(conn: sqlite3.Connection, *, board_id: int, name: str, rank: str, now: str) -> int:
    list_id: int = conn.execute(
        "INSERT INTO lists (board_id, name, rank, created_at) VALUES (?, ?, ?, ?) RETURNING id",
        (board_id, name, rank, now),
    ).fetchone()[0]
    return list_id


def insert_card(
    conn: sqlite3.Connection, *, list_id: int, title: str, rank: str, created_by: int, now: str
) -> int:
    card_id: int = conn.execute(
        "INSERT INTO cards (list_id, title, rank, created_by, created_at, updated_at)"
        " VALUES (?, ?, ?, ?, ?, ?) RETURNING id",
        (list_id, title, rank, created_by, now, now),
    ).fetchone()[0]
    return card_id


def rename_list(conn: sqlite3.Connection, list_id: int, name: str) -> None:
    conn.execute("UPDATE lists SET name = ? WHERE id = ?", (name, list_id))


def set_list_archived(conn: sqlite3.Connection, list_id: int, at: str | None) -> None:
    conn.execute("UPDATE lists SET archived_at = ? WHERE id = ?", (at, list_id))


def rename_card(conn: sqlite3.Connection, card_id: int, title: str, now: str) -> None:
    conn.execute("UPDATE cards SET title = ?, updated_at = ? WHERE id = ?", (title, now, card_id))


def set_card_archived(conn: sqlite3.Connection, card_id: int, at: str | None, now: str) -> None:
    conn.execute(
        "UPDATE cards SET archived_at = ?, updated_at = ? WHERE id = ?", (at, now, card_id)
    )


def touch_card(conn: sqlite3.Connection, card_id: int, now: str) -> None:
    """Card aging counts a move as activity."""
    conn.execute("UPDATE cards SET updated_at = ? WHERE id = ?", (now, card_id))
