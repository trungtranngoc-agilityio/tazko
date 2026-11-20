"""tazko backup, check and purge-trash (M1-08) on a real data folder."""

from __future__ import annotations

import os
import shutil
import sqlite3
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from tazko.cli import main
from tazko.db import Database, snapshot
from tazko.db.tenant import Tenants

NOW = datetime(2026, 11, 20, 2, 30, tzinfo=UTC)


@pytest.fixture
def data(tmp_path: Path) -> Iterator[Path]:
    """A data folder as the server leaves it: control.db listing two live
    companies and a deleted one, their files, the secret, and a trash folder."""
    folder = tmp_path / "data"
    control = Database(folder / "control.db", "control", readers=1)
    tenants = Tenants(folder)
    try:
        companies = (("acme", "active"), ("zeta", "suspended"), ("gone", "deleted"))
        control.write(
            lambda c: c.executemany(
                "INSERT INTO orgs (slug, name, status, created_at) VALUES (?, ?, ?, '2026')",
                [(slug, slug.title(), status) for slug, status in companies],
            )
        )
        for slug, status in companies:
            if status != "deleted":
                tenants.create(slug)
        (folder / "orgs" / "acme" / "files" / "ab").mkdir()
        (folder / "orgs" / "acme" / "files" / "ab" / "abcd").write_bytes(b"attachment")
        (folder / "secret").write_bytes(b"s" * 32)
        (folder / "trash" / "old-20260101T000000Z").mkdir(parents=True)
        yield folder
    finally:
        tenants.close()
        control.close()


def rows(db: Path, sql: str) -> list[tuple[object, ...]]:
    conn = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    try:
        return list(conn.execute(sql).fetchall())
    finally:
        conn.close()


# --- backup -------------------------------------------------------------------------


def test_backup_copies_every_database_the_files_and_the_secret(data: Path, tmp_path: Path) -> None:
    made = snapshot.backup(data, tmp_path / "backups", keep_days=30, now=NOW)

    assert made == tmp_path / "backups" / "20261120T023000Z"
    assert rows(made / "control.db", "SELECT slug FROM orgs ORDER BY slug") == [
        ("acme",),
        ("gone",),
        ("zeta",),
    ]
    assert (made / "orgs" / "acme" / "tazko.db").is_file()
    assert (made / "orgs" / "zeta" / "tazko.db").is_file()
    assert (made / "orgs" / "acme" / "files" / "ab" / "abcd").read_bytes() == b"attachment"
    assert (made / "secret").read_bytes() == b"s" * 32
    assert not (made / "trash").exists()  # deleted companies are not backed up again


def test_backup_sees_writes_committed_while_the_server_runs(data: Path, tmp_path: Path) -> None:
    # given the server holds control.db open in WAL mode with a fresh commit in the -wal file
    control = Database(data / "control.db", "control", readers=1)
    try:
        control.write(
            lambda c: c.execute(
                "INSERT INTO orgs (slug, name, created_at) VALUES ('late', 'Late', '2026')"
            )
        )
        made = snapshot.backup(data, tmp_path / "backups", keep_days=30, now=NOW)
    finally:
        control.close()

    assert ("late",) in rows(made / "control.db", "SELECT slug FROM orgs")


def test_backup_keeps_snapshots_and_files_private(data: Path, tmp_path: Path) -> None:
    if os.name != "posix":
        pytest.skip("POSIX file modes")
    made = snapshot.backup(data, tmp_path / "backups", keep_days=30, now=NOW)

    assert (made.stat().st_mode & 0o777) == 0o700
    assert ((made / "secret").stat().st_mode & 0o777) == 0o600
    assert ((made / "control.db").stat().st_mode & 0o777) == 0o600


def test_backup_removes_snapshots_older_than_keep_days(data: Path, tmp_path: Path) -> None:
    backups = tmp_path / "backups"
    for stamp in ("20261019T023000Z", "20261021T023000Z"):
        (backups / stamp).mkdir(parents=True)
    (backups / "notes").mkdir()  # not a snapshot: never touched

    snapshot.backup(data, backups, keep_days=30, now=NOW)

    assert sorted(p.name for p in backups.iterdir()) == [
        "20261021T023000Z",
        "20261120T023000Z",
        "notes",
    ]


def test_backup_never_removes_the_snapshot_it_just_made(data: Path, tmp_path: Path) -> None:
    made = snapshot.backup(data, tmp_path / "backups", keep_days=0, now=NOW)

    assert made.is_dir()


def test_a_failed_backup_leaves_no_snapshot(
    data: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def broken(*_args: object, **_kwargs: object) -> None:
        raise OSError("disk full")

    monkeypatch.setattr(shutil, "copytree", broken)

    with pytest.raises(OSError):
        snapshot.backup(data, tmp_path / "backups", keep_days=30, now=NOW)

    assert list((tmp_path / "backups").iterdir()) == []


def test_backup_refuses_a_target_inside_the_data_folder(data: Path) -> None:
    with pytest.raises(ValueError, match="outside the data folder"):
        snapshot.backup(data, data / "backups", keep_days=30, now=NOW)


# --- check ---------------------------------------------------------------------------


def test_check_accepts_a_fresh_snapshot(data: Path, tmp_path: Path) -> None:
    made = snapshot.backup(data, tmp_path / "backups", keep_days=30, now=NOW)

    checked, problems, databases = snapshot.check(made)

    assert (checked, problems, databases) == (made, [], 3)


def test_check_on_the_backup_folder_checks_the_newest_snapshot(data: Path, tmp_path: Path) -> None:
    backups = tmp_path / "backups"
    snapshot.backup(data, backups, keep_days=30, now=NOW - timedelta(days=1))
    newest = snapshot.backup(data, backups, keep_days=30, now=NOW)
    (backups / ".tmp-20261121T000000Z").mkdir()  # a backup still being written

    assert snapshot.check(backups)[0] == newest


def test_check_finds_a_corrupted_database(data: Path, tmp_path: Path) -> None:
    made = snapshot.backup(data, tmp_path / "backups", keep_days=30, now=NOW)
    db = made / "orgs" / "acme" / "tazko.db"
    raw = bytearray(db.read_bytes())
    raw[4096 : 4096 + 512] = b"\xff" * 512  # the second page
    db.write_bytes(bytes(raw))

    _, problems, _ = snapshot.check(made)

    assert len(problems) == 1
    assert "orgs/acme/tazko.db" in problems[0]


def test_check_finds_a_live_company_without_its_database(data: Path, tmp_path: Path) -> None:
    made = snapshot.backup(data, tmp_path / "backups", keep_days=30, now=NOW)
    (made / "orgs" / "zeta" / "tazko.db").unlink()

    _, problems, _ = snapshot.check(made)

    assert problems == ["orgs/zeta/tazko.db: missing for company zeta"]


def test_check_finds_a_missing_control_database(tmp_path: Path) -> None:
    (tmp_path / "empty").mkdir()

    _, problems, _ = snapshot.check(tmp_path / "empty")

    assert problems == ["control.db: missing"]


def test_check_works_on_a_live_data_folder_without_changing_it(data: Path) -> None:
    files = [data / "control.db", data / "orgs" / "acme" / "tazko.db"]
    before = sorted(p.name for p in data.iterdir()), [f.read_bytes() for f in files]

    _, problems, databases = snapshot.check(data)

    assert (problems, databases) == ([], 3)
    assert (sorted(p.name for p in data.iterdir()), [f.read_bytes() for f in files]) == before


# --- purge-trash ----------------------------------------------------------------------


def test_purge_trash_removes_folders_older_than_the_limit(data: Path) -> None:
    trash = data / "trash"
    (trash / "young-20261101T000000Z").mkdir()
    (trash / "not-a-trash-folder").mkdir()

    removed = snapshot.purge_trash(data, older_than_days=30, now=NOW)

    assert [p.name for p in removed] == ["old-20260101T000000Z"]
    assert sorted(p.name for p in trash.iterdir()) == [
        "not-a-trash-folder",
        "young-20261101T000000Z",
    ]


def test_purge_trash_without_a_trash_folder_does_nothing(tmp_path: Path) -> None:
    assert snapshot.purge_trash(tmp_path, older_than_days=30, now=NOW) == []


# --- the commands ---------------------------------------------------------------------


def test_backup_then_check_succeed_from_the_command_line(
    data: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    backups = tmp_path / "backups"

    assert main(["backup", "--data", str(data), "--to", str(backups)]) == 0
    assert main(["check", "--data", str(backups)]) == 0

    out = capsys.readouterr().out
    assert f"backup written to {backups}" in out
    assert "ok: 3 databases" in out


def test_check_fails_on_a_corrupted_snapshot_from_the_command_line(
    data: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    made = snapshot.backup(data, tmp_path / "backups", keep_days=30, now=NOW)
    (made / "control.db").write_bytes(b"not a database at all" * 300)

    assert main(["check", "--data", str(made)]) == 1
    assert "control.db" in capsys.readouterr().err


def test_purge_trash_from_the_command_line(data: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["purge-trash", "--data", str(data)]) == 0

    assert not (data / "trash" / "old-20260101T000000Z").exists()
    assert "removed" in capsys.readouterr().out


def test_check_refuses_a_company_slug_that_would_leave_the_folder(
    data: Path, tmp_path: Path
) -> None:
    made = snapshot.backup(data, tmp_path / "backups", keep_days=30, now=NOW)
    conn = sqlite3.connect(made / "control.db")
    conn.execute("UPDATE orgs SET slug = '../../outside' WHERE slug = 'zeta'")
    conn.commit()
    conn.close()

    _, problems, _ = snapshot.check(made)

    assert problems == ["control.db: invalid company slug '../../outside'"]


def test_backup_removes_a_half_written_snapshot_left_by_a_crash(data: Path, tmp_path: Path) -> None:
    backups = tmp_path / "backups"
    (backups / ".tmp-20261118T023000Z").mkdir(parents=True)  # killed two days ago
    (backups / ".tmp-20261120T020000Z").mkdir()  # maybe still running: kept

    snapshot.backup(data, backups, keep_days=30, now=NOW)

    assert sorted(p.name for p in backups.iterdir()) == [
        ".tmp-20261120T020000Z",
        "20261120T023000Z",
    ]


def test_a_broken_company_database_fails_the_backup_with_its_name(
    data: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    broken = tmp_path / "broken"
    shutil.copytree(data, broken, ignore=shutil.ignore_patterns("*-wal", "*-shm"))
    (broken / "orgs" / "acme" / "tazko.db").write_bytes(b"garbage" * 1000)

    assert main(["backup", "--data", str(broken), "--to", str(tmp_path / "b")]) == 1

    err = capsys.readouterr().err
    assert "orgs" in err and "acme" in err
    assert "Traceback" not in err


@pytest.mark.parametrize(
    "argv",
    [
        ["purge-trash", "--older-than-days", "0"],
        ["purge-trash", "--older-than-days", "-5"],
        ["backup", "--to", "x", "--keep-days", "0"],
    ],
)
def test_day_counts_below_one_are_wrong_usage(argv: list[str]) -> None:
    with pytest.raises(SystemExit) as exit_:
        main(argv)

    assert exit_.value.code == 2


def set_versions(db: Path, *, user_version: int, oldest: int) -> None:
    conn = sqlite3.connect(db)
    try:
        conn.execute(f"PRAGMA user_version = {user_version}")
        conn.execute(f"PRAGMA application_id = {oldest}")
    finally:
        conn.close()


def test_check_finds_a_company_file_this_release_cannot_use(data: Path, tmp_path: Path) -> None:
    # given a newer release ran a contract migration on one company's file (D36)
    made = snapshot.backup(data, tmp_path / "backups", keep_days=30, now=NOW)
    set_versions(made / "orgs" / "acme" / "tazko.db", user_version=99, oldest=99)

    _, problems, _ = snapshot.check(made)

    assert len(problems) == 1
    assert problems[0].startswith("orgs/acme/tazko.db: version 99 is newer than this release")


def test_check_accepts_a_newer_file_its_migrations_allow(data: Path, tmp_path: Path) -> None:
    made = snapshot.backup(data, tmp_path / "backups", keep_days=30, now=NOW)
    set_versions(made / "control.db", user_version=99, oldest=1)

    assert snapshot.check(made)[1] == []
