"""Backups, checks and trash cleanup for a data folder (M1-08, build plan "Backups").

`backup` copies every database with SQLite's online backup API, so it runs
while the server does; WAL commits are included. A snapshot is written under
`.tmp-<stamp>` and renamed when complete, so a half-written one never counts.

`check` opens every database read-only and runs `PRAGMA integrity_check`; it
never changes what it checks, so it is safe on a live data folder too.

A data folder: control.db, secret, orgs/<slug>/{tazko.db,files/}, trash/.
"""

from __future__ import annotations

import contextlib
import os
import re
import shutil
import sqlite3
from datetime import UTC, datetime, timedelta
from pathlib import Path

STAMP = "%Y%m%dT%H%M%SZ"
SNAPSHOT = re.compile(r"^\d{8}T\d{6}Z$")
TRASHED = re.compile(r"^[a-z0-9](?:[a-z0-9-]{0,38}[a-z0-9])?-(\d{8}T\d{6}Z)$")
TMP = ".tmp-"


def _open_ro(path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(f"{path.resolve().as_uri()}?mode=ro", uri=True)
    conn.execute("PRAGMA query_only = ON")
    return conn


def _copy_db(source: Path, target: Path) -> None:
    """Online backup: a consistent copy of the last commit, WAL included."""
    os.close(os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600))
    src = _open_ro(source)
    try:
        dst = sqlite3.connect(target)
        try:
            src.backup(dst)
        finally:
            dst.close()
    finally:
        src.close()


def _copy_private(source: Path, target: Path) -> None:
    fd = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "wb") as out:
        out.write(source.read_bytes())


def _stamp_of(name: str) -> datetime | None:
    try:
        return datetime.strptime(name, STAMP).replace(tzinfo=UTC)
    except ValueError:
        return None


def backup(data: Path, to: Path, *, keep_days: int, now: datetime) -> Path:
    """Write data/ into to/<UTC stamp>/ and remove snapshots older than
    keep_days. The new snapshot is never removed. Returns its path."""
    data, to = data.resolve(), to.resolve()
    if to == data or data in to.parents:
        raise ValueError(f"backups must go outside the data folder ({to} is inside {data})")
    if not (data / "control.db").is_file():
        raise ValueError(f"{data} has no control.db; pass the server's data folder")
    to.mkdir(mode=0o700, parents=True, exist_ok=True)
    stamp = now.astimezone(UTC).strftime(STAMP)
    final = to / stamp
    if final.exists():
        raise FileExistsError(final)
    work = to / f"{TMP}{stamp}"
    work.mkdir(mode=0o700)
    try:
        _copy_db(data / "control.db", work / "control.db")
        if (data / "secret").is_file():
            _copy_private(data / "secret", work / "secret")
        orgs = data / "orgs"
        for folder in sorted(orgs.iterdir()) if orgs.is_dir() else []:
            if not (folder / "tazko.db").is_file():
                continue
            (work / "orgs" / folder.name).mkdir(mode=0o700, parents=True)
            _copy_db(folder / "tazko.db", work / "orgs" / folder.name / "tazko.db")
            if (folder / "files").is_dir():
                shutil.copytree(folder / "files", work / "orgs" / folder.name / "files")
        work.rename(final)
    except BaseException:
        shutil.rmtree(work, ignore_errors=True)
        raise
    _prune(to, keep=final, before=now - timedelta(days=keep_days))
    return final


def _prune(to: Path, *, keep: Path, before: datetime) -> None:
    for entry in to.iterdir():
        made = _stamp_of(entry.name) if SNAPSHOT.match(entry.name) else None
        if made is not None and made < before and entry != keep and entry.is_dir():
            shutil.rmtree(entry)


def newest(folder: Path) -> Path | None:
    """The newest complete snapshot in a backup folder."""
    found = sorted(e for e in folder.iterdir() if SNAPSHOT.match(e.name) and e.is_dir())
    return found[-1] if found else None


def check(path: Path) -> tuple[Path, list[str], int]:
    """Check a data folder or snapshot, or the newest snapshot of a backup
    folder. Returns (what was checked, problems, databases checked).

    TODO(M3-02): verify each attachment file against its hash once files exist."""
    if not (path / "control.db").exists() and path.is_dir():
        path = newest(path) or path
    problems: list[str] = []
    control = path / "control.db"
    if not control.is_file():
        return path, ["control.db: missing"], 0
    databases = [control]
    problems += _integrity(control, "control.db")
    live: list[str] = []
    if not problems:
        conn = _open_ro(control)
        try:
            live = [r[0] for r in conn.execute("SELECT slug FROM orgs WHERE status != 'deleted'")]
        except sqlite3.Error as err:
            problems.append(f"control.db: {err}")
        finally:
            conn.close()
    for slug in sorted(live):
        db = path / "orgs" / slug / "tazko.db"
        name = f"orgs/{slug}/tazko.db"
        if not db.is_file():
            problems.append(f"{name}: missing for company {slug}")
            continue
        databases.append(db)
        problems += _integrity(db, name)
    return path, problems, len(databases)


def _integrity(db: Path, name: str) -> list[str]:
    try:
        conn = _open_ro(db)
        try:
            result = [r[0] for r in conn.execute("PRAGMA integrity_check").fetchall()]
        finally:
            conn.close()
    except sqlite3.Error as err:
        return [f"{name}: {err}"]
    return [] if result == ["ok"] else [f"{name}: {'; '.join(result[:5])}"]


def purge_trash(data: Path, *, older_than_days: int, now: datetime) -> list[Path]:
    """Remove data/trash/<slug>-<stamp> folders whose stamp is older than the
    limit (D35). Anything else in trash/ is left alone."""
    trash = data / "trash"
    if not trash.is_dir():
        return []
    before = now - timedelta(days=older_than_days)
    removed: list[Path] = []
    for entry in sorted(trash.iterdir()):
        match = TRASHED.match(entry.name)
        made = _stamp_of(match[1]) if match else None
        if made is not None and made < before and entry.is_dir() and not entry.is_symlink():
            with contextlib.suppress(FileNotFoundError):
                shutil.rmtree(entry)
                removed.append(entry)
    return removed
