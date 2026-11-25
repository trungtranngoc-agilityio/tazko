"""Console pages that read across modules: the audit log and the Server page.

Every function checks the actor in the database, inside its own read.
"""

from __future__ import annotations

import os
import sqlite3
import time
from dataclasses import dataclass
from pathlib import Path

from tazko import __version__
from tazko.core.config import Settings
from tazko.db import Database
from tazko.modules.audit import service as audit
from tazko.modules.audit.service import Entry
from tazko.modules.users import service as users

__all__ = ["Email", "Entry", "ServerInfo", "audit_page", "server_info"]


def audit_page(
    control: Database, *, actor_id: int, before: int | None, limit: int, kind: str | None
) -> tuple[list[Entry], int | None]:
    """One page of the audit log, newest first, and the cursor for the next."""

    def run(conn: sqlite3.Connection) -> list[Entry]:
        users.require_super_admin(conn, actor_id)
        return audit.page(conn, before=before, limit=limit + 1, kind=kind)

    rows = control.read(run)
    more = len(rows) > limit
    rows = rows[:limit]
    return rows, (rows[-1].id if more else None)


@dataclass(frozen=True)
class Email:
    enabled: bool
    host: str | None
    port: int | None
    sender: str | None


@dataclass(frozen=True)
class ServerInfo:
    version: str
    public_url: str
    uptime_seconds: int
    data_bytes: int
    email: Email


def server_info(
    control: Database, settings: Settings, *, actor_id: int, started: float
) -> ServerInfo:
    """Version, uptime, data size and email status. The SMTP user and password
    never leave the settings file."""
    control.read(lambda conn: users.require_super_admin(conn, actor_id))
    on = settings.email_enabled
    return ServerInfo(
        version=__version__,
        public_url=settings.api_url,
        uptime_seconds=int(time.monotonic() - started),
        data_bytes=_size(settings.data_dir),
        email=Email(
            enabled=on,
            host=settings.smtp_host if on else None,
            port=settings.smtp_port if on else None,
            sender=settings.mail_from if on else None,
        ),
    )


def _size(folder: Path) -> int:
    total = 0
    for root, _dirs, files in os.walk(folder):
        for name in files:
            try:
                total += (Path(root) / name).lstat().st_size
            except OSError:  # removed while we walked
                continue
    return total
