"""SQL for boards: restricted access lists and stars, in the company's own file."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass

BOARDS_CAP = 500  # a project has tens of boards; a fixed cap instead of paging
BOARD_SETTINGS = ("name", "background")
BOARD_COLUMNS = (
    "b.id, b.project_id, b.name, b.background, b.restricted, b.created_at, b.archived_at"
)


@dataclass(frozen=True)
class Board:
    id: int
    project_id: int
    name: str
    background: str | None
    restricted: bool
    created_at: str
    archived_at: str | None


def _board(row: sqlite3.Row) -> Board:
    return Board(
        id=row["id"],
        project_id=row["project_id"],
        name=row["name"],
        background=row["background"],
        restricted=bool(row["restricted"]),
        created_at=row["created_at"],
        archived_at=row["archived_at"],
    )


def insert_board(
    conn: sqlite3.Connection,
    *,
    project_id: int,
    name: str,
    background: str | None,
    created_by: int,
    now: str,
) -> int:
    board_id: int = conn.execute(
        "INSERT INTO boards (project_id, name, background, created_by, created_at)"
        " VALUES (?, ?, ?, ?, ?) RETURNING id",
        (project_id, name, background, created_by, now),
    ).fetchone()[0]
    return board_id


def board(conn: sqlite3.Connection, project_id: int, board_id: int) -> Board | None:
    """The board, only if it belongs to this project."""
    row = conn.execute(
        f"SELECT {BOARD_COLUMNS} FROM boards b WHERE b.id = ? AND b.project_id = ?",  # noqa: S608 (BOARD_COLUMNS is a constant; values are bound)
        (board_id, project_id),
    ).fetchone()
    return _board(row) if row else None


def boards_seen(
    conn: sqlite3.Connection, project_id: int, person_id: int, *, every_restricted: bool
) -> list[tuple[Board, bool]]:
    """The project's boards this person may see, with whether they starred each.
    Restricted boards only when `every_restricted` (project owners) or listed."""
    rows = conn.execute(
        f"SELECT {BOARD_COLUMNS},"  # noqa: S608 (BOARD_COLUMNS is a constant; values are bound)
        " EXISTS (SELECT 1 FROM board_stars s WHERE s.board_id = b.id AND s.person_id = ?)"
        " AS starred"
        " FROM boards b WHERE b.project_id = ?"
        " AND (b.restricted = 0 OR ? OR EXISTS"
        "  (SELECT 1 FROM board_access a WHERE a.board_id = b.id AND a.person_id = ?))"
        " ORDER BY b.name COLLATE NOCASE, b.id LIMIT ?",
        (person_id, project_id, every_restricted, person_id, BOARDS_CAP),
    ).fetchall()
    return [(_board(row), bool(row["starred"])) for row in rows]


def listed(conn: sqlite3.Connection, board_id: int, person_id: int) -> bool:
    row = conn.execute(
        "SELECT 1 FROM board_access WHERE board_id = ? AND person_id = ?", (board_id, person_id)
    ).fetchone()
    return row is not None


def starred(conn: sqlite3.Connection, board_id: int, person_id: int) -> bool:
    row = conn.execute(
        "SELECT 1 FROM board_stars WHERE board_id = ? AND person_id = ?", (board_id, person_id)
    ).fetchone()
    return row is not None


def access_lists(conn: sqlite3.Connection, project_id: int) -> dict[int, list[int]]:
    """The list of every restricted board of the project, in one query."""
    lists: dict[int, list[int]] = {}
    for board_id, person_id in conn.execute(
        "SELECT a.board_id, a.person_id FROM board_access a JOIN boards b ON b.id = a.board_id"
        " WHERE b.project_id = ? AND b.restricted = 1 ORDER BY a.board_id, a.person_id",
        (project_id,),
    ):
        lists.setdefault(board_id, []).append(person_id)
    return lists


def access_list(conn: sqlite3.Connection, board_id: int) -> list[int]:
    rows = conn.execute(
        "SELECT person_id FROM board_access WHERE board_id = ? ORDER BY person_id", (board_id,)
    )
    return [row[0] for row in rows]


def update_board(conn: sqlite3.Connection, board_id: int, changes: dict[str, object]) -> None:
    if not set(changes) <= set(BOARD_SETTINGS):
        raise ValueError(f"not a board setting: {sorted(set(changes) - set(BOARD_SETTINGS))}")
    names = [name for name in BOARD_SETTINGS if name in changes]
    assignments = ", ".join(f"{name} = ?" for name in names)
    conn.execute(
        f"UPDATE boards SET {assignments} WHERE id = ?",  # noqa: S608 (names come from BOARD_SETTINGS only; values are bound)
        (*(changes[name] for name in names), board_id),
    )


def set_board_archived(conn: sqlite3.Connection, board_id: int, at: str | None) -> None:
    conn.execute("UPDATE boards SET archived_at = ? WHERE id = ?", (at, board_id))


def set_access(
    conn: sqlite3.Connection, board_id: int, *, restricted: bool, people: list[int]
) -> None:
    """Restricted with exactly `people` listed, or open to the project with no list."""
    conn.execute("UPDATE boards SET restricted = ? WHERE id = ?", (int(restricted), board_id))
    conn.execute("DELETE FROM board_access WHERE board_id = ?", (board_id,))
    if restricted:
        conn.executemany(
            "INSERT INTO board_access (board_id, person_id) VALUES (?, ?)",
            [(board_id, person_id) for person_id in sorted(set(people))],
        )
        # A star never outlives the view: only project owners and the list keep theirs.
        conn.execute(
            "DELETE FROM board_stars WHERE board_id = ? AND person_id NOT IN"
            " (SELECT person_id FROM board_access WHERE board_id = ?"
            "  UNION SELECT person_id FROM project_members"
            "  WHERE project_id = (SELECT project_id FROM boards WHERE id = ?) AND role = 'owner')",
            (board_id, board_id, board_id),
        )


def set_star(
    conn: sqlite3.Connection, board_id: int, person_id: int, *, on: bool, now: str
) -> bool:
    """True when this changed anything."""
    if on:
        cursor = conn.execute(
            "INSERT OR IGNORE INTO board_stars (person_id, board_id, created_at) VALUES (?, ?, ?)",
            (person_id, board_id, now),
        )
    else:
        cursor = conn.execute(
            "DELETE FROM board_stars WHERE person_id = ? AND board_id = ?", (person_id, board_id)
        )
    return cursor.rowcount == 1
