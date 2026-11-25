"""The super admin console's view of companies: list, create, suspend,
resume and delete them, and open one for its people and invites."""

from __future__ import annotations

import logging
import os
import sqlite3
from dataclasses import dataclass
from pathlib import Path

from tazko.core import clock
from tazko.core.errors import AppError, Conflict, Invalid, NotFound
from tazko.db import Database
from tazko.db.tenant import Tenant, Tenants, valid_slug
from tazko.modules.audit import service as audit
from tazko.modules.orgs import repository as repo
from tazko.modules.orgs.repository import Org
from tazko.modules.orgs.service import Company, create_company, require_super_admin
from tazko.modules.users import service as users

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class CompanySummary:
    """A company as the console's Companies page shows it. Boards come in M2."""

    org: Org
    members: int
    storage_bytes: int
    storage_limit_bytes: int | None
    last_activity_at: str | None


@dataclass(frozen=True)
class Console:
    """What a super admin reaches in the console. Only core/deps.py makes one,
    after checking the flag, so routes never hold the company cache itself.

    A super admin manages a company's people and invites without being a
    member, but never opens its boards: `open` gives a Company whose file is
    used only for membership events here."""

    control: Database
    tenants: Tenants
    actor_id: int

    def companies(self) -> list[CompanySummary]:
        def run(conn: sqlite3.Connection) -> list[repo.OrgCounts]:
            require_super_admin(conn, self.actor_id)
            return repo.all_with_counts(conn)

        return [self._summary(c) for c in self.control.read(run)]

    def company(self, slug: str) -> CompanySummary:
        def run(conn: sqlite3.Connection) -> repo.OrgCounts | None:
            require_super_admin(conn, self.actor_id)
            return repo.one_with_counts(conn, slug)

        found = self.control.read(run) if valid_slug(slug) else None
        if found is None:
            raise NotFound()
        return self._summary(found)

    def create(self, *, slug: str, name: str) -> Org:
        return create_company(
            self.control, self.tenants, slug=slug, name=name, actor_id=self.actor_id
        )

    def suspend(self, slug: str) -> CompanySummary:
        """Members lose access at once: open_company refuses a suspended
        company and sign-in refuses a person whose companies are all suspended."""
        return self._set_status(slug, to="suspended", event="company.suspended")

    def resume(self, slug: str) -> CompanySummary:
        return self._set_status(slug, to="active", event="company.resumed")

    def delete(self, slug: str, *, confirm: str) -> None:
        """Move the folder to trash and mark the row deleted. The move happens
        inside the control.db transaction; if that transaction then fails, the
        folder is moved back, so the company stays as it was. A row whose
        folder is already gone is still deleted. The row keeps its slug, so the
        folder can be restored by hand (D35)."""
        if confirm != slug:
            raise Invalid("confirm: type the short name of the company", field="confirm")
        moved: list[Path] = []

        def run(conn: sqlite3.Connection) -> None:
            org = self._live(conn, slug)
            now = clock.now()  # UTC (core/clock)
            if self.tenants.folder(slug).exists():
                moved.append(self.tenants.trash(slug, now.strftime("%Y%m%dT%H%M%SZ")))
            else:
                log.error("company %s has a row but no folder; deleting the row", slug)
            repo.mark_deleted(conn, org.id, now=clock.iso(now))
            audit.record(
                conn,
                "company.deleted",
                actor_id=self.actor_id,
                org_id=org.id,
                target=slug,
                detail={"trash": moved[0].name if moved else None},
            )

        try:
            self.control.write(run)
        except BaseException:
            if moved:
                moved[0].rename(self.tenants.folder(slug))  # the row was not deleted
            raise

    def _set_status(self, slug: str, *, to: str, event: str) -> CompanySummary:
        def run(conn: sqlite3.Connection) -> None:
            org = self._live(conn, slug)
            if org.status == to:
                code = "COMPANY_SUSPENDED" if to == "suspended" else "COMPANY_ACTIVE"
                raise Conflict(f"the company is already {org.status}", code=code)
            repo.set_status(conn, org.id, to)
            if to == "suspended":
                # Sign-in would refuse them now, so their open sessions end too.
                for user_id in repo.stranded_members(conn, org.id):
                    users.end_sessions(conn, user_id)
            audit.record(conn, event, actor_id=self.actor_id, org_id=org.id, target=slug)

        self.control.write(run)
        if to == "suspended":
            self.tenants.evict(slug)  # nothing keeps using its file
        return self.company(slug)

    def _live(self, conn: sqlite3.Connection, slug: str) -> Org:
        require_super_admin(conn, self.actor_id)
        org = repo.by_slug_not_deleted(conn, slug) if valid_slug(slug) else None
        if org is None:
            raise NotFound()
        return org

    def open(self, slug: str) -> Company:
        """The company's row only; its file opens when a change writes an event."""

        def run(conn: sqlite3.Connection) -> Org | None:
            require_super_admin(conn, self.actor_id)
            return repo.by_slug_not_deleted(conn, slug)

        org = self.control.read(run) if valid_slug(slug) else None
        if org is None:
            raise NotFound()
        return Company(org=org, role="super_admin", open_tenant=lambda: self._tenant(slug))

    def _tenant(self, slug: str) -> Tenant:
        try:
            return self.tenants.get(slug)
        except FileNotFoundError:
            log.error("company %s has a row but no database file", slug)
            raise AppError() from None

    def _summary(self, counts: repo.OrgCounts) -> CompanySummary:
        return CompanySummary(
            org=counts.org,
            members=counts.members,
            storage_bytes=_folder_size(self.tenants.folder(counts.org.slug)),
            storage_limit_bytes=counts.storage_limit_bytes,
            last_activity_at=counts.last_activity_at,
        )


def _folder_size(folder: Path) -> int:
    total = 0
    for root, _dirs, files in os.walk(folder):
        for name in files:
            try:
                total += (Path(root) / name).lstat().st_size  # a link counts as itself
            except OSError:  # removed while we walked
                continue
    return total
