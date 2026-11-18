"""Company settings for owners: members, roles and invites, and the company
switcher (M1-06). Every route goes through HTTP with a real session."""

from __future__ import annotations

from typing import Any

import pytest
from fastapi.testclient import TestClient

from tazko.core.errors import Conflict, Forbidden
from tazko.db import Database
from tazko.db.tenant import Tenants
from tazko.modules.invites import service as invites
from tazko.modules.orgs import repository as orgs_repo
from tazko.modules.orgs import service as orgs
from tazko.modules.orgs.service import Org
from tazko.modules.users import service as users
from tazko.modules.users.service import User
from tests.integration.oidc import SAME_ORIGIN, FakeGoogle, audit, sign_in


@pytest.fixture
def tenants(client: TestClient) -> Tenants:
    found: Tenants = client.app.state.tenants  # type: ignore[attr-defined]  # TestClient.app is typed as ASGIApp
    return found


@pytest.fixture
def acme(control: Database, tenants: Tenants) -> Org:
    return orgs.create_company(control, tenants, slug="acme", name="Acme", actor_id=None)


def person(control: Database, tenants: Tenants, org: Org, name: str, role: str) -> User:
    user = users.get_or_create(control, f"{name}@example.com", name=name.title())
    orgs.add_member(control, tenants, org=org, user=user, role=role, actor_id=None)  # type: ignore[arg-type]  # role is owner or member here
    return user


def as_(client: TestClient, google: FakeGoogle, user: User) -> None:
    """Sign in as this person (a fresh session)."""
    client.cookies.clear()
    sign_in(client, google, sub=f"sub-{user.id}", email=user.email, name=user.name)


def write(client: TestClient, method: str, path: str, body: Any = None) -> Any:
    return client.request(method, path, json=body, headers=SAME_ORIGIN)


@pytest.fixture
def ana(control: Database, tenants: Tenants, acme: Org) -> User:
    return person(control, tenants, acme, "ana", "owner")


@pytest.fixture
def bo(control: Database, tenants: Tenants, acme: Org) -> User:
    return person(control, tenants, acme, "bo", "member")


# --- company switcher ----------------------------------------------------------------


def test_switcher_lists_only_the_persons_companies(
    client: TestClient, google: FakeGoogle, control: Database, tenants: Tenants, ana: User
) -> None:
    zeta = orgs.create_company(control, tenants, slug="zeta", name="Zeta", actor_id=None)
    orgs.create_company(control, tenants, slug="other", name="Other", actor_id=None)
    orgs.add_member(control, tenants, org=zeta, user=ana, role="member", actor_id=None)
    as_(client, google, ana)

    response = client.get("/api/orgs")

    assert response.status_code == 200
    assert response.json() == [
        {"slug": "acme", "name": "Acme", "role": "owner", "status": "active"},
        {"slug": "zeta", "name": "Zeta", "role": "member", "status": "active"},
    ]


def test_switcher_needs_a_session(client: TestClient) -> None:
    assert client.get("/api/orgs").status_code == 401


ROUTES = [
    ("GET", "/api/orgs/acme/members", None),
    ("PATCH", "/api/orgs/acme/members/1", {"role": "member"}),
    ("DELETE", "/api/orgs/acme/members/1", None),
    ("GET", "/api/orgs/acme/invites", None),
    ("POST", "/api/orgs/acme/invites", {"email": "cy@example.com", "role": "member"}),
    ("DELETE", "/api/orgs/acme/invites/1", None),
]


# --- members -----------------------------------------------------------------------


def test_owner_sees_the_members(
    client: TestClient, google: FakeGoogle, ana: User, bo: User
) -> None:
    as_(client, google, ana)

    response = client.get("/api/orgs/acme/members")

    assert response.status_code == 200
    rows = response.json()
    assert [(r["email"], r["role"]) for r in rows] == [
        ("ana@example.com", "owner"),
        ("bo@example.com", "member"),
    ]
    assert rows[0]["account"] == "personal"  # signed in with a Google account that has no hd
    assert rows[0]["last_seen_at"] is not None
    assert rows[1]["account"] is None  # never signed in
    assert rows[1]["last_seen_at"] is None
    assert set(rows[0]) == {
        "user_id",
        "name",
        "email",
        "avatar_url",
        "account",
        "role",
        "last_seen_at",
    }


@pytest.mark.parametrize(("method", "path", "body"), ROUTES)
def test_a_member_cannot_manage_the_company(
    client: TestClient,
    google: FakeGoogle,
    ana: User,
    bo: User,
    method: str,
    path: str,
    body: Any,
) -> None:
    as_(client, google, bo)

    response = write(client, method, path, body)

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "FORBIDDEN"


@pytest.mark.parametrize(("method", "path", "body"), ROUTES)
def test_another_companys_people_get_404(
    client: TestClient,
    google: FakeGoogle,
    control: Database,
    tenants: Tenants,
    ana: User,
    method: str,
    path: str,
    body: Any,
) -> None:
    beta = orgs.create_company(control, tenants, slug="beta", name="Beta", actor_id=None)
    cy = person(control, tenants, beta, "cy", "owner")
    as_(client, google, cy)

    assert write(client, method, path, body).status_code == 404


@pytest.mark.parametrize(
    "path", ["/api/orgs/acme/members/99999999999999999999", "/api/orgs/acme/members/0"]
)
def test_an_impossible_id_is_422_not_a_crash(
    client: TestClient, google: FakeGoogle, ana: User, path: str
) -> None:
    as_(client, google, ana)

    assert write(client, "DELETE", path).status_code == 422


def test_a_disabled_owner_does_not_count_as_an_owner(
    client: TestClient,
    google: FakeGoogle,
    control: Database,
    tenants: Tenants,
    acme: Org,
    ana: User,
) -> None:
    dee = person(control, tenants, acme, "dee", "owner")
    control.write(
        lambda c: c.execute(
            "UPDATE users SET disabled_at = '2026-01-01T00:00:00.000Z' WHERE id = ?", (dee.id,)
        )
    )
    as_(client, google, ana)

    assert (
        write(client, "DELETE", f"/api/orgs/acme/members/{ana.id}").json()["error"]["code"]
        == "LAST_OWNER"
    )
    response = write(client, "PATCH", f"/api/orgs/acme/members/{ana.id}", {"role": "member"})
    assert response.json()["error"]["code"] == "LAST_OWNER"


def test_members_of_a_suspended_company_cannot_be_changed(
    control: Database, tenants: Tenants, acme: Org, ana: User, bo: User
) -> None:
    company = orgs.open_company(control, tenants, user_id=ana.id, slug="acme")
    control.write(lambda c: c.execute("UPDATE orgs SET status = 'suspended'"))

    with pytest.raises(Conflict) as err:
        orgs.change_role(control, company, user_id=bo.id, role="owner", actor_id=ana.id, ip=None)
    assert err.value.code == "COMPANY_NOT_ACTIVE"
    with pytest.raises(Conflict):
        orgs.remove_member(control, company, user_id=bo.id, actor_id=ana.id, ip=None)


def test_a_failed_company_file_event_does_not_undo_the_change(
    client: TestClient,
    google: FakeGoogle,
    control: Database,
    ana: User,
    bo: User,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def broken(*args: object, **kwargs: object) -> None:
        raise OSError("disk full")

    monkeypatch.setattr(orgs_repo, "add_event", broken)
    as_(client, google, ana)

    response = write(client, "PATCH", f"/api/orgs/acme/members/{bo.id}", {"role": "owner"})

    assert response.status_code == 200
    assert [r["role"] for r in client.get("/api/orgs/acme/members").json()] == ["owner", "owner"]


def test_owner_changes_a_role(
    client: TestClient, google: FakeGoogle, control: Database, tenants: Tenants, ana: User, bo: User
) -> None:
    as_(client, google, ana)

    response = write(client, "PATCH", f"/api/orgs/acme/members/{bo.id}", {"role": "owner"})

    assert response.status_code == 200
    assert response.json()["role"] == "owner"
    changed = audit(control, "member.role_changed")
    assert [(r["target"], r["actor_id"]) for r in changed] == [("bo@example.com", ana.id)]
    events = tenants.get("acme").db.read(
        lambda c: c.execute(
            "SELECT count(*) FROM events WHERE type = 'member.role_changed'"
        ).fetchone()[0]
    )
    assert events == 1


def test_bad_role_is_422(client: TestClient, google: FakeGoogle, ana: User, bo: User) -> None:
    as_(client, google, ana)

    response = write(client, "PATCH", f"/api/orgs/acme/members/{bo.id}", {"role": "boss"})

    assert response.status_code == 422


def test_last_owner_cannot_be_demoted(
    client: TestClient, google: FakeGoogle, ana: User, bo: User
) -> None:
    as_(client, google, ana)

    response = write(client, "PATCH", f"/api/orgs/acme/members/{ana.id}", {"role": "member"})

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "LAST_OWNER"


def test_last_owner_cannot_be_removed(
    client: TestClient, google: FakeGoogle, ana: User, bo: User
) -> None:
    # KNOWN-DEVIATIONS #5: the prototype lets the only owner remove themselves.
    as_(client, google, ana)

    response = write(client, "DELETE", f"/api/orgs/acme/members/{ana.id}")

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "LAST_OWNER"


def test_an_owner_can_leave_when_another_owner_stays(
    client: TestClient,
    google: FakeGoogle,
    control: Database,
    tenants: Tenants,
    acme: Org,
    ana: User,
) -> None:
    person(control, tenants, acme, "cy", "owner")
    as_(client, google, ana)

    assert write(client, "DELETE", f"/api/orgs/acme/members/{ana.id}").status_code == 204
    assert client.get("/api/orgs/acme/members").status_code == 404  # no longer in it


def test_owner_removes_a_member(
    client: TestClient, google: FakeGoogle, control: Database, ana: User, bo: User
) -> None:
    as_(client, google, ana)

    response = write(client, "DELETE", f"/api/orgs/acme/members/{bo.id}")

    assert response.status_code == 204
    assert [r["email"] for r in client.get("/api/orgs/acme/members").json()] == ["ana@example.com"]
    assert [r["target"] for r in audit(control, "member.removed")] == ["bo@example.com"]


def test_removed_member_can_no_longer_open_the_company(
    client: TestClient, google: FakeGoogle, control: Database, tenants: Tenants, ana: User, bo: User
) -> None:
    orgs.remove_member(
        control,
        orgs.open_company(control, tenants, user_id=ana.id, slug="acme"),
        user_id=bo.id,
        actor_id=ana.id,
        ip=None,
    )
    as_(client, google, bo)

    assert client.get("/api/orgs").json() == []
    assert client.get("/api/orgs/acme/invites").status_code == 404


def test_changing_someone_not_in_the_company_is_404(
    client: TestClient, google: FakeGoogle, control: Database, ana: User
) -> None:
    stranger = users.get_or_create(control, "stranger@example.com")
    as_(client, google, ana)

    assert (
        write(
            client, "PATCH", f"/api/orgs/acme/members/{stranger.id}", {"role": "owner"}
        ).status_code
        == 404
    )
    assert write(client, "DELETE", f"/api/orgs/acme/members/{stranger.id}").status_code == 404


# --- invites -------------------------------------------------------------------------


def test_owner_invites_someone(
    client: TestClient, google: FakeGoogle, control: Database, ana: User
) -> None:
    as_(client, google, ana)

    response = write(
        client, "POST", "/api/orgs/acme/invites", {"email": "Cy@Gmail.com", "role": "member"}
    )

    assert response.status_code == 201
    body = response.json()
    assert response.headers["location"] == f"/api/orgs/acme/invites/{body['id']}"
    assert (body["email"], body["role"], body["account"]) == ("cy@gmail.com", "member", "personal")
    assert body["invited_by"] == "Ana"
    assert [r["email"] for r in client.get("/api/orgs/acme/invites").json()] == ["cy@gmail.com"]


def test_invite_of_a_member_is_409(
    client: TestClient, google: FakeGoogle, ana: User, bo: User
) -> None:
    as_(client, google, ana)

    response = write(
        client, "POST", "/api/orgs/acme/invites", {"email": "bo@example.com", "role": "owner"}
    )

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "ALREADY_MEMBER"


def test_bad_invite_email_is_422(client: TestClient, google: FakeGoogle, ana: User) -> None:
    as_(client, google, ana)

    response = write(client, "POST", "/api/orgs/acme/invites", {"email": "nope", "role": "member"})

    assert response.status_code == 422
    assert response.json()["error"]["details"][0]["field"] == "email"


def test_pending_invites_show_the_workspace_kind(
    client: TestClient, google: FakeGoogle, control: Database, acme: Org, ana: User
) -> None:
    control.write(
        lambda c: c.execute(
            "INSERT INTO workspace_domains (domain, first_seen_at) VALUES ('corp.example', '2026-01-01T00:00:00.000Z')"
        )
    )
    invites.create_invite(control, org=acme, email="di@corp.example", role="owner", actor_id=None)
    invites.create_invite(control, org=acme, email="ed@other.example", role="member", actor_id=None)
    as_(client, google, ana)

    rows = client.get("/api/orgs/acme/invites").json()

    assert [(r["email"], r["account"], r["invited_by"]) for r in rows] == [
        ("ed@other.example", None, None),  # newest first
        ("di@corp.example", "workspace", None),
    ]


def test_used_and_revoked_invites_are_not_listed(
    client: TestClient, google: FakeGoogle, control: Database, acme: Org, ana: User
) -> None:
    gone = invites.create_invite(
        control, org=acme, email="di@example.com", role="member", actor_id=None
    )
    invites.revoke_invite(control, org=acme, invite_id=gone.id, actor_id=None)
    as_(client, google, ana)

    assert client.get("/api/orgs/acme/invites").json() == []


def test_owner_revokes_an_invite(
    client: TestClient, google: FakeGoogle, control: Database, acme: Org, ana: User
) -> None:
    invite = invites.create_invite(
        control, org=acme, email="di@example.com", role="member", actor_id=None
    )
    as_(client, google, ana)

    assert write(client, "DELETE", f"/api/orgs/acme/invites/{invite.id}").status_code == 204
    assert client.get("/api/orgs/acme/invites").json() == []
    assert (
        write(client, "DELETE", f"/api/orgs/acme/invites/{invite.id}").json()["error"]["code"]
        == "INVITE_REVOKED"
    )


def test_another_companys_invite_cannot_be_revoked(
    client: TestClient, google: FakeGoogle, control: Database, tenants: Tenants, ana: User
) -> None:
    beta = orgs.create_company(control, tenants, slug="beta", name="Beta", actor_id=None)
    theirs = invites.create_invite(
        control, org=beta, email="di@example.com", role="member", actor_id=None
    )
    as_(client, google, ana)

    assert write(client, "DELETE", f"/api/orgs/acme/invites/{theirs.id}").status_code == 404


# --- services check the actor (carried from M1-05) ----------------------------------------


def test_add_member_checks_the_actor(
    control: Database, tenants: Tenants, acme: Org, bo: User
) -> None:
    cy = users.get_or_create(control, "cy@example.com")

    with pytest.raises(Forbidden):
        orgs.add_member(control, tenants, org=acme, user=cy, role="owner", actor_id=bo.id)


def test_add_member_never_changes_an_existing_members_role(
    control: Database, tenants: Tenants, acme: Org, ana: User
) -> None:
    # Role changes go through change_role, which keeps the last owner.
    with pytest.raises(Conflict) as err:
        orgs.add_member(control, tenants, org=acme, user=ana, role="member", actor_id=None)
    assert err.value.code == "ALREADY_MEMBER"


def test_people_without_a_name_are_listed_last(
    client: TestClient,
    google: FakeGoogle,
    control: Database,
    tenants: Tenants,
    acme: Org,
    ana: User,
) -> None:
    nameless = users.get_or_create(control, "aaa@example.com")
    orgs.add_member(control, tenants, org=acme, user=nameless, role="member", actor_id=None)
    as_(client, google, ana)

    assert [r["email"] for r in client.get("/api/orgs/acme/members").json()] == [
        "ana@example.com",
        "aaa@example.com",
    ]


def test_only_a_super_admin_creates_a_company(
    control: Database, tenants: Tenants, ana: User
) -> None:
    with pytest.raises(Forbidden):
        orgs.create_company(control, tenants, slug="new", name="New", actor_id=ana.id)
    admin, _ = users.grant_super_admin(control, "admin@example.com", actor_id=None)

    assert (
        orgs.create_company(control, tenants, slug="new", name="New", actor_id=admin.id).slug
        == "new"
    )
