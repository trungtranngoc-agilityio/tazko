"""SQL for projects and project members, in the company's own file. Deleted
projects (in trash) are invisible to every query here."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass

# Fixed caps instead of paging (api-design.md): a company has a few hundred
# projects at most, and a project a few hundred members.
PROJECTS_CAP = 500
MEMBERS_CAP = 500

# What PATCH may change, by API field. Never a column name from the request.
SETTINGS = (
    "name",
    "description",
    "color",
    "default_background",
    "members_can_create_boards",
    "members_can_invite",
    "aging_enabled",
    "aging_days",
)

COLUMNS = (
    "p.id, p.name, p.description, p.color, p.default_background,"
    " p.members_can_create_boards, p.members_can_invite, p.aging_enabled, p.aging_days,"
    " p.created_at, p.archived_at"
)


@dataclass(frozen=True)
class Project:
    id: int
    name: str
    description: str
    color: str | None
    default_background: str | None
    members_can_create_boards: bool
    members_can_invite: bool
    aging_enabled: bool
    aging_days: int
    created_at: str
    archived_at: str | None


@dataclass(frozen=True)
class Summary:
    """A project on the company owners' Manage projects page."""

    project: Project
    owners: list[tuple[int, str]]
    members: int
    boards: int


@dataclass(frozen=True)
class Member:
    user_id: int
    name: str
    email: str
    avatar_url: str | None
    role: str


def _project(row: sqlite3.Row) -> Project:
    return Project(
        id=row["id"],
        name=row["name"],
        description=row["description"],
        color=row["color"],
        default_background=row["default_background"],
        members_can_create_boards=bool(row["members_can_create_boards"]),
        members_can_invite=bool(row["members_can_invite"]),
        aging_enabled=bool(row["aging_enabled"]),
        aging_days=row["aging_days"],
        created_at=row["created_at"],
        archived_at=row["archived_at"],
    )


def insert(
    conn: sqlite3.Connection,
    *,
    name: str,
    description: str,
    color: str | None,
    created_by: int,
    now: str,
) -> int:
    project_id: int = conn.execute(
        "INSERT INTO projects (name, description, color, created_by, created_at)"
        " VALUES (?, ?, ?, ?, ?) RETURNING id",
        (name, description, color, created_by, now),
    ).fetchone()[0]
    return project_id


def get(conn: sqlite3.Connection, project_id: int) -> Project | None:
    row = conn.execute(
        f"SELECT {COLUMNS} FROM projects p WHERE p.id = ? AND p.deleted_at IS NULL",  # noqa: S608 (COLUMNS is a constant; values are bound)
        (project_id,),
    ).fetchone()
    return _project(row) if row else None


def role_of(conn: sqlite3.Connection, project_id: int, person_id: int) -> str | None:
    row = conn.execute(
        "SELECT role FROM project_members WHERE project_id = ? AND person_id = ?",
        (project_id, person_id),
    ).fetchone()
    return row[0] if row else None


def of_person(conn: sqlite3.Connection, person_id: int) -> list[tuple[Project, str]]:
    rows = conn.execute(
        f"SELECT {COLUMNS}, m.role FROM project_members m"  # noqa: S608 (COLUMNS is a constant; values are bound)
        " JOIN projects p ON p.id = m.project_id"
        " WHERE m.person_id = ? AND p.deleted_at IS NULL"
        " ORDER BY p.name COLLATE NOCASE, p.id LIMIT ?",
        (person_id, PROJECTS_CAP),
    ).fetchall()
    return [(_project(row), row["role"]) for row in rows]


def summaries(conn: sqlite3.Connection) -> list[Summary]:
    """Every live project with its counts, then the owners of all of them in one query."""
    rows = conn.execute(
        f"SELECT {COLUMNS},"  # noqa: S608 (COLUMNS is a constant; values are bound)
        " (SELECT count(*) FROM project_members m WHERE m.project_id = p.id) AS members,"
        " (SELECT count(*) FROM boards b WHERE b.project_id = p.id) AS boards"
        " FROM projects p WHERE p.deleted_at IS NULL"
        " ORDER BY p.name COLLATE NOCASE, p.id LIMIT ?",
        (PROJECTS_CAP,),
    ).fetchall()
    owners: dict[int, list[tuple[int, str]]] = {row["id"]: [] for row in rows}
    for project_id, person_id, name in conn.execute(
        "SELECT m.project_id, m.person_id, pe.name FROM project_members m"
        " JOIN people pe ON pe.id = m.person_id"
        " WHERE m.role = 'owner' AND m.project_id IN"
        " (SELECT id FROM projects WHERE deleted_at IS NULL"
        " ORDER BY name COLLATE NOCASE, id LIMIT ?)"
        " ORDER BY pe.name COLLATE NOCASE, pe.id",
        (PROJECTS_CAP,),
    ):
        if project_id in owners:
            owners[project_id].append((person_id, name))
    return [
        Summary(_project(row), owners[row["id"]], row["members"], row["boards"]) for row in rows
    ]


def update(conn: sqlite3.Connection, project_id: int, changes: dict[str, object]) -> None:
    if not set(changes) <= set(SETTINGS):
        raise ValueError(f"not a project setting: {sorted(set(changes) - set(SETTINGS))}")
    names = [name for name in SETTINGS if name in changes]
    assignments = ", ".join(f"{name} = ?" for name in names)
    conn.execute(
        f"UPDATE projects SET {assignments} WHERE id = ?",  # noqa: S608 (names come from SETTINGS only; values are bound)
        (*(changes[name] for name in names), project_id),
    )


def set_archived(conn: sqlite3.Connection, project_id: int, at: str | None) -> None:
    conn.execute("UPDATE projects SET archived_at = ? WHERE id = ?", (at, project_id))


def mark_deleted(conn: sqlite3.Connection, project_id: int, now: str) -> None:
    conn.execute("UPDATE projects SET deleted_at = ? WHERE id = ?", (now, project_id))


def members(conn: sqlite3.Connection, project_id: int) -> list[Member]:
    rows = conn.execute(
        "SELECT pe.id, pe.name, pe.email, pe.avatar_url, m.role FROM project_members m"
        " JOIN people pe ON pe.id = m.person_id WHERE m.project_id = ?"
        " ORDER BY pe.name COLLATE NOCASE, pe.id LIMIT ?",
        (project_id, MEMBERS_CAP),
    ).fetchall()
    return [Member(r["id"], r["name"], r["email"], r["avatar_url"], r["role"]) for r in rows]


def member(conn: sqlite3.Connection, project_id: int, person_id: int) -> Member | None:
    row = conn.execute(
        "SELECT pe.id, pe.name, pe.email, pe.avatar_url, m.role FROM project_members m"
        " JOIN people pe ON pe.id = m.person_id WHERE m.project_id = ? AND m.person_id = ?",
        (project_id, person_id),
    ).fetchone()
    return (
        Member(row["id"], row["name"], row["email"], row["avatar_url"], row["role"])
        if row
        else None
    )


def add_member(
    conn: sqlite3.Connection, *, project_id: int, person_id: int, role: str, now: str
) -> None:
    conn.execute(
        "INSERT INTO project_members (project_id, person_id, role, created_at) VALUES (?, ?, ?, ?)",
        (project_id, person_id, role, now),
    )


def set_role(conn: sqlite3.Connection, *, project_id: int, person_id: int, role: str) -> None:
    conn.execute(
        "UPDATE project_members SET role = ? WHERE project_id = ? AND person_id = ?",
        (role, project_id, person_id),
    )


def owner_count(conn: sqlite3.Connection, project_id: int) -> int:
    count: int = conn.execute(
        "SELECT count(*) FROM project_members WHERE project_id = ? AND role = 'owner'",
        (project_id,),
    ).fetchone()[0]
    return count


def remove_member(conn: sqlite3.Connection, *, project_id: int, person_id: int) -> None:
    """Take the person out, and off the project's restricted boards, board
    stars, card assignees and watchers (D6). Their cards and comments stay."""
    boards = "SELECT id FROM boards WHERE project_id = ?"
    cards = (
        "SELECT c.id FROM cards c JOIN lists l ON l.id = c.list_id"
        " JOIN boards b ON b.id = l.board_id WHERE b.project_id = ?"
    )
    for table in ("board_access", "board_stars"):
        conn.execute(
            f"DELETE FROM {table} WHERE person_id = ? AND board_id IN ({boards})",  # noqa: S608 (fixed table names and subquery; values are bound)
            (person_id, project_id),
        )
    for table in ("card_members", "card_watchers"):
        conn.execute(
            f"DELETE FROM {table} WHERE person_id = ? AND card_id IN ({cards})",  # noqa: S608 (fixed table names and subquery; values are bound)
            (person_id, project_id),
        )
    conn.execute(
        "DELETE FROM project_members WHERE project_id = ? AND person_id = ?",
        (project_id, person_id),
    )


def projects_of_any_state(conn: sqlite3.Connection, person_id: int) -> list[int]:
    """Every project the person is in, archived and in trash included."""
    rows = conn.execute("SELECT project_id FROM project_members WHERE person_id = ?", (person_id,))
    return [row[0] for row in rows]


def add_event(
    conn: sqlite3.Connection,
    *,
    type: str,
    actor_id: int | None,
    payload: str,
    now: str,
    board_id: int | None = None,
) -> None:
    conn.execute(
        "INSERT INTO events (type, actor_id, board_id, payload, created_at) VALUES (?, ?, ?, ?, ?)",
        (type, actor_id, board_id, payload, now),
    )


# --- boards ------------------------------------------------------------------------------

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
