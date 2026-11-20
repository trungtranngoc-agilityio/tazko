"""One SQLite file: a single writer thread, a small read pool, migrations.

Every write runs on the file's own writer thread inside `BEGIN IMMEDIATE`, so
writes to one company never interleave and a busy company never blocks
another. Reads use separate `query_only` connections; with WAL they see the
last committed state and do not wait for the writer.

Callers pass a function that receives the connection:

    db.write(lambda c: c.execute("INSERT ..."))
    rows = db.read(lambda c: c.execute("SELECT ...").fetchall())

Both block the calling thread, so FastAPI routes that use them are plain
`def` routes (run in the thread pool), never `async def`.
"""

from __future__ import annotations

import logging
import os
import queue
import re
import sqlite3
import threading
from collections.abc import Callable
from concurrent.futures import Future
from importlib.resources import files
from importlib.resources.abc import Traversable
from pathlib import Path
from typing import Any

log = logging.getLogger(__name__)

SCRIPT_NAME = re.compile(r"^(\d{4})_[a-z0-9_]+\.sql$")
# First line of a migration that an older release can live with (expand-contract, D21):
# "-- readers: N" means a release that knows migrations up to N can still use the file.
READERS = re.compile(r"\A--[ \t]*readers:[ \t]*(\d+)[ \t]*$", re.MULTILINE)
BUSY_TIMEOUT_MS = 5000
READ_WAIT_SECONDS = 30


class MigrationError(RuntimeError):
    """A migration failed or the file is newer than this code. Nothing was changed."""


type Job = tuple[Callable[[sqlite3.Connection], Any], Future[Any]]


def connect(path: Path, *, readonly: bool = False) -> sqlite3.Connection:
    # isolation_level=None: no hidden transactions; this module opens them itself.
    conn = sqlite3.connect(
        path, isolation_level=None, check_same_thread=False, timeout=BUSY_TIMEOUT_MS / 1000
    )
    conn.row_factory = sqlite3.Row
    conn.execute(f"PRAGMA busy_timeout = {BUSY_TIMEOUT_MS}")
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA synchronous = NORMAL")
    if readonly:
        conn.execute("PRAGMA query_only = ON")
    else:
        conn.execute("PRAGMA journal_mode = WAL")
    return conn


def load_scripts(source: Path | Traversable) -> list[tuple[int, str, str]]:
    """(version, name, sql) sorted by version; versions must run 1, 2, 3 ..."""
    found: list[tuple[int, str, str]] = []
    for entry in source.iterdir():
        match = SCRIPT_NAME.match(entry.name)
        if match:
            found.append((int(match[1]), entry.name.removesuffix(".sql"), entry.read_text("utf-8")))
    found.sort()
    for expected, (version, name, sql) in enumerate(found, start=1):
        if version != expected:
            raise MigrationError(f"{name}: expected migration {expected:04d} next")
        if not 1 <= readers_of(version, sql) <= version:
            raise MigrationError(f"{name}: readers must be between 1 and {version}")
    return found


def readers_of(version: int, sql: str) -> int:
    """The oldest release (named by its newest migration) that can use the file
    after this migration. Without a mark, only releases that have the migration."""
    match = READERS.match(sql)
    return int(match[1]) if match else version


def oldest_reader(scripts: list[tuple[int, str, str]]) -> int:
    """After running `scripts`, the oldest release that can still use the file:
    every migration newer than that release must allow it. Stored in
    PRAGMA application_id next to user_version (D36)."""
    oldest = len(scripts)
    needed = 0
    for version, _name, sql in reversed(scripts[1:]):
        needed = max(needed, readers_of(version, sql))
        if needed > version - 1:
            break
        oldest = version - 1
    return oldest


def migrate(conn: sqlite3.Connection, scripts: list[tuple[int, str, str]], label: str) -> int:
    current: int = conn.execute("PRAGMA user_version").fetchone()[0]
    latest = scripts[-1][0] if scripts else 0
    if current > latest:
        oldest: int = conn.execute("PRAGMA application_id").fetchone()[0]
        if not 1 <= oldest <= latest:
            raise MigrationError(
                f"{label} is at version {current}, newer than this release ({latest}), and "
                "its migrations do not allow this release: run the newer release or "
                "restore the pre-release backup"
            )
        log.warning("%s: version %s is newer than this release (%s)", label, current, latest)
        return current
    for version, name, sql in scripts[current:]:
        oldest = oldest_reader(scripts[:version])
        try:
            # One script, one transaction: the schema, the version and the oldest
            # release that can still use the file move together. application_id is
            # SQLite's file-type marker; Tazko stores that release number in it (D36).
            conn.executescript(
                f"BEGIN IMMEDIATE;\n{sql}\n;PRAGMA user_version = {version};\n"
                f"PRAGMA application_id = {oldest};\nCOMMIT;"
            )
        except sqlite3.Error as err:
            if conn.in_transaction:
                conn.execute("ROLLBACK")
            raise MigrationError(f"{label}: migration {name} failed: {err}") from err
        log.info("%s: migrated to %s", label, name)
    return latest


class Database:
    def __init__(
        self,
        path: Path,
        schema: str,
        *,
        readers: int = 2,
        migrations: Path | None = None,
    ) -> None:
        """Open (creating if needed) and migrate `path`.

        `schema` names the folder under tazko/migrations (`control` or
        `tenant`); `migrations` points somewhere else, for tests.
        """
        self.path = path
        self.schema = schema
        source = migrations or files("tazko") / "migrations" / schema
        scripts = load_scripts(source)
        path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        # Made 600 before SQLite opens it; SQLite gives -wal and -shm the same mode.
        if not path.exists():
            os.close(os.open(path, os.O_WRONLY | os.O_CREAT, 0o600))

        self._jobs: queue.SimpleQueue[Job | None] = queue.SimpleQueue()
        # Guards `_closed` and the enqueue together, so no job can land behind
        # the stop marker that close() puts on the queue.
        self._state = threading.Lock()
        self._closed = False
        started: Future[int] = Future()
        self._writer = threading.Thread(
            target=self._run_writer,
            args=(scripts, started),
            name=f"db-writer:{path.parent.name}/{path.name}",
            daemon=True,
        )
        self._writer.start()
        self.version = started.result()  # re-raises a failed migration

        self._readers: queue.Queue[sqlite3.Connection] = queue.Queue()
        for _ in range(readers):
            self._readers.put(connect(path, readonly=True))
        self._reader_count = readers

    def _run_writer(self, scripts: list[tuple[int, str, str]], started: Future[int]) -> None:
        try:
            conn = connect(self.path)
            try:
                version = migrate(conn, scripts, str(self.path))
            except BaseException:
                conn.close()
                raise
        except BaseException as err:
            started.set_exception(err)
            return
        started.set_result(version)
        try:
            while (job := self._jobs.get()) is not None:
                fn, future = job
                if not future.set_running_or_notify_cancel():
                    continue
                try:
                    conn.execute("BEGIN IMMEDIATE")
                    result = fn(conn)
                    conn.execute("COMMIT")
                except BaseException as err:
                    if conn.in_transaction:
                        conn.execute("ROLLBACK")
                    future.set_exception(err)
                else:
                    future.set_result(result)
        finally:
            conn.close()

    def write[T](self, fn: Callable[[sqlite3.Connection], T]) -> T:
        """Run `fn` in one transaction on the writer thread and return its result."""
        if threading.current_thread() is self._writer:
            raise RuntimeError("write() called from inside a write; use the connection given")
        future: Future[T] = Future()
        with self._state:
            if self._closed:
                raise RuntimeError(f"{self.path} is closed")
            self._jobs.put((fn, future))
        return future.result()

    def read[T](self, fn: Callable[[sqlite3.Connection], T]) -> T:
        """Run `fn` on a read-only connection inside one read transaction."""
        if self._closed:
            raise RuntimeError(f"{self.path} is closed")
        conn = self._readers.get(timeout=READ_WAIT_SECONDS)
        try:
            conn.execute("BEGIN")
            try:
                return fn(conn)
            finally:
                if conn.in_transaction:
                    conn.execute("ROLLBACK")
        finally:
            self._readers.put(conn)

    def close(self) -> None:
        """Finish queued writes, then close every connection. Safe to call twice."""
        with self._state:
            if self._closed:
                return
            self._closed = True
            self._jobs.put(None)
        self._writer.join()
        for _ in range(self._reader_count):
            self._readers.get().close()
