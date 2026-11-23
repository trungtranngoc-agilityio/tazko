"""The company file's board tables (migration 0002): constraints, cascades, rollback."""

from __future__ import annotations

import shutil
import sqlite3
from collections.abc import Callable
from importlib.resources import as_file, files
from pathlib import Path

import pytest

from tazko.db import Database
from tests.unit.tenant_rows import AT, add_board, add_card, add_label, add_list, add_person

BOARD_TABLES = {
    "projects",
    "project_members",
    "boards",
    "board_access",
    "board_stars",
    "lists",
    "cards",
    "labels",
    "card_labels",
    "card_members",
    "card_watchers",
}


def test_a_company_file_has_the_board_tables(company: Database) -> None:
    names = company.read(
        lambda c: {r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type = 'table'")}
    )
    assert names >= BOARD_TABLES


@pytest.mark.parametrize("bad", ["", "a0", "a-b", "é", "x" * 33])
def test_a_malformed_rank_is_refused(company: Database, bad: str) -> None:
    def insert(conn: sqlite3.Connection) -> None:
        add_person(conn)
        board = add_board(conn)
        conn.execute(
            "INSERT INTO lists (board_id, name, rank, created_at) VALUES (?, 'L', ?, ?)",
            (board, bad, AT),
        )

    with pytest.raises(sqlite3.IntegrityError, match="CHECK"):
        company.write(insert)


def test_an_unknown_project_role_is_refused(company: Database) -> None:
    def insert(conn: sqlite3.Connection) -> None:
        add_person(conn)
        add_person(conn, 2)
        board = add_board(conn)
        project = conn.execute("SELECT project_id FROM boards WHERE id = ?", (board,)).fetchone()
        conn.execute(
            "INSERT INTO project_members (project_id, person_id, role, created_at)"
            " VALUES (?, 2, 'admin', ?)",
            (project[0], AT),
        )

    with pytest.raises(sqlite3.IntegrityError, match="CHECK"):
        company.write(insert)


def test_a_card_member_must_be_a_person_of_the_company(company: Database) -> None:
    def insert(conn: sqlite3.Connection) -> None:
        add_person(conn)
        card = add_card(conn, add_list(conn, add_board(conn)))
        conn.execute("INSERT INTO card_members (card_id, person_id) VALUES (?, 99)", (card,))

    with pytest.raises(sqlite3.IntegrityError, match="FOREIGN KEY"):
        company.write(insert)


def test_a_label_belongs_to_the_board_of_its_card(company: Database) -> None:
    def insert(conn: sqlite3.Connection) -> None:
        add_person(conn)
        card = add_card(conn, add_list(conn, add_board(conn)))
        label = add_label(conn, add_board(conn))
        conn.execute("INSERT INTO card_labels (card_id, label_id) VALUES (?, ?)", (card, label))

    with pytest.raises(sqlite3.IntegrityError, match="another board"):
        company.write(insert)


def test_deleting_a_project_removes_everything_on_its_boards(company: Database) -> None:
    def seed(conn: sqlite3.Connection) -> None:
        add_person(conn)
        board = add_board(conn)
        card = add_card(conn, add_list(conn, board))
        conn.execute("INSERT INTO card_labels VALUES (?, ?)", (card, add_label(conn, board)))
        conn.execute("INSERT INTO card_members VALUES (?, 1)", (card,))
        conn.execute("INSERT INTO card_watchers VALUES (?, 1)", (card,))
        conn.execute("INSERT INTO board_stars VALUES (1, ?, ?)", (board, AT))
        conn.execute("UPDATE boards SET restricted = 1 WHERE id = ?", (board,))
        conn.execute("INSERT INTO board_access VALUES (?, 1)", (board,))

    company.write(seed)
    company.write(lambda c: c.execute("DELETE FROM projects"))

    def counts(conn: sqlite3.Connection) -> dict[str, int]:
        return {
            t: conn.execute(f"SELECT count(*) FROM {t}").fetchone()[0]  # noqa: S608 (fixed names)
            for t in BOARD_TABLES
        }

    assert company.read(counts) == dict.fromkeys(BOARD_TABLES, 0)
    assert company.read(lambda c: c.execute("SELECT count(*) FROM people").fetchone()[0]) == 1


def test_the_release_before_the_board_tables_still_opens_the_file(tmp_path: Path) -> None:
    """D21: 0002 only adds tables, so a rollback to the release that knew only
    0001 keeps running on a file that a newer release migrated."""
    path = tmp_path / "tazko.db"
    Database(path, "tenant").close()
    older = tmp_path / "older"
    older.mkdir()
    with as_file(files("tazko") / "migrations" / "tenant" / "0001_init.sql") as first:
        shutil.copy(first, older / "0001_init.sql")

    db = Database(path, "tenant", migrations=older)
    try:
        assert db.version >= 2

        # What that release writes to a company file: the copy of a person (orgs.repository).
        def upsert(name: str) -> Callable[[sqlite3.Connection], object]:
            return lambda c: c.execute(
                "INSERT INTO people (id, name, email, updated_at) VALUES (7, ?, 'a@x.io', ?)"
                " ON CONFLICT (id) DO UPDATE SET name = excluded.name",
                (name, AT),
            )

        db.write(upsert("Ann"))
        db.write(upsert("Ann B."))
        assert db.read(lambda c: c.execute("SELECT name FROM people").fetchone()[0]) == "Ann B."
    finally:
        db.close()


def board_card_and_label(conn: sqlite3.Connection) -> tuple[int, int, int]:
    """(board, card, label): a card on the board wearing one of its labels."""
    add_person(conn)
    board = add_board(conn)
    card = add_card(conn, add_list(conn, board))
    label = add_label(conn, board)
    conn.execute("INSERT INTO card_labels VALUES (?, ?)", (card, label))
    return board, card, label


def test_a_card_label_cannot_be_changed_to_a_label_of_another_board(company: Database) -> None:
    def change(conn: sqlite3.Connection) -> None:
        _, card, _ = board_card_and_label(conn)
        other = add_label(conn, add_board(conn), "Other")
        conn.execute("UPDATE card_labels SET label_id = ? WHERE card_id = ?", (other, card))

    with pytest.raises(sqlite3.IntegrityError, match="another board"):
        company.write(change)


def test_moving_a_card_to_another_board_drops_its_labels(company: Database) -> None:
    def move_away(conn: sqlite3.Connection) -> None:
        _, card, _ = board_card_and_label(conn)
        elsewhere = add_list(conn, add_board(conn))
        conn.execute("UPDATE cards SET list_id = ? WHERE id = ?", (elsewhere, card))

    company.write(move_away)
    assert company.read(lambda c: c.execute("SELECT count(*) FROM card_labels").fetchone()[0]) == 0
    assert company.read(lambda c: c.execute("SELECT count(*) FROM cards").fetchone()[0]) == 1


def test_moving_a_card_within_its_board_keeps_its_labels(company: Database) -> None:
    def move_along(conn: sqlite3.Connection) -> None:
        board, card, _ = board_card_and_label(conn)
        conn.execute("UPDATE cards SET list_id = ? WHERE id = ?", (add_list(conn, board), card))

    company.write(move_along)
    assert company.read(lambda c: c.execute("SELECT count(*) FROM card_labels").fetchone()[0]) == 1


def test_moving_a_list_to_another_board_drops_the_labels_of_its_cards(company: Database) -> None:
    def move_away(conn: sqlite3.Connection) -> None:
        _, card, _ = board_card_and_label(conn)
        other = add_board(conn)
        conn.execute(
            "UPDATE lists SET board_id = ? WHERE id = (SELECT list_id FROM cards WHERE id = ?)",
            (other, card),
        )

    company.write(move_away)
    assert company.read(lambda c: c.execute("SELECT count(*) FROM card_labels").fetchone()[0]) == 0


@pytest.mark.parametrize(
    "sql",
    [
        "UPDATE projects SET name = '   '",
        "UPDATE boards SET name = ' '",
        "UPDATE lists SET name = '  '",
        "UPDATE cards SET title = ' '",
    ],
)
def test_a_blank_name_is_refused(company: Database, sql: str) -> None:
    def blank(conn: sqlite3.Connection) -> None:
        add_person(conn)
        add_card(conn, add_list(conn, add_board(conn)))
        conn.execute(sql)

    with pytest.raises(sqlite3.IntegrityError, match="CHECK"):
        company.write(blank)


NEW_ROW: dict[str, Callable[[sqlite3.Connection, int], int]] = {
    "projects": lambda conn, board: conn.execute(
        "INSERT INTO projects (name, created_at) VALUES ('P', ?) RETURNING id", (AT,)
    ).fetchone()[0],
    "boards": lambda conn, board: add_board(conn),
    "lists": lambda conn, board: add_list(conn, board),
    "cards": lambda conn, board: add_card(conn, add_list(conn, board)),
    "labels": lambda conn, board: add_label(conn, board),
}


@pytest.mark.parametrize("table", sorted(NEW_ROW))
def test_the_id_of_a_deleted_row_is_never_given_again(company: Database, table: str) -> None:
    """Events and share links name rows by id; a new row must not inherit them."""

    def replace(conn: sqlite3.Connection) -> tuple[int, int]:
        add_person(conn)
        board = add_board(conn)
        old = NEW_ROW[table](conn, board)
        conn.execute(f"DELETE FROM {table} WHERE id = ?", (old,))  # noqa: S608 (fixed names)
        return old, NEW_ROW[table](conn, board)

    old, new = company.write(replace)
    assert new > old


def test_a_label_cannot_move_to_another_board(company: Database) -> None:
    def move_label(conn: sqlite3.Connection) -> None:
        _, _, label = board_card_and_label(conn)
        conn.execute("UPDATE labels SET board_id = ? WHERE id = ?", (add_board(conn), label))

    with pytest.raises(sqlite3.IntegrityError, match="stays on its board"):
        company.write(move_label)


def test_a_card_label_that_does_not_exist_is_a_foreign_key_error(company: Database) -> None:
    def insert(conn: sqlite3.Connection) -> None:
        add_person(conn)
        card = add_card(conn, add_list(conn, add_board(conn)))
        conn.execute("INSERT INTO card_labels VALUES (?, 999)", (card,))

    with pytest.raises(sqlite3.IntegrityError, match="FOREIGN KEY"):
        company.write(insert)
