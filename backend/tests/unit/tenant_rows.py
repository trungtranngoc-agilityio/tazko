"""Rows for tests on a company file: a person, a project, a board, lists and cards.

Plain SQL on purpose: the services that create these rows arrive with the
screens (M2-02, M2-03); these tests prove the schema and the ranks under them.
"""

from __future__ import annotations

import sqlite3

from tazko.db import rank

AT = "2026-11-23T09:00:00.000Z"


def add_person(conn: sqlite3.Connection, person_id: int = 1) -> int:
    conn.execute(
        "INSERT INTO people (id, name, email, updated_at) VALUES (?, ?, ?, ?)",
        (person_id, f"Person {person_id}", f"p{person_id}@example.com", AT),
    )
    return person_id


def add_board(conn: sqlite3.Connection, *, owner: int = 1) -> int:
    """A project with `owner` as its owner and one board in it."""
    project_id: int = conn.execute(
        "INSERT INTO projects (name, created_by, created_at) VALUES ('Launch', ?, ?) RETURNING id",
        (owner, AT),
    ).fetchone()[0]
    conn.execute(
        "INSERT INTO project_members (project_id, person_id, role, created_at)"
        " VALUES (?, ?, 'owner', ?)",
        (project_id, owner, AT),
    )
    board_id: int = conn.execute(
        "INSERT INTO boards (project_id, name, created_by, created_at)"
        " VALUES (?, 'Sprint', ?, ?) RETURNING id",
        (project_id, owner, AT),
    ).fetchone()[0]
    return board_id


def add_list(conn: sqlite3.Connection, board_id: int, name: str = "To do") -> int:
    list_id: int = conn.execute(
        "INSERT INTO lists (board_id, name, rank, created_at) VALUES (?, ?, ?, ?) RETURNING id",
        (board_id, name, rank.at_end(conn, "list", board_id), AT),
    ).fetchone()[0]
    return list_id


def add_card(conn: sqlite3.Connection, list_id: int, title: str = "Card") -> int:
    card_id: int = conn.execute(
        "INSERT INTO cards (list_id, title, rank, created_at, updated_at)"
        " VALUES (?, ?, ?, ?, ?) RETURNING id",
        (list_id, title, rank.at_end(conn, "card", list_id), AT, AT),
    ).fetchone()[0]
    return card_id


def card_order(conn: sqlite3.Connection, list_id: int) -> list[int]:
    rows = conn.execute(
        "SELECT id FROM cards WHERE list_id = ? ORDER BY rank, id", (list_id,)
    ).fetchall()
    return [row[0] for row in rows]


def ranks(conn: sqlite3.Connection, table: str, scope: str, scope_id: int) -> list[str]:
    assert (table, scope) in {("cards", "list_id"), ("lists", "board_id")}
    query = f"SELECT rank FROM {table} WHERE {scope} = ?"  # noqa: S608 (names checked above)
    rows = conn.execute(query, (scope_id,)).fetchall()
    return [row[0] for row in rows]
