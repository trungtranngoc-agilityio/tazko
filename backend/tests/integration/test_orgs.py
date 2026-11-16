"""Companies: one database file each, opened only for members."""

from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from pathlib import Path

import pytest

from tazko.core.errors import BadRequest, NotFound
from tazko.db import Database
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
    with pytest.raises(BadRequest):
        orgs.create_company(control, tenants, slug=slug, name="X", actor_id=None)
    assert not (tmp_path / "orgs").exists() or list((tmp_path / "orgs").iterdir()) == []


def test_duplicate_slug_is_refused(control: Database, tenants: Tenants) -> None:
    orgs.create_company(control, tenants, slug="acme", name="Acme", actor_id=None)
    with pytest.raises(BadRequest, match="taken"):
        orgs.create_company(control, tenants, slug="acme", name="Acme 2", actor_id=None)


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
