"""Super admin console, second part (M1-06): People, Audit log, Server page and
Workspace domains. Through HTTP with real sessions."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from tazko import __version__
from tazko.core.config import load_settings
from tazko.db import Database
from tazko.db.tenant import Tenants
from tazko.modules.admin import service as admin_service
from tazko.modules.admin.schemas import ServerOut
from tazko.modules.invites import service as invites
from tazko.modules.orgs import service as orgs
from tazko.modules.orgs.service import Org
from tazko.modules.users import service as users
from tazko.modules.users.service import User
from tests.integration.oidc import SAME_ORIGIN, FakeGoogle, audit, session_count, sign_in


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


def as_(client: TestClient, google: FakeGoogle, user: User, **claims: Any) -> None:
    client.cookies.clear()
    sign_in(
        client,
        google,
        sub=f"sub-{user.id}",
        email=user.email,
        name=user.name or user.email.split("@")[0].title(),
        **claims,
    )


def call(client: TestClient, method: str, path: str, body: Any = None) -> Any:
    return client.request(method, path, json=body, headers=SAME_ORIGIN)


# --- people ----------------------------------------------------------------------------


def test_people_lists_everyone_with_companies_and_flags(
    client: TestClient,
    google: FakeGoogle,
    control: Database,
    tenants: Tenants,
    admin: User,
    acme: Org,
) -> None:
    beta = orgs.create_company(control, tenants, slug="beta", name="Beta", actor_id=None)
    ana = users.get_or_create(control, "ana@corp.example", name="Ana")
    orgs.add_member(control, tenants, org=acme, user=ana, role="owner", actor_id=None)
    orgs.add_member(control, tenants, org=beta, user=ana, role="member", actor_id=None)
    as_(client, google, ana, hd="corp.example")
    as_(client, google, admin)

    body = client.get("/admin/api/people").json()

    rows = {r["email"]: r for r in body["items"]}
    assert set(rows) == {"admin@example.com", "ana@corp.example"}
    assert rows["ana@corp.example"]["companies"] == [
        {"slug": "acme", "name": "Acme", "role": "owner"},
        {"slug": "beta", "name": "Beta", "role": "member"},
    ]
    assert rows["ana@corp.example"]["account"] == "workspace"
    assert rows["ana@corp.example"]["active"] is True
    assert rows["ana@corp.example"]["is_super_admin"] is False
    assert rows["admin@example.com"]["is_super_admin"] is True
    assert body["next"] is None


def test_people_search_matches_name_or_email(
    client: TestClient, google: FakeGoogle, control: Database, admin: User
) -> None:
    users.get_or_create(control, "ana@example.com", name="Ana Reyes")
    users.get_or_create(control, "bo@example.com", name="Bo")
    as_(client, google, admin)

    assert [r["email"] for r in client.get("/admin/api/people?q=reyes").json()["items"]] == [
        "ana@example.com"
    ]
    assert [r["email"] for r in client.get("/admin/api/people?q=BO@").json()["items"]] == [
        "bo@example.com"
    ]
    users.get_or_create(control, "anh@example.com", name="Trần Ánh")
    assert [r["email"] for r in client.get("/admin/api/people?q=Ánh").json()["items"]] == [
        "anh@example.com"
    ]
    # LIKE wildcards are matched as plain characters.
    assert client.get("/admin/api/people?q=%25").json()["items"] == []


def test_people_come_in_pages(
    client: TestClient, google: FakeGoogle, control: Database, admin: User
) -> None:
    for n in range(5):
        users.get_or_create(control, f"p{n}@example.com")
    as_(client, google, admin)

    first = client.get("/admin/api/people?limit=4").json()
    second = client.get(f"/admin/api/people?limit=4&after={first['next']}").json()

    assert len(first["items"]) == 4
    assert len(second["items"]) == 2  # 6 people in all, with the admin
    assert second["next"] is None
    assert {r["id"] for r in first["items"]}.isdisjoint({r["id"] for r in second["items"]})


@pytest.mark.parametrize("query", ["limit=0", "limit=201", "after=-1"])
def test_people_paging_is_bounded(
    client: TestClient, google: FakeGoogle, admin: User, query: str
) -> None:
    as_(client, google, admin)

    assert client.get(f"/admin/api/people?{query}").status_code == 422


def test_disabling_someone_signs_them_out_and_is_audited(
    client: TestClient, google: FakeGoogle, control: Database, admin: User
) -> None:
    bo = users.get_or_create(control, "bo@example.com", name="Bo")
    as_(client, google, bo)
    as_(client, google, admin)
    assert session_count(control) == 2

    response = call(client, "PATCH", f"/admin/api/people/{bo.id}", {"active": False})

    assert response.status_code == 200
    assert response.json()["active"] is False
    assert session_count(control) == 1  # only the admin's
    assert [(r["target"], r["actor_id"]) for r in audit(control, "person.disabled")] == [
        ("bo@example.com", admin.id)
    ]


def test_enabling_someone_again_lets_them_sign_in(
    client: TestClient, google: FakeGoogle, control: Database, admin: User
) -> None:
    bo = users.get_or_create(control, "bo@example.com", name="Bo")
    as_(client, google, admin)
    call(client, "PATCH", f"/admin/api/people/{bo.id}", {"active": False})

    assert (
        call(client, "PATCH", f"/admin/api/people/{bo.id}", {"active": True}).json()["active"]
        is True
    )
    assert [r["target"] for r in audit(control, "person.enabled")] == ["bo@example.com"]
    as_(client, google, bo)
    assert client.get("/api/me").status_code == 200


def test_granting_and_revoking_super_admin_is_audited(
    client: TestClient, google: FakeGoogle, control: Database, admin: User
) -> None:
    bo = users.get_or_create(control, "bo@example.com", name="Bo")
    as_(client, google, admin)

    granted = call(client, "PATCH", f"/admin/api/people/{bo.id}", {"is_super_admin": True})
    revoked = call(client, "PATCH", f"/admin/api/people/{bo.id}", {"is_super_admin": False})

    assert (granted.json()["is_super_admin"], revoked.json()["is_super_admin"]) == (True, False)
    assert [r["actor_id"] for r in audit(control, "super_admin.granted")][-1] == admin.id
    assert [r["target"] for r in audit(control, "super_admin.revoked")] == ["bo@example.com"]


@pytest.mark.parametrize("body", [{"active": False}, {"is_super_admin": False}])
def test_a_super_admin_cannot_change_themselves(
    client: TestClient, google: FakeGoogle, admin: User, body: dict[str, bool]
) -> None:
    # So the console always keeps at least one super admin who can sign in.
    as_(client, google, admin)

    response = call(client, "PATCH", f"/admin/api/people/{admin.id}", body)

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "SELF_CHANGE"


def test_changing_an_unknown_person_is_404(
    client: TestClient, google: FakeGoogle, admin: User
) -> None:
    as_(client, google, admin)

    assert call(client, "PATCH", "/admin/api/people/9999", {"active": False}).status_code == 404


def test_an_empty_change_is_422(
    client: TestClient, google: FakeGoogle, control: Database, admin: User
) -> None:
    bo = users.get_or_create(control, "bo@example.com")
    as_(client, google, admin)

    assert call(client, "PATCH", f"/admin/api/people/{bo.id}", {}).status_code == 422


def test_revoking_super_admin_takes_effect_at_once(
    client: TestClient, google: FakeGoogle, control: Database, admin: User
) -> None:
    bo, _ = users.grant_super_admin(control, "bo@example.com", actor_id=None)
    as_(client, google, bo)
    assert client.get("/admin/api/companies").status_code == 200

    users.set_flags(control, user_id=bo.id, is_super_admin=False, actor_id=admin.id, ip=None)

    assert client.get("/admin/api/companies").status_code == 403


# --- audit log ---------------------------------------------------------------------


def test_audit_log_lists_newest_first_with_names(
    client: TestClient, google: FakeGoogle, control: Database, admin: User, acme: Org
) -> None:
    as_(client, google, admin)
    invites.create_invite(
        control, org=acme, email="di@example.com", role="member", actor_id=admin.id
    )

    items = client.get("/admin/api/audit").json()["items"]

    newest = items[0]
    assert newest["action"] == "invite.created"
    assert newest["actor"] == {"id": admin.id, "name": "Admin", "email": "admin@example.com"}
    assert newest["company"] == {"slug": "acme", "name": "Acme"}
    assert newest["target"] == "di@example.com"
    assert newest["detail"] == {"role": "member"}
    # Older rows: the admin's first sign-in linked their account; the company
    # and the flag came before it.
    assert [i["action"] for i in items[1:]] == [
        "account.linked",
        "company.created",
        "super_admin.granted",
    ]


def test_audit_log_filters_by_kind(
    client: TestClient, google: FakeGoogle, control: Database, admin: User, acme: Org
) -> None:
    as_(client, google, admin)
    sign_in(client, google, sub="sub-nobody", email="nobody@example.com")  # refused
    as_(client, google, admin)

    refused = client.get("/admin/api/audit?kind=signin").json()["items"]
    companies = client.get("/admin/api/audit?kind=company").json()["items"]

    assert [i["action"] for i in refused] == ["signin.refused"]
    assert refused[0]["actor"] is None
    assert [i["action"] for i in companies] == ["company.created"]
    assert client.get("/admin/api/audit?kind=secrets").status_code == 422


def test_audit_log_comes_in_pages(
    client: TestClient, google: FakeGoogle, control: Database, tenants: Tenants, admin: User
) -> None:
    for n in range(4):
        orgs.create_company(control, tenants, slug=f"c{n}", name=f"C{n}", actor_id=None)
    as_(client, google, admin)

    first = client.get("/admin/api/audit?kind=company&limit=3").json()
    second = client.get(f"/admin/api/audit?kind=company&limit=3&before={first['next']}").json()

    assert [i["target"] for i in first["items"]] == ["c3", "c2", "c1"]
    assert [i["target"] for i in second["items"]] == ["c0"]
    assert second["next"] is None


# --- server page ----------------------------------------------------------------------


def test_server_page_shows_version_uptime_size_and_email(
    client: TestClient, google: FakeGoogle, admin: User
) -> None:
    as_(client, google, admin)

    body = client.get("/admin/api/server").json()

    assert body["version"] == __version__
    assert body["uptime_seconds"] >= 0
    assert body["data_bytes"] > 0  # control.db at least
    assert body["last_backup"] is None  # backups arrive with M1-08
    assert body["email"] == {"enabled": False, "host": None, "port": None, "sender": None}
    assert body["public_url"] == "https://testserver"


def test_server_page_never_shows_the_smtp_login(tmp_path: Path) -> None:
    # With email on: host, port and sender only.
    settings = load_settings(
        data_dir=tmp_path,
        smtp_host="smtp.example.com",
        smtp_user="mailer",
        smtp_password="s3cret-pass",  # a made-up password the page must not show
        mail_from="Tazko <no-reply@example.com>",
    )
    control = Database(tmp_path / "control.db", "control")
    try:
        admin_user, _ = users.grant_super_admin(control, "admin@example.com", actor_id=None)
        info = admin_service.server_info(control, settings, actor_id=admin_user.id, started=0.0)
    finally:
        control.close()

    body = ServerOut.from_info(info).model_dump_json()

    assert '"enabled":true' in body
    assert '"host":"smtp.example.com"' in body
    assert "s3cret-pass" not in body
    assert "mailer" not in body


# --- workspace domains (D26) -----------------------------------------------------------


def test_super_admin_lists_and_removes_a_workspace_domain(
    client: TestClient, google: FakeGoogle, control: Database, admin: User
) -> None:
    control.write(
        lambda c: c.execute(
            "INSERT INTO workspace_domains (domain, first_seen_at) VALUES ('corp.example', '2026-01-01T00:00:00.000Z')"
        )
    )
    as_(client, google, admin)

    assert client.get("/admin/api/workspace-domains").json() == [
        {"domain": "corp.example", "first_seen_at": "2026-01-01T00:00:00.000Z"}
    ]
    assert call(client, "DELETE", "/admin/api/workspace-domains/CORP.example").status_code == 204
    assert client.get("/admin/api/workspace-domains").json() == []
    removed = audit(control, "workspace_domain.removed")
    assert [(r["target"], r["detail"]) for r in removed] == [
        ("corp.example", '{"first_seen_at":"2026-01-01T00:00:00.000Z"}')
    ]
    assert call(client, "DELETE", "/admin/api/workspace-domains/corp.example").status_code == 404


def test_after_removing_a_domain_a_personal_account_can_use_its_invite(
    client: TestClient, google: FakeGoogle, control: Database, admin: User, acme: Org
) -> None:
    control.write(
        lambda c: c.execute(
            "INSERT INTO workspace_domains (domain, first_seen_at) VALUES ('corp.example', '2026-01-01T00:00:00.000Z')"
        )
    )
    invites.create_invite(control, org=acme, email="bo@corp.example", role="member", actor_id=None)
    as_(client, google, admin)
    call(client, "DELETE", "/admin/api/workspace-domains/corp.example")
    client.cookies.clear()

    response = sign_in(client, google, sub="sub-bo", email="bo@corp.example", name="Bo")

    assert response.headers["location"].endswith("/")  # signed in, not refused
