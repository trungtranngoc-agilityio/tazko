"""Companies: one database file each, opened only for members."""

from __future__ import annotations

import os
import sqlite3
import stat
import threading
import time
from collections.abc import Iterator
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

import pytest

from tazko.core.errors import Conflict, Invalid, NotFound
from tazko.db import Database, MigrationError
from tazko.db import tenant as tenant_module
from tazko.db.tenant import Tenants
from tazko.modules.orgs import service as orgs
from tazko.modules.users import service as users


@pytest.fixture
def control(tmp_path: Path) -> Iterator[Database]:
    db = Database(tmp_path / "control.db", "control")
    yield db
    db.close()


@pytest.fixture
def tenants(tmp_path: Path) -> Iterator[Tenants]:
    cache = Tenants(tmp_path)
    yield cache
    cache.close()


def people(company: orgs.Company) -> set[str]:
    rows = company.tenant.db.read(lambda c: c.execute("SELECT name FROM people").fetchall())
    return {row["name"] for row in rows}


def column(db: Database, sql: str) -> list[str]:
    def run(conn: sqlite3.Connection) -> list[str]:
        return [row[0] for row in conn.execute(sql)]

    return db.read(run)


def test_person_in_two_companies_sees_only_the_chosen_one(
    control: Database, tenants: Tenants, tmp_path: Path
) -> None:
    # given Ana in Acme and Beta, and Bo only in Acme
    acme = orgs.create_company(control, tenants, slug="acme", name="Acme", actor_id=None)
    beta = orgs.create_company(control, tenants, slug="beta", name="Beta", actor_id=None)
    ana = users.get_or_create(control, "ana@example.com", name="Ana")
    bo = users.get_or_create(control, "bo@example.com", name="Bo")
    for org in (acme, beta):
        orgs.add_member(control, tenants, org=org, user=ana, role="member", actor_id=None)
    orgs.add_member(control, tenants, org=acme, user=bo, role="owner", actor_id=None)

    # when Ana opens Beta
    company = orgs.open_company(control, tenants, user_id=ana.id, slug="beta")

    # then she sees Beta's data only, from Beta's own file
    assert company.org.slug == "beta"
    assert company.role == "member"
    assert people(company) == {"Ana"}
    assert company.tenant.db.path == tmp_path / "orgs" / "beta" / "tazko.db"
    assert company.tenant.files_dir == tmp_path / "orgs" / "beta" / "files"
    acme_view = orgs.open_company(control, tenants, user_id=ana.id, slug="acme")
    assert people(acme_view) == {"Ana", "Bo"}
    assert acme_view.tenant.db.path != company.tenant.db.path
    assert [m.org.slug for m in orgs.companies_of(control, ana.id)] == ["acme", "beta"]
    assert [m.org.slug for m in orgs.companies_of(control, bo.id)] == ["acme"]


def test_non_member_cannot_open_company(control: Database, tenants: Tenants) -> None:
    orgs.create_company(control, tenants, slug="acme", name="Acme", actor_id=None)
    outsider = users.get_or_create(control, "out@example.com", name="Out")
    with pytest.raises(NotFound):
        orgs.open_company(control, tenants, user_id=outsider.id, slug="acme")


def test_unknown_company_is_not_found(control: Database, tenants: Tenants) -> None:
    ana = users.get_or_create(control, "ana@example.com", name="Ana")
    with pytest.raises(NotFound):
        orgs.open_company(control, tenants, user_id=ana.id, slug="nope")


def test_bad_slug_when_opening_is_not_found(control: Database, tenants: Tenants) -> None:
    ana = users.get_or_create(control, "ana@example.com", name="Ana")
    with pytest.raises(NotFound):
        orgs.open_company(control, tenants, user_id=ana.id, slug="../acme")


@pytest.mark.parametrize("slug", ["../x", "Acme", "a/b", "", "-acme", "acme-", "a" * 41])
def test_bad_slug_is_refused(
    control: Database, tenants: Tenants, tmp_path: Path, slug: str
) -> None:
    with pytest.raises(Invalid) as raised:
        orgs.create_company(control, tenants, slug=slug, name="X", actor_id=None)
    assert raised.value.details[0].field == "slug"
    assert not (tmp_path / "orgs").exists() or list((tmp_path / "orgs").iterdir()) == []


@pytest.mark.parametrize("name", ["", "   ", "x" * 101])
def test_empty_or_long_name_is_refused(control: Database, tenants: Tenants, name: str) -> None:
    with pytest.raises(Invalid) as raised:
        orgs.create_company(control, tenants, slug="acme", name=name, actor_id=None)
    assert raised.value.details[0].field == "name"
    assert column(control, "SELECT slug FROM orgs") == []


@pytest.mark.parametrize(
    "email",
    [
        "not-an-email",
        "a@b",
        "a b@example.com",
        "",
        "\u212aate@example.com",  # Kelvin sign: lower() turns it into "kate@..."
        "admin@example.com\u200b",  # zero-width space: a look-alike of admin@
        "\u00e4dmin@example.com",
        "admin@exa\nmple.com",
    ],
)
def test_bad_email_is_refused(control: Database, email: str) -> None:
    with pytest.raises(Invalid) as raised:
        users.get_or_create(control, email, name="X")
    assert raised.value.status == 422
    assert raised.value.details[0].field == "email"


def test_duplicate_slug_is_refused(control: Database, tenants: Tenants) -> None:
    orgs.create_company(control, tenants, slug="acme", name="Acme", actor_id=None)
    with pytest.raises(Conflict) as raised:
        orgs.create_company(control, tenants, slug="acme", name="Acme 2", actor_id=None)
    assert raised.value.code == "SLUG_TAKEN"


@pytest.mark.skipif(os.name == "nt", reason="POSIX file modes")
def test_company_folder_and_database_are_private(control: Database, tenants: Tenants) -> None:
    orgs.create_company(control, tenants, slug="acme", name="Acme", actor_id=None)
    tenant = tenants.get("acme")
    for path in (tenant.db.path.parent, tenant.files_dir, tenant.db.path):
        assert stat.S_IMODE(path.stat().st_mode) & 0o077 == 0, path


def test_company_files_are_cached_and_reopened(
    control: Database, tenants: Tenants, tmp_path: Path
) -> None:
    orgs.create_company(control, tenants, slug="acme", name="Acme", actor_id=None)
    assert tenants.get("acme") is tenants.get("acme")
    tenants.close()
    reopened = Tenants(tmp_path)
    try:
        assert reopened.get("acme").db.version >= 1
    finally:
        reopened.close()


class SlowDatabase(Database):
    """Opening the company `slow` waits until the test lets it go."""

    release = threading.Event()

    def __init__(self, path: Path, schema: str, **kwargs: Any) -> None:
        if path.parent.name == "slow":
            assert SlowDatabase.release.wait(10)
        super().__init__(path, schema, **kwargs)


def test_opening_one_company_does_not_block_another(
    control: Database, tenants: Tenants, monkeypatch: pytest.MonkeyPatch
) -> None:
    # given acme is open and slow is being opened (a long migration)
    for slug in ("acme", "beta", "slow"):
        orgs.create_company(control, tenants, slug=slug, name=slug, actor_id=None)
    tenants.close()
    tenants.get("acme")
    monkeypatch.setattr(tenant_module, "Database", SlowDatabase)
    SlowDatabase.release.clear()
    with ThreadPoolExecutor(2) as pool:
        opening = pool.submit(tenants.get, "slow")
        time.sleep(0.1)
        try:
            # then the open company and another new one are served meanwhile
            assert pool.submit(tenants.get, "acme").result(timeout=1).slug == "acme"
            assert tenants.get("beta").slug == "beta"
            assert not opening.done()
        finally:
            SlowDatabase.release.set()
        assert opening.result(timeout=5).slug == "slow"


def test_same_company_opened_at_once_is_opened_once(control: Database, tenants: Tenants) -> None:
    orgs.create_company(control, tenants, slug="acme", name="Acme", actor_id=None)
    tenants.close()
    with ThreadPoolExecutor(8) as pool:
        opened = list(pool.map(lambda _: tenants.get("acme"), range(16)))
    assert all(t is opened[0] for t in opened)


def test_failed_company_creation_leaves_no_folder(
    control: Database, tenants: Tenants, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # given the new company's database cannot be migrated
    def broken(*args: object, **kwargs: object) -> Database:
        raise MigrationError("migration 0001_init failed: disk full")

    monkeypatch.setattr(tenant_module, "Database", broken)
    with pytest.raises(MigrationError):
        orgs.create_company(control, tenants, slug="acme", name="Acme", actor_id=None)

    # then no row and no folder are left, so the slug can be used again
    assert not (tmp_path / "orgs" / "acme").exists()
    assert column(control, "SELECT slug FROM orgs") == []
    monkeypatch.undo()
    assert orgs.create_company(control, tenants, slug="acme", name="Acme", actor_id=None)


def test_creating_a_company_writes_an_audit_row(control: Database, tenants: Tenants) -> None:
    orgs.create_company(control, tenants, slug="acme", name="Acme", actor_id=None)
    assert column(control, "SELECT action FROM audit_log") == ["company.created"]


def test_adding_a_member_writes_an_event_in_the_company(
    control: Database, tenants: Tenants
) -> None:
    acme = orgs.create_company(control, tenants, slug="acme", name="Acme", actor_id=None)
    ana = users.get_or_create(control, "ana@example.com", name="Ana")
    orgs.add_member(control, tenants, org=acme, user=ana, role="member", actor_id=None)
    assert column(tenants.get("acme").db, "SELECT type FROM events") == ["member.added"]
    assert column(control, "SELECT action FROM audit_log ORDER BY id") == [
        "company.created",
        "member.added",
    ]


def test_disabled_person_cannot_open_company(control: Database, tenants: Tenants) -> None:
    acme = orgs.create_company(control, tenants, slug="acme", name="Acme", actor_id=None)
    ana = users.get_or_create(control, "ana@example.com", name="Ana")
    orgs.add_member(control, tenants, org=acme, user=ana, role="owner", actor_id=None)
    control.write(lambda c: c.execute("UPDATE users SET disabled_at = 'x' WHERE id = ?", (ana.id,)))

    with pytest.raises(NotFound):
        orgs.open_company(control, tenants, user_id=ana.id, slug="acme")
