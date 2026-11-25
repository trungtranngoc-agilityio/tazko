"""Super admin console API under /admin/api: the gate, companies,
company detail and invites across companies. Through HTTP with real sessions."""

from __future__ import annotations

from typing import Any

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from tazko.db import Database
from tazko.db.tenant import Tenants
from tazko.modules.invites import service as invites
from tazko.modules.orgs import service as orgs
from tazko.modules.orgs.service import Org
from tazko.modules.users import service as users
from tazko.modules.users.service import User
from tests.integration.oidc import SAME_ORIGIN, FakeGoogle, audit, sign_in
from tests.integration.test_origin import walk


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


def as_(client: TestClient, google: FakeGoogle, user: User) -> None:
    client.cookies.clear()
    sign_in(client, google, sub=f"sub-{user.id}", email=user.email, name=user.name or "Someone")


def call(client: TestClient, method: str, path: str, body: Any = None) -> Any:
    return client.request(method, path, json=body, headers=SAME_ORIGIN)


def admin_routes(app: FastAPI) -> list[tuple[str, str]]:
    return [
        (
            method,
            path.replace("{slug}", "acme")
            .replace("{user_id}", "1")
            .replace("{invite_id}", "1")
            .replace("{domain}", "corp.example"),
        )
        for path, route in walk(app.routes)
        if path.startswith("/admin/api")
        for method in sorted(route.methods or set())
    ]


# --- the gate -----------------------------------------------------------------------


def test_the_console_has_routes_to_guard(app: FastAPI) -> None:
    assert ("GET", "/admin/api/companies") in admin_routes(app)


def test_every_console_route_needs_a_session(app: FastAPI, client: TestClient, acme: Org) -> None:
    for method, path in admin_routes(app):
        assert call(client, method, path).status_code == 401, (method, path)


def test_every_console_route_refuses_a_person_who_is_not_super_admin(
    app: FastAPI,
    client: TestClient,
    google: FakeGoogle,
    control: Database,
    tenants: Tenants,
    acme: Org,
) -> None:
    # Even an owner of the company named in the path.
    owner = users.get_or_create(control, "owner@example.com", name="Owner")
    orgs.add_member(control, tenants, org=acme, user=owner, role="owner", actor_id=None)
    as_(client, google, owner)

    for method, path in admin_routes(app):
        response = call(client, method, path)
        assert response.status_code == 403, (method, path)
        assert response.json()["error"]["code"] == "FORBIDDEN"


def test_a_super_admin_who_is_disabled_is_signed_out(
    client: TestClient, google: FakeGoogle, control: Database, admin: User
) -> None:
    as_(client, google, admin)
    control.write(lambda c: c.execute("UPDATE users SET disabled_at = '2026-01-01T00:00:00.000Z'"))

    assert client.get("/admin/api/companies").status_code == 401


# --- companies ---------------------------------------------------------------------


def test_companies_list_shows_counts_storage_and_activity(
    client: TestClient,
    google: FakeGoogle,
    control: Database,
    tenants: Tenants,
    admin: User,
    acme: Org,
) -> None:
    ana = users.get_or_create(control, "ana@example.com", name="Ana")
    orgs.add_member(control, tenants, org=acme, user=ana, role="owner", actor_id=None)
    orgs.create_company(control, tenants, slug="beta", name="Beta", actor_id=None)
    as_(client, google, admin)

    response = client.get("/admin/api/companies")

    assert response.status_code == 200
    rows = response.json()
    assert [(r["slug"], r["name"], r["status"], r["members"]) for r in rows] == [
        ("acme", "Acme", "active", 1),
        ("beta", "Beta", "active", 0),
    ]
    assert rows[0]["storage_bytes"] > 0  # its database file
    assert rows[0]["storage_limit_bytes"] is None
    # Each company's newest audit row: member.added for acme, company.created for beta.
    newest = dict(
        control.read(
            lambda c: c.execute(
                "SELECT o.slug, max(a.at) FROM audit_log a JOIN orgs o ON o.id = a.org_id GROUP BY o.slug"
            ).fetchall()
        )
    )
    assert rows[0]["last_activity_at"] == newest["acme"]
    assert rows[1]["last_activity_at"] == newest["beta"]


def test_companies_page_opens_no_company_files(
    client: TestClient, google: FakeGoogle, control: Database, tenants: Tenants, admin: User
) -> None:
    for slug in ("one", "two"):
        orgs.create_company(control, tenants, slug=slug, name=slug.title(), actor_id=None)
        tenants.evict(slug)
    as_(client, google, admin)

    client.get("/admin/api/companies")
    client.get("/admin/api/companies/one/members")

    assert not tenants.is_open("one")
    assert not tenants.is_open("two")


def test_deleted_companies_are_left_out(
    client: TestClient, google: FakeGoogle, control: Database, admin: User, acme: Org
) -> None:
    invites.create_invite(control, org=acme, email="di@example.com", role="member", actor_id=None)
    control.write(lambda c: c.execute("UPDATE orgs SET status = 'deleted'"))
    as_(client, google, admin)

    assert client.get("/admin/api/companies").json() == []
    assert client.get("/admin/api/companies/acme").status_code == 404
    assert client.get("/admin/api/companies/acme/members").status_code == 404
    assert client.get("/admin/api/invites").json() == []


def test_suspended_companies_are_listed_as_suspended(
    client: TestClient, google: FakeGoogle, control: Database, admin: User, acme: Org
) -> None:
    control.write(lambda c: c.execute("UPDATE orgs SET status = 'suspended'"))
    as_(client, google, admin)

    assert [r["status"] for r in client.get("/admin/api/companies").json()] == ["suspended"]


def test_company_row_without_its_file_is_a_clear_error(
    client: TestClient,
    google: FakeGoogle,
    control: Database,
    tenants: Tenants,
    admin: User,
    acme: Org,
) -> None:
    ana = users.get_or_create(control, "ana@example.com", name="Ana")
    bo = users.get_or_create(control, "bo@example.com", name="Bo")
    orgs.add_member(control, tenants, org=acme, user=ana, role="owner", actor_id=None)
    orgs.add_member(control, tenants, org=acme, user=bo, role="member", actor_id=None)
    tenants.evict("acme")
    for path in sorted(tenants.folder("acme").rglob("*"), reverse=True):
        path.unlink() if path.is_file() else path.rmdir()
    as_(client, google, admin)

    assert client.get("/admin/api/companies").status_code == 200  # listing needs no file
    assert client.get("/admin/api/companies/acme/members").status_code == 200
    response = call(
        client, "PATCH", f"/admin/api/companies/acme/members/{bo.id}", {"role": "owner"}
    )
    assert response.status_code == 200  # the change stands; the missing file is logged


def test_super_admin_creates_a_company(
    client: TestClient, google: FakeGoogle, control: Database, tenants: Tenants, admin: User
) -> None:
    as_(client, google, admin)

    response = call(
        client, "POST", "/admin/api/companies", {"slug": "harbor", "name": "Harbor Studio"}
    )

    assert response.status_code == 201
    assert response.headers["location"] == "/admin/api/companies/harbor"
    assert response.json()["slug"] == "harbor"
    assert tenants.exists("harbor")
    assert [(r["target"], r["actor_id"]) for r in audit(control, "company.created")] == [
        ("harbor", admin.id)
    ]


def test_taken_slug_is_409(client: TestClient, google: FakeGoogle, admin: User, acme: Org) -> None:
    as_(client, google, admin)

    response = call(client, "POST", "/admin/api/companies", {"slug": "acme", "name": "Again"})

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "SLUG_TAKEN"


def test_bad_slug_is_422(client: TestClient, google: FakeGoogle, admin: User) -> None:
    as_(client, google, admin)

    response = call(client, "POST", "/admin/api/companies", {"slug": "Bad Slug!", "name": "X"})

    assert response.status_code == 422
    assert response.json()["error"]["details"][0]["field"] == "slug"


def test_one_company_is_shown_with_its_status(
    client: TestClient, google: FakeGoogle, admin: User, acme: Org
) -> None:
    as_(client, google, admin)

    body = client.get("/admin/api/companies/acme").json()

    assert (body["slug"], body["name"], body["status"], body["members"]) == (
        "acme",
        "Acme",
        "active",
        0,
    )


def test_unknown_company_is_404(client: TestClient, google: FakeGoogle, admin: User) -> None:
    as_(client, google, admin)

    assert client.get("/admin/api/companies/nope").status_code == 404
    assert client.get("/admin/api/companies/nope/members").status_code == 404


# --- company detail: members and invites --------------------------------------------


def test_super_admin_invites_the_first_owner_and_manages_members(
    client: TestClient,
    google: FakeGoogle,
    control: Database,
    tenants: Tenants,
    admin: User,
    acme: Org,
) -> None:
    # The super admin is not a member of the company and still manages it.
    as_(client, google, admin)

    made = call(
        client,
        "POST",
        "/admin/api/companies/acme/invites",
        {"email": "ana@example.com", "role": "owner"},
    )
    assert made.status_code == 201
    assert made.headers["location"] == f"/admin/api/companies/acme/invites/{made.json()['id']}"
    assert [r["email"] for r in client.get("/admin/api/companies/acme/invites").json()] == [
        "ana@example.com"
    ]

    ana = users.get_or_create(control, "ana@example.com", name="Ana")
    bo = users.get_or_create(control, "bo@example.com", name="Bo")
    orgs.add_member(control, tenants, org=acme, user=ana, role="owner", actor_id=None)
    orgs.add_member(control, tenants, org=acme, user=bo, role="member", actor_id=None)

    assert [r["email"] for r in client.get("/admin/api/companies/acme/members").json()] == [
        "ana@example.com",
        "bo@example.com",
    ]
    changed = call(client, "PATCH", f"/admin/api/companies/acme/members/{bo.id}", {"role": "owner"})
    assert changed.json()["role"] == "owner"
    assert call(client, "DELETE", f"/admin/api/companies/acme/members/{bo.id}").status_code == 204
    assert (
        call(client, "DELETE", f"/admin/api/companies/acme/members/{ana.id}").json()["error"][
            "code"
        ]
        == "LAST_OWNER"
    )
    assert [r["actor_id"] for r in audit(control, "member.removed")] == [admin.id]


def test_super_admin_revokes_a_company_invite(
    client: TestClient, google: FakeGoogle, control: Database, admin: User, acme: Org
) -> None:
    invite = invites.create_invite(
        control, org=acme, email="di@example.com", role="member", actor_id=None
    )
    as_(client, google, admin)

    assert (
        call(client, "DELETE", f"/admin/api/companies/acme/invites/{invite.id}").status_code == 204
    )
    assert client.get("/admin/api/companies/acme/invites").json() == []


def test_super_admin_reads_no_company_data_beyond_people(
    client: TestClient, google: FakeGoogle, admin: User, acme: Org
) -> None:
    # Boards stay hidden from super admins: the company routes need membership.
    as_(client, google, admin)

    assert client.get("/api/orgs/acme/members").status_code == 404


# --- invites across companies --------------------------------------------------------


def test_invites_page_lists_pending_invites_of_every_company(
    client: TestClient,
    google: FakeGoogle,
    control: Database,
    tenants: Tenants,
    admin: User,
    acme: Org,
) -> None:
    beta = orgs.create_company(control, tenants, slug="beta", name="Beta", actor_id=None)
    invites.create_invite(
        control, org=acme, email="di@example.com", role="member", actor_id=admin.id
    )
    invites.create_invite(control, org=beta, email="ed@gmail.com", role="owner", actor_id=None)
    gone = invites.create_invite(
        control, org=beta, email="fy@example.com", role="member", actor_id=None
    )
    invites.revoke_invite(control, org=beta, invite_id=gone.id, actor_id=None)
    as_(client, google, admin)

    rows = client.get("/admin/api/invites").json()

    assert [
        (r["email"], r["company"]["slug"], r["company"]["name"], r["account"]) for r in rows
    ] == [
        ("ed@gmail.com", "beta", "Beta", "personal"),  # newest first
        ("di@example.com", "acme", "Acme", None),
    ]
    assert rows[1]["invited_by"] == "Someone"  # the super admin's name from Google
    assert rows[0]["invited_by"] is None  # made from the command line


def test_invites_page_revokes_any_companys_invite(
    client: TestClient, google: FakeGoogle, control: Database, admin: User, acme: Org
) -> None:
    invite = invites.create_invite(
        control, org=acme, email="di@example.com", role="member", actor_id=None
    )
    as_(client, google, admin)

    assert call(client, "DELETE", f"/admin/api/invites/{invite.id}").status_code == 204
    assert (
        call(client, "DELETE", f"/admin/api/invites/{invite.id}").json()["error"]["code"]
        == "INVITE_REVOKED"
    )
    assert call(client, "DELETE", "/admin/api/invites/9999").status_code == 404
    assert [r["actor_id"] for r in audit(control, "invite.revoked")] == [admin.id]
