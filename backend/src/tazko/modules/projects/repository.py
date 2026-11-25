"""SQL for projects and project members, in the company's own file. Deleted
projects (in trash) are invisible to every query here."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass

# Fixed caps instead of paging: a company has a few hundred
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
    stars, card assignees and watchers. Their cards and comments stay."""
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


@dataclass(frozen=True)
class CardExtras:
    """What a project card on Your projects shows besides the project."""

    members: int
    people: list[tuple[int, str]]  # the first PEOPLE_ON_CARD members, by name
    boards: int  # open boards this person may see


PEOPLE_ON_CARD = 4


def card_extras(conn: sqlite3.Connection, person_id: int) -> dict[int, CardExtras]:
    """For every project the person is in, in three queries whatever their number."""
    counts = dict(
        conn.execute(
            "SELECT project_id, count(*) FROM project_members WHERE project_id IN"
            " (SELECT project_id FROM project_members WHERE person_id = ?) GROUP BY project_id",
            (person_id,),
        ).fetchall()
    )
    people: dict[int, list[tuple[int, str]]] = {}
    for project_id, user_id, name in conn.execute(
        "SELECT project_id, person_id, name FROM ("
        " SELECT m.project_id, m.person_id, pe.name, row_number() OVER ("
        "  PARTITION BY m.project_id ORDER BY pe.name COLLATE NOCASE, pe.id) AS n"
        " FROM project_members m JOIN people pe ON pe.id = m.person_id"
        " WHERE m.project_id IN (SELECT project_id FROM project_members WHERE person_id = ?))"
        " WHERE n <= ? ORDER BY project_id, n",
        (person_id, PEOPLE_ON_CARD),
    ):
        people.setdefault(project_id, []).append((user_id, name))
    boards = dict(
        conn.execute(
            "SELECT b.project_id, count(*) FROM boards b"
            " JOIN project_members me ON me.project_id = b.project_id AND me.person_id = ?"
            " WHERE b.archived_at IS NULL AND (b.restricted = 0 OR me.role = 'owner' OR EXISTS"
            "  (SELECT 1 FROM board_access a WHERE a.board_id = b.id AND a.person_id = ?))"
            " GROUP BY b.project_id",
            (person_id, person_id),
        ).fetchall()
    )
    return {
        project_id: CardExtras(count, people.get(project_id, []), boards.get(project_id, 0))
        for project_id, count in counts.items()
    }
