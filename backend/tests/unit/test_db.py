"""Database: migrations by user_version, one writer thread, a read pool."""

from __future__ import annotations

import sqlite3
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest

from tazko.db import Database, MigrationError


def scripts(folder: Path, **files: str) -> Path:
    folder.mkdir(parents=True, exist_ok=True)
    for name, sql in files.items():
        (folder / f"{name}.sql").write_text(sql)
    return folder


def version(path: Path) -> int:
    conn = sqlite3.connect(path)
    try:
        value: int = conn.execute("PRAGMA user_version").fetchone()[0]
    finally:
        conn.close()
    return value


def tables(path: Path) -> set[str]:
    conn = sqlite3.connect(path)
    try:
        rows = conn.execute("SELECT name FROM sqlite_master WHERE type = 'table'").fetchall()
    finally:
        conn.close()
    return {row[0] for row in rows}


def count_a(conn: sqlite3.Connection) -> int:
    value: int = conn.execute("SELECT count(*) FROM a").fetchone()[0]
    return value


@pytest.mark.parametrize("schema", ["control", "tenant"])
def test_new_database_is_migrated_to_latest(tmp_path: Path, schema: str) -> None:
    db = Database(tmp_path / "x.db", schema)
    try:
        assert db.version >= 1
        assert version(tmp_path / "x.db") == db.version
        assert db.read(lambda c: c.execute("PRAGMA journal_mode").fetchone()[0]) == "wal"
        assert db.read(lambda c: c.execute("PRAGMA foreign_keys").fetchone()[0]) == 1
    finally:
        db.close()


def test_migrations_run_once_in_order(tmp_path: Path) -> None:
    folder = scripts(
        tmp_path / "m",
        **{"0001_a": "CREATE TABLE a (x INTEGER);", "0002_b": "INSERT INTO a VALUES (2);"},
    )
    Database(tmp_path / "x.db", "test", migrations=folder).close()
    db = Database(tmp_path / "x.db", "test", migrations=folder)
    try:
        assert db.version == 2
        assert db.read(count_a) == 1
    finally:
        db.close()


def test_failed_migration_rolls_back(tmp_path: Path) -> None:
    folder = scripts(
        tmp_path / "m",
        **{
            "0001_a": "CREATE TABLE a (x INTEGER);",
            "0002_bad": "CREATE TABLE b (x INTEGER); INSERT INTO missing VALUES (1);",
        },
    )
    with pytest.raises(MigrationError, match="0002_bad"):
        Database(tmp_path / "x.db", "test", migrations=folder)
    assert version(tmp_path / "x.db") == 1
    assert "b" not in tables(tmp_path / "x.db")


def test_database_newer_than_the_code_is_refused(tmp_path: Path) -> None:
    conn = sqlite3.connect(tmp_path / "x.db")
    conn.execute("PRAGMA user_version = 99")
    conn.close()
    folder = scripts(tmp_path / "m", **{"0001_a": "CREATE TABLE a (x INTEGER);"})
    with pytest.raises(MigrationError, match="newer"):
        Database(tmp_path / "x.db", "test", migrations=folder)


def test_writes_run_on_one_thread(tmp_path: Path) -> None:
    db = Database(tmp_path / "x.db", "tenant")
    try:
        with ThreadPoolExecutor(4) as pool:
            idents = set(pool.map(lambda _: db.write(lambda c: threading.get_ident()), range(20)))
        assert len(idents) == 1
        assert threading.get_ident() not in idents
    finally:
        db.close()


def test_failed_write_rolls_back(tmp_path: Path) -> None:
    folder = scripts(tmp_path / "m", **{"0001_a": "CREATE TABLE a (x INTEGER);"})
    db = Database(tmp_path / "x.db", "test", migrations=folder)

    def insert_then_fail(conn: sqlite3.Connection) -> None:
        conn.execute("INSERT INTO a VALUES (1)")
        raise ValueError("boom")

    try:
        with pytest.raises(ValueError, match="boom"):
            db.write(insert_then_fail)
        assert db.read(count_a) == 0
    finally:
        db.close()


def test_reads_see_committed_writes(tmp_path: Path) -> None:
    folder = scripts(tmp_path / "m", **{"0001_a": "CREATE TABLE a (x INTEGER);"})
    db = Database(tmp_path / "x.db", "test", migrations=folder)
    try:
        db.write(lambda c: c.execute("INSERT INTO a VALUES (7)"))
        assert db.read(lambda c: c.execute("SELECT x FROM a").fetchone()[0]) == 7
    finally:
        db.close()


def test_reads_cannot_write(tmp_path: Path) -> None:
    folder = scripts(tmp_path / "m", **{"0001_a": "CREATE TABLE a (x INTEGER);"})
    db = Database(tmp_path / "x.db", "test", migrations=folder)
    try:
        with pytest.raises(sqlite3.OperationalError):
            db.read(lambda c: c.execute("INSERT INTO a VALUES (1)"))
    finally:
        db.close()


def test_closed_database_refuses_work(tmp_path: Path) -> None:
    db = Database(tmp_path / "x.db", "tenant")
    db.close()
    with pytest.raises(RuntimeError, match="closed"):
        db.write(lambda c: None)
