"""Handles to exactly one company's file and folder (data/orgs/<slug>/).

A slug is checked before any path is built from it. Membership is checked by
orgs.service.open_company, the only way handlers reach a Tenant.
"""

from __future__ import annotations

import re
import shutil
import threading
from dataclasses import dataclass
from pathlib import Path

from tazko.db.database import Database

SLUG = re.compile(r"^[a-z0-9](?:[a-z0-9-]{0,38}[a-z0-9])?$")
STAMP = re.compile(r"\d{8}T\d{6}Z")  # UTC, as tazko purge-trash reads it


def valid_slug(slug: str) -> bool:
    """Lowercase letters, digits and inner hyphens, 1 to 40 characters."""
    return bool(SLUG.fullmatch(slug))


@dataclass(frozen=True)
class Tenant:
    slug: str
    db: Database
    files_dir: Path


class Tenants:
    """Opens each company file once (migrating it) and keeps it open.

    An open company is returned without taking any lock. Opening one takes a
    lock for that slug only, so a long migration of one company never holds
    up requests for another (CLAUDE.md: a busy company never blocks another).
    """

    def __init__(self, data_dir: Path, *, readers: int = 2) -> None:
        self.root = data_dir / "orgs"
        self._readers = readers
        self._open: dict[str, Tenant] = {}
        self._lock = threading.Lock()  # guards _open and _opening, held only briefly
        self._opening: dict[str, threading.Lock] = {}

    def folder(self, slug: str) -> Path:
        if not valid_slug(slug):
            raise ValueError(f"invalid company slug: {slug!r}")
        return self.root / slug

    def exists(self, slug: str) -> bool:
        return (self.folder(slug) / "tazko.db").exists()

    def create(self, slug: str) -> Tenant:
        """Make the folder and an empty, migrated database. On failure nothing
        is left behind, so the slug stays free."""
        folder = self.folder(slug)
        if folder.exists():
            raise FileExistsError(folder)
        self.root.mkdir(mode=0o700, parents=True, exist_ok=True)
        folder.mkdir(mode=0o700)
        (folder / "files").mkdir(mode=0o700)
        try:
            return self.get(slug, create=True)
        except BaseException:
            self.evict(slug)
            shutil.rmtree(folder, ignore_errors=True)
            raise

    def get(self, slug: str, *, create: bool = False) -> Tenant:
        folder = self.folder(slug)
        tenant = self._open.get(slug)  # a dict read is atomic; no lock for open companies
        if tenant is not None:
            return tenant
        with self._lock:
            opening = self._opening.setdefault(slug, threading.Lock())
        with opening:
            tenant = self._open.get(slug)  # another thread may have opened it meanwhile
            if tenant is None:
                if not create and not (folder / "tazko.db").exists():
                    raise FileNotFoundError(folder / "tazko.db")
                db = Database(folder / "tazko.db", "tenant", readers=self._readers)
                tenant = Tenant(slug=slug, db=db, files_dir=folder / "files")
                with self._lock:
                    self._open[slug] = tenant
            return tenant

    def trash(self, slug: str, stamp: str) -> Path:
        """Close the company's file and move its folder to data/trash/<slug>-<stamp>/.
        Trash older than 30 days is removed by the nightly job."""
        if not STAMP.fullmatch(stamp):
            raise ValueError(f"invalid trash stamp: {stamp!r}")
        folder = self.folder(slug)
        with self._lock:
            opening = self._opening.setdefault(slug, threading.Lock())
        # Held across close and move: a request racing the delete cannot open
        # the file again in between; after the move, get() finds no file.
        with opening:
            self.evict(slug)
            bin_dir = self.root.parent / "trash"
            bin_dir.mkdir(mode=0o700, parents=True, exist_ok=True)
            target = bin_dir / f"{slug}-{stamp}"
            if target.exists():
                raise FileExistsError(target)
            folder.rename(target)  # same file system: data/orgs and data/trash share data/
        return target

    def is_open(self, slug: str) -> bool:
        """Whether the company's file is open in the cache (tests, diagnostics)."""
        return slug in self._open

    def evict(self, slug: str) -> None:
        """Close one company's file (before suspend, delete or restore)."""
        with self._lock:
            tenant = self._open.pop(slug, None)
        if tenant:
            tenant.db.close()

    def close(self) -> None:
        with self._lock:
            open_now, self._open = list(self._open.values()), {}
        for tenant in open_now:
            tenant.db.close()
