"""Company lifecycle (M1-07): create, suspend, resume, delete to trash/.
One test per state, through HTTP with real sessions."""

from __future__ import annotations

import json
import re
import shutil
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from tazko.db import Database
from tazko.db.tenant import Tenants
from tazko.modules.audit import service as audit_service
from tazko.modules.invites import service as invites
from tazko.modules.orgs import service as orgs
from tazko.modules.orgs.console import Console
from tazko.modules.orgs.service import Org
from tazko.modules.users import service as users
from tazko.modules.users.service import User
from tests.integration.oidc import SAME_ORIGIN, WEB, FakeGoogle, audit, sign_in


@pytest.fixture
def tenants(client: TestClient) -> Tenants:
    found: Tenants = client.app.state.tenants  # type: ignore[attr-defined]  # TestClient.app is typed as ASGIApp
    return found


@pytest.fixture
def admin(control: Database) -> User:
    made, _ = users.grant_super_admin(control, "admin@example.com", actor_id=None)
    return made


@pytest.fixture
def acme(control: Database, tenants: Tenants) -> Org:
    return orgs.create_company(control, tenants, slug="acme", name="Acme", actor_id=None)


@pytest.fixture
def ana(control: Database, tenants: Tenants, acme: Org) -> User:
    user = users.get_or_create(control, "ana@example.com", name="Ana")
    orgs.add_member(control, tenants, org=acme, user=user, role="owner", actor_id=None)
    return user


def as_(client: TestClient, google: FakeGoogle, user: User) -> Any:
    client.cookies.clear()
    return sign_in(client, google, sub=f"sub-{user.id}", email=user.email, name=user.name or "X")


def call(client: TestClient, method: str, path: str, body: Any = None) -> Any:
    return client.request(method, path, json=body, headers=SAME_ORIGIN)


def status(control: Database) -> str:
    return str(control.read(lambda c: c.execute("SELECT status FROM orgs").fetchone()[0]))


# --- create --------------------------------------------------------------------------


def test_create_makes_the_folder_and_a_migrated_database(
    client: TestClient, google: FakeGoogle, admin: User, tenants: Tenants
) -> None:
    as_(client, google, admin)

    created = call(client, "POST", "/admin/api/companies", {"slug": "acme", "name": "Acme"})

    assert created.status_code == 201
    assert created.json()["status"] == "active"
    assert (tenants.folder("acme") / "tazko.db").is_file()
    assert (tenants.folder("acme") / "files").is_dir()


# --- suspend -------------------------------------------------------------------------


def test_suspend_blocks_the_members_api_access_at_once(
    client: TestClient, google: FakeGoogle, control: Database, admin: User, ana: User
) -> None:
    # given Ana is signed in and works in Acme
    as_(client, google, ana)
    assert client.get("/api/orgs/acme/members").status_code == 200
    ana_cookies = dict(client.cookies)

    # when a super admin suspends Acme
    as_(client, google, admin)
    suspended = call(client, "POST", "/admin/api/companies/acme/suspend")

    # then the console shows it suspended and Ana's open session is over
    assert suspended.status_code == 200
    assert suspended.json()["status"] == "suspended"
    client.cookies.clear()
    client.cookies.update(ana_cookies)
    assert client.get("/api/orgs/acme/members").status_code == 401
    assert client.get("/api/orgs").status_code == 401
    assert [(r["target"], r["actor_id"]) for r in audit(control, "company.suspended")] == [
        ("acme", admin.id)
    ]


def test_suspend_signs_out_members_with_no_other_active_company(
    client: TestClient,
    google: FakeGoogle,
    control: Database,
    tenants: Tenants,
    admin: User,
    ana: User,
) -> None:
    # given Ana (only in Acme) and Bo (also in active Zeta) are signed in
    bo = users.get_or_create(control, "bo@example.com", name="Bo")
    orgs.add_member(control, tenants, org=ana_org(control), user=bo, role="member", actor_id=None)
    zeta = orgs.create_company(control, tenants, slug="zeta", name="Zeta", actor_id=None)
    orgs.add_member(control, tenants, org=zeta, user=bo, role="member", actor_id=None)
    as_(client, google, ana)
    as_(client, google, bo)

    # when a super admin suspends Acme
    as_(client, google, admin)
    call(client, "POST", "/admin/api/companies/acme/suspend")

    # then Ana is signed out at once; Bo and the super admin keep their sessions
    def sessions(user: User) -> int:
        return int(
            control.read(
                lambda c: c.execute(
                    "SELECT count(*) FROM sessions WHERE user_id = ?", (user.id,)
                ).fetchone()[0]
            )
        )

    assert (sessions(ana), sessions(bo), sessions(admin)) == (0, 1, 1)


def ana_org(control: Database) -> Org:
    found = control.read(lambda c: c.execute("SELECT id FROM orgs WHERE slug = 'acme'").fetchone())
    return Org(id=found["id"], slug="acme", name="Acme", status="active")


def test_a_member_whose_only_company_is_suspended_cannot_sign_in(
    client: TestClient, google: FakeGoogle, control: Database, admin: User, ana: User
) -> None:
    as_(client, google, admin)
    call(client, "POST", "/admin/api/companies/acme/suspend")

    response = as_(client, google, ana)

    assert response.headers["location"] == f"{WEB}/signin/refused"
    assert [json.loads(r["detail"]) for r in audit(control, "signin.refused")] == [
        {"reason": "company_suspended"}
    ]
    assert client.get("/auth/refusal").json()["reason"] == "company_suspended"


def test_a_member_with_another_active_company_still_signs_in(
    client: TestClient,
    google: FakeGoogle,
    control: Database,
    tenants: Tenants,
    admin: User,
    ana: User,
) -> None:
    zeta = orgs.create_company(control, tenants, slug="zeta", name="Zeta", actor_id=None)
    orgs.add_member(control, tenants, org=zeta, user=ana, role="member", actor_id=None)
    as_(client, google, admin)
    call(client, "POST", "/admin/api/companies/acme/suspend")

    response = as_(client, google, ana)

    assert response.headers["location"] == f"{WEB}/"
    statuses = {o["slug"]: o["status"] for o in client.get("/api/orgs").json()}
    assert statuses == {"acme": "suspended", "zeta": "active"}
    assert client.get("/api/orgs/acme/members").status_code == 404


def test_a_super_admin_in_a_suspended_company_still_signs_in(
    client: TestClient,
    google: FakeGoogle,
    control: Database,
    tenants: Tenants,
    admin: User,
    acme: Org,
) -> None:
    orgs.add_member(control, tenants, org=acme, user=admin, role="owner", actor_id=None)
    as_(client, google, admin)
    call(client, "POST", "/admin/api/companies/acme/suspend")

    assert as_(client, google, admin).headers["location"] == f"{WEB}/"


def test_suspending_twice_is_a_conflict(
    client: TestClient, google: FakeGoogle, admin: User, acme: Org
) -> None:
    as_(client, google, admin)
    call(client, "POST", "/admin/api/companies/acme/suspend")

    again = call(client, "POST", "/admin/api/companies/acme/suspend")

    assert again.status_code == 409
    assert again.json()["error"]["code"] == "COMPANY_SUSPENDED"


def test_suspend_closes_the_company_file(
    client: TestClient, google: FakeGoogle, admin: User, ana: User, tenants: Tenants
) -> None:
    as_(client, google, admin)
    assert tenants.is_open("acme")  # opened when Ana was added

    call(client, "POST", "/admin/api/companies/acme/suspend")

    assert not tenants.is_open("acme")


# --- resume --------------------------------------------------------------------------


def test_resume_gives_the_members_their_company_back(
    client: TestClient, google: FakeGoogle, control: Database, admin: User, ana: User
) -> None:
    as_(client, google, admin)
    call(client, "POST", "/admin/api/companies/acme/suspend")

    resumed = call(client, "POST", "/admin/api/companies/acme/resume")

    assert resumed.status_code == 200
    assert resumed.json()["status"] == "active"
    assert as_(client, google, ana).headers["location"] == f"{WEB}/"
    assert client.get("/api/orgs/acme/members").status_code == 200
    assert [r["target"] for r in audit(control, "company.resumed")] == ["acme"]


def test_resuming_an_active_company_is_a_conflict(
    client: TestClient, google: FakeGoogle, admin: User, acme: Org
) -> None:
    as_(client, google, admin)

    again = call(client, "POST", "/admin/api/companies/acme/resume")

    assert again.status_code == 409
    assert again.json()["error"]["code"] == "COMPANY_ACTIVE"


# --- delete to trash ------------------------------------------------------------------


def test_delete_moves_the_folder_to_trash_and_ends_access(
    client: TestClient,
    google: FakeGoogle,
    control: Database,
    tenants: Tenants,
    settings: Any,
    admin: User,
    acme: Org,
    ana: User,
) -> None:
    invites.create_invite(control, org=acme, email="bo@example.com", role="member", actor_id=None)
    folder = tenants.folder("acme")
    as_(client, google, admin)

    deleted = call(client, "DELETE", "/admin/api/companies/acme", {"confirm": "acme"})

    # then the folder sits in trash/acme-<timestamp>/ with its database, and nothing is left behind
    assert deleted.status_code == 204
    assert not folder.exists()
    trash = Path(settings.data_dir) / "trash"
    [moved] = list(trash.iterdir())
    assert re.fullmatch(r"acme-\d{8}T\d{6}Z", moved.name)
    assert (moved / "tazko.db").is_file()
    assert not tenants.is_open("acme")
    # the row stays as deleted, so the console and members no longer see it
    assert status(control) == "deleted"
    assert control.read(lambda c: c.execute("SELECT deleted_at FROM orgs").fetchone()[0])
    assert client.get("/admin/api/companies").json() == []
    assert client.get("/admin/api/invites").json() == []
    assert [(r["target"], json.loads(r["detail"])) for r in audit(control, "company.deleted")] == [
        ("acme", {"trash": moved.name})
    ]
    as_(client, google, ana)
    assert client.get("/api/orgs").json() == []
    assert client.get("/api/orgs/acme/members").status_code == 404


def test_delete_needs_the_short_name_typed(
    client: TestClient,
    google: FakeGoogle,
    control: Database,
    tenants: Tenants,
    admin: User,
    acme: Org,
) -> None:
    as_(client, google, admin)

    assert call(client, "DELETE", "/admin/api/companies/acme").status_code == 400  # no body
    for body in ({"confirm": "ACME"}, {"confirm": "zeta"}, {}):
        refused = call(client, "DELETE", "/admin/api/companies/acme", body)
        assert refused.status_code == 422, body

    assert status(control) == "active"
    assert tenants.exists("acme")


def test_a_deleted_companys_short_name_stays_taken(
    client: TestClient, google: FakeGoogle, admin: User, acme: Org
) -> None:
    # the row keeps the slug so the folder in trash can be restored by hand (D35)
    as_(client, google, admin)
    call(client, "DELETE", "/admin/api/companies/acme", {"confirm": "acme"})

    again = call(client, "POST", "/admin/api/companies", {"slug": "acme", "name": "Acme 2"})

    assert again.status_code == 409
    assert again.json()["error"]["code"] == "SLUG_TAKEN"


def test_deleting_a_deleted_company_is_404(
    client: TestClient, google: FakeGoogle, admin: User, acme: Org
) -> None:
    as_(client, google, admin)
    call(client, "DELETE", "/admin/api/companies/acme", {"confirm": "acme"})

    assert (
        call(client, "DELETE", "/admin/api/companies/acme", {"confirm": "acme"}).status_code == 404
    )
    assert call(client, "POST", "/admin/api/companies/acme/resume").status_code == 404


def test_a_suspended_company_can_be_deleted(
    client: TestClient, google: FakeGoogle, control: Database, admin: User, acme: Org
) -> None:
    as_(client, google, admin)
    call(client, "POST", "/admin/api/companies/acme/suspend")

    assert (
        call(client, "DELETE", "/admin/api/companies/acme", {"confirm": "acme"}).status_code == 204
    )
    assert status(control) == "deleted"


def test_a_refusal_cookie_from_the_previous_release_reads_as_not_invited() -> None:
    from tazko.core.signing import sign
    from tazko.modules.auth import service as auth

    secret = b"s" * 32
    old = sign({"email": "jo@example.com"}, secret, purpose="refused", max_age=60)

    assert auth.refused_email(old, secret) == ("jo@example.com", "not_invited")


def test_a_trashed_company_cannot_be_opened_again(
    control: Database, tenants: Tenants, acme: Org
) -> None:
    tenants.get("acme")
    tenants.trash("acme", "20261120T000000Z")

    assert not tenants.is_open("acme")
    with pytest.raises(FileNotFoundError):
        tenants.get("acme")


def test_a_failed_delete_puts_the_folder_back_and_keeps_the_company(
    client: TestClient,
    google: FakeGoogle,
    control: Database,
    tenants: Tenants,
    admin: User,
    acme: Org,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # given the control.db write fails after the folder has moved
    as_(client, google, admin)
    real = audit_service.record

    def failing(conn: Any, action: str, **kwargs: Any) -> None:
        if action == "company.deleted":
            raise RuntimeError("disk full")
        real(conn, action, **kwargs)

    monkeypatch.setattr(audit_service, "record", failing)

    with pytest.raises(RuntimeError):
        Console(control, tenants, admin.id).delete("acme", confirm="acme")

    # then the folder is back and the company still works
    assert tenants.exists("acme")
    assert status(control) == "active"
    assert not (Path(tenants.root.parent) / "trash").exists() or not any(
        (Path(tenants.root.parent) / "trash").iterdir()
    )


def test_a_company_whose_folder_is_gone_can_still_be_deleted(
    client: TestClient,
    google: FakeGoogle,
    control: Database,
    tenants: Tenants,
    admin: User,
    acme: Org,
) -> None:
    tenants.evict("acme")
    shutil.rmtree(tenants.folder("acme"))
    as_(client, google, admin)

    assert (
        call(client, "DELETE", "/admin/api/companies/acme", {"confirm": "acme"}).status_code == 204
    )
    assert status(control) == "deleted"
    assert [json.loads(r["detail"]) for r in audit(control, "company.deleted")] == [{"trash": None}]
