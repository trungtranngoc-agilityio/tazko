"""`tazko backup`, `tazko check` and `tazko purge-trash` for a data folder.

Backups use SQLite's online backup API, so they run while the server does, and
are written under `.tmp-<stamp>` then renamed, so a half-written one never
counts. `check` opens everything read-only and is safe on a live folder.
Databases are copied one after another, not at one instant: a company made
or deleted during a backup can make that snapshot fail `check`; run it again.
"""

from __future__ import annotations

import contextlib
import logging
import os
import re
import shutil
import sqlite3
from datetime import UTC, datetime, timedelta
from importlib.resources import files
from pathlib import Path

from tazko.db.database import load_scripts
from tazko.db.tenant import valid_slug

log = logging.getLogger(__name__)

STAMP = "%Y%m%dT%H%M%SZ"
SNAPSHOT = re.compile(r"^\d{8}T\d{6}Z$")
TRASHED = re.compile(r"^[a-z0-9](?:[a-z0-9-]{0,38}[a-z0-9])?-(\d{8}T\d{6}Z)$")
TMP = ".tmp-"
# A .tmp- snapshot older than this was left by a backup that was killed.
STALE_TMP = timedelta(days=1)


class BackupFailed(Exception):
    """A database could not be copied; the message names it."""


def _open_ro(path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(f"{path.resolve().as_uri()}?mode=ro", uri=True)
    conn.execute("PRAGMA query_only = ON")
    return conn


def _copy_db(source: Path, target: Path) -> None:
    """Online backup: a consistent copy of the last commit, WAL included."""
    os.close(os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600))
    try:
        src = _open_ro(source)
        try:
            dst = sqlite3.connect(target)
            try:
                src.backup(dst)
            finally:
                dst.close()
        finally:
            src.close()
    except sqlite3.Error as err:
        raise BackupFailed(f"{source}: {err}") from err


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
                shutil.copytree(
                    folder / "files", work / "orgs" / folder.name / "files", symlinks=True
                )
        work.rename(final)
    except BaseException:
        shutil.rmtree(work, ignore_errors=True)
        raise
    _prune(to, keep=final, before=now - timedelta(days=keep_days), now=now)
    return final


def _prune(to: Path, *, keep: Path, before: datetime, now: datetime) -> None:
    """Remove old snapshots and half-written ones a killed backup left. A
    failure is logged and skipped: the new snapshot is already good."""
    for entry in to.iterdir():
        if SNAPSHOT.match(entry.name):
            made, limit = _stamp_of(entry.name), before
        elif entry.name.startswith(TMP):
            made, limit = _stamp_of(entry.name.removeprefix(TMP)), now - STALE_TMP
        else:
            continue
        if made is None or made >= limit or entry == keep or not entry.is_dir():
            continue
        try:
            shutil.rmtree(entry)
        except OSError as err:
            log.warning("could not remove old backup %s: %s", entry, err)


def newest(folder: Path) -> Path | None:
    """The newest complete snapshot in a backup folder."""
    found = sorted(e for e in folder.iterdir() if SNAPSHOT.match(e.name) and e.is_dir())
    return found[-1] if found else None


def check(path: Path) -> tuple[Path, list[str], int]:
    """Check a data folder or snapshot, or the newest snapshot of a backup
    folder. Returns (what was checked, problems, databases checked)."""
    if not (path / "control.db").exists() and path.is_dir():
        path = newest(path) or path
    problems: list[str] = []
    control = path / "control.db"
    if not control.is_file():
        return path, ["control.db: missing"], 0
    databases = [control]
    problems += _integrity(control, "control.db", "control")
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
        if not valid_slug(slug):  # a path is only ever built from a checked slug
            problems.append(f"control.db: invalid company slug {slug!r}")
            continue
        db = path / "orgs" / slug / "tazko.db"
        name = f"orgs/{slug}/tazko.db"
        if not db.is_file():
            problems.append(f"{name}: missing for company {slug}")
            continue
        databases.append(db)
        problems += _integrity(db, name, "tenant")
    return path, problems, len(databases)


def _latest(schema: str) -> int:
    return len(load_scripts(files("tazko") / "migrations" / schema))


def _integrity(db: Path, name: str, schema: str) -> list[str]:
    """integrity_check, then whether this release can use the file: a newer
    file is fine only if its migrations allow this release. release.sh
    runs check after a rollback, since /health opens only control.db."""
    try:
        conn = _open_ro(db)
        try:
            result = [r[0] for r in conn.execute("PRAGMA integrity_check").fetchall()]
            current: int = conn.execute("PRAGMA user_version").fetchone()[0]
            oldest: int = conn.execute("PRAGMA application_id").fetchone()[0]
        finally:
            conn.close()
    except sqlite3.Error as err:
        return [f"{name}: {err}"]
    if result != ["ok"]:
        return [f"{name}: {'; '.join(result[:5])}"]
    latest = _latest(schema)
    if current > latest and not 1 <= oldest <= latest:
        return [
            f"{name}: version {current} is newer than this release ({latest}) and does not allow it"
        ]
    return []


def purge_trash(data: Path, *, older_than_days: int, now: datetime) -> list[Path]:
    """Remove data/trash/<slug>-<stamp> folders whose stamp is older than the
    limit. Anything else in trash/ is left alone."""
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
                log.info("removed %s from trash for good", entry.name)
    return removed
