"""Project invites over HTTP. An invite names one email,
one project and a project role. Someone not yet in the company joins it as a
plain member at sign-in and sees only that project; the project part is used
the first time they open the company. Fixtures: conftest.py (acme, boss, pia,
max_, launch); helpers: company.py."""

from __future__ import annotations

import json
from typing import Any

import pytest
from fastapi.testclient import TestClient

from tazko.db import Database
from tazko.db.tenant import Tenants
from tazko.modules.orgs.service import Org
from tazko.modules.users.service import User
from tests.integration.company import BASE, as_, company_rows, join, person, roles, write
from tests.integration.oidc import FakeGoogle, audit, sign_in

NEW = "new.person@example.com"


def invite(client: TestClient, project: int, email: str = NEW, role: str = "member") -> Any:
    return write(client, "POST", f"{BASE}/{project}/invites", {"email": email, "role": role})


def sign_in_as(client: TestClient, google: FakeGoogle, email: str, sub: str = "sub-new") -> None:
    client.cookies.clear()
    done = sign_in(client, google, sub=sub, email=email, name="New Person")
    assert done.status_code == 302, done.text
    assert "refused" not in done.headers["location"], done.headers["location"]


def company_role(control: Database, email: str) -> str | None:
    row = control.read(
        lambda c: c.execute(
            "SELECT m.role FROM org_members m JOIN users u ON u.id = m.user_id WHERE u.email = ?",
            (email,),
        ).fetchone()
    )
    return row[0] if row else None


def user_id(control: Database, email: str) -> int:
    found: int = control.read(
        lambda c: c.execute("SELECT id FROM users WHERE email = ?", (email,)).fetchone()[0]
    )
    return found


@pytest.fixture
def other(client: TestClient, google: FakeGoogle, boss: User, max_: User) -> int:
    """Project "Other", owned by Max; Pia is not in it."""
    as_(client, google, boss)
    made = write(client, "POST", BASE, {"name": "Other", "owner_id": max_.id})
    assert made.status_code == 201, made.text
    project_id: int = made.json()["id"]
    return project_id


# --- a new email ------------------------------------------------------------------------


def test_a_new_email_joins_the_company_as_a_plain_member_and_sees_only_that_project(
    client: TestClient, google: FakeGoogle, control: Database, pia: User, launch: int, other: int
) -> None:
    as_(client, google, pia)
    made = invite(client, launch, role="member")
    assert made.status_code == 201, made.text

    sign_in_as(client, google, NEW)

    assert company_role(control, NEW) == "member"
    seen = client.get(BASE).json()
    assert [(p["id"], p["role"]) for p in seen] == [(launch, "member")]
    assert client.get(f"{BASE}/{other}").status_code == 404


def test_an_invite_as_project_owner_still_joins_the_company_as_a_plain_member(
    client: TestClient,
    google: FakeGoogle,
    control: Database,
    tenants: Tenants,
    pia: User,
    launch: int,
) -> None:
    as_(client, google, pia)
    invite(client, launch, role="owner")

    sign_in_as(client, google, NEW)
    client.get(BASE)

    assert company_role(control, NEW) == "member"
    assert roles(tenants, launch)[user_id(control, NEW)] == "owner"


def test_the_invite_answers_as_the_pending_list_shows_it(
    client: TestClient, google: FakeGoogle, pia: User, launch: int
) -> None:
    as_(client, google, pia)

    made = invite(client, launch, email=" New.Person@Example.com ", role="observer")

    body = made.json()
    assert made.headers["location"] == f"{BASE}/{launch}/invites/{body['id']}"
    assert (body["email"], body["role"], body["invited_by"]) == (NEW, "observer", "Pia")
    assert client.get(f"{BASE}/{launch}/invites").json() == [body]


def test_using_the_invite_writes_one_event_and_the_audit_rows(
    client: TestClient,
    google: FakeGoogle,
    control: Database,
    tenants: Tenants,
    pia: User,
    launch: int,
) -> None:
    as_(client, google, pia)
    invite(client, launch, role="observer")

    sign_in_as(client, google, NEW)
    client.get(BASE)
    client.get(BASE)

    new_id = user_id(control, NEW)
    joined = company_rows(
        tenants,
        "SELECT actor_id, payload FROM events WHERE type = 'project.member_added'"
        " AND json_extract(payload, '$.user_id') = ?",
        new_id,
    )
    assert len(joined) == 1
    assert joined[0][0] == new_id
    assert json.loads(joined[0][1]) == {
        "project_id": launch,
        "user_id": new_id,
        "role": "observer",
        "via": "invite",
        "invited_by": pia.id,
    }
    created = audit(control, "invite.created")[-1]
    assert json.loads(created["detail"]) == {
        "role": "member",
        "project": "Launch",
        "project_role": "observer",
    }
    accepted = audit(control, "invite.accepted")
    assert len(accepted) == 1
    assert json.loads(accepted[0]["detail"]) == {
        "role": "member",
        "project": "Launch",
        "project_role": "observer",
    }


def test_an_invite_is_used_once(
    client: TestClient,
    google: FakeGoogle,
    control: Database,
    tenants: Tenants,
    pia: User,
    launch: int,
) -> None:
    as_(client, google, pia)
    invite(client, launch)
    sign_in_as(client, google, NEW)
    client.get(BASE)
    new_id = user_id(control, NEW)
    as_(client, google, pia)
    assert client.get(f"{BASE}/{launch}/invites").json() == []
    assert write(client, "DELETE", f"{BASE}/{launch}/members/{new_id}").status_code == 204

    sign_in_as(client, google, NEW)

    assert client.get(BASE).json() == []
    assert new_id not in roles(tenants, launch)


# --- someone already in the company ---------------------------------------------------------


def test_a_company_member_gets_the_project_at_their_next_request(
    client: TestClient, google: FakeGoogle, tenants: Tenants, pia: User, max_: User, launch: int
) -> None:
    as_(client, google, max_)
    assert client.get(BASE).json() == []
    session = dict(client.cookies)
    as_(client, google, pia)
    invite(client, launch, email=max_.email, role="member")

    client.cookies.clear()
    client.cookies.update(session)  # Max's session, no new sign-in

    assert [p["id"] for p in client.get(BASE).json()] == [launch]
    assert roles(tenants, launch)[max_.id] == "member"


def test_inviting_someone_already_in_the_project_is_a_conflict(
    client: TestClient, google: FakeGoogle, control: Database, pia: User, max_: User, launch: int
) -> None:
    join(client, google, launch, max_, "member", by=pia)

    response = invite(client, launch, email=max_.email)

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "ALREADY_PROJECT_MEMBER"
    assert audit(control, "invite.created") == []


def test_a_second_pending_invite_to_the_same_project_is_a_conflict(
    client: TestClient, google: FakeGoogle, pia: User, launch: int
) -> None:
    as_(client, google, pia)
    invite(client, launch)

    response = invite(client, launch, role="owner")

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "INVITE_PENDING"


def test_one_email_invited_to_two_projects_joins_both(
    client: TestClient,
    google: FakeGoogle,
    control: Database,
    tenants: Tenants,
    pia: User,
    max_: User,
    launch: int,
    other: int,
) -> None:
    as_(client, google, pia)
    assert invite(client, launch, role="member").status_code == 201
    as_(client, google, max_)
    assert invite(client, other, role="observer").status_code == 201

    sign_in_as(client, google, NEW)

    assert sorted((p["id"], p["role"]) for p in client.get(BASE).json()) == [
        (launch, "member"),
        (other, "observer"),
    ]


def test_a_company_invite_as_owner_wins_over_a_project_invite(
    client: TestClient, google: FakeGoogle, control: Database, boss: User, pia: User, launch: int
) -> None:
    as_(client, google, pia)
    invite(client, launch)
    as_(client, google, boss)
    made = write(client, "POST", "/api/orgs/acme/invites", {"email": NEW, "role": "owner"})
    assert made.status_code == 201, made.text

    sign_in_as(client, google, NEW)

    assert company_role(control, NEW) == "owner"


def test_company_and_project_invites_are_listed_apart(
    client: TestClient, google: FakeGoogle, boss: User, pia: User, launch: int
) -> None:
    as_(client, google, pia)
    invite(client, launch, email="project@example.com")
    as_(client, google, boss)
    write(
        client, "POST", "/api/orgs/acme/invites", {"email": "company@example.com", "role": "member"}
    )

    company = [i["email"] for i in client.get("/api/orgs/acme/invites").json()]
    as_(client, google, pia)
    project = [i["email"] for i in client.get(f"{BASE}/{launch}/invites").json()]

    assert (company, project) == (["company@example.com"], ["project@example.com"])


# --- who may invite ------------------------------------------------------------------------


def test_an_observer_cannot_invite(
    client: TestClient, google: FakeGoogle, control: Database, pia: User, max_: User, launch: int
) -> None:
    join(client, google, launch, max_, "observer", by=pia)
    as_(client, google, max_)

    response = invite(client, launch)

    assert response.status_code == 403
    assert audit(control, "invite.created") == []


def test_a_member_invites_only_when_the_project_allows_it_and_never_an_owner(
    client: TestClient, google: FakeGoogle, pia: User, max_: User, launch: int
) -> None:
    join(client, google, launch, max_, "member", by=pia)
    as_(client, google, max_)
    assert invite(client, launch).status_code == 403
    as_(client, google, pia)
    write(client, "PATCH", f"{BASE}/{launch}", {"members_can_invite": True})
    as_(client, google, max_)

    assert invite(client, launch, role="owner").status_code == 403
    assert invite(client, launch, role="member").status_code == 201


def test_someone_outside_the_project_cannot_see_or_use_its_invites(
    client: TestClient, google: FakeGoogle, control: Database, pia: User, max_: User, launch: int
) -> None:
    as_(client, google, pia)
    made = invite(client, launch).json()
    as_(client, google, max_)

    assert invite(client, launch, email="x@example.com").status_code == 404
    assert client.get(f"{BASE}/{launch}/invites").status_code == 404
    assert write(client, "DELETE", f"{BASE}/{launch}/invites/{made['id']}").status_code == 404
    assert len(audit(control, "invite.created")) == 1
    assert audit(control, "invite.revoked") == []


def test_a_company_owner_outside_the_project_invites_owners_only(
    client: TestClient, google: FakeGoogle, boss: User, launch: int
) -> None:
    as_(client, google, boss)

    assert invite(client, launch, role="member").status_code == 403
    assert invite(client, launch, role="owner").status_code == 201


def test_an_archived_project_takes_no_invites(
    client: TestClient, google: FakeGoogle, boss: User, pia: User, launch: int
) -> None:
    as_(client, google, boss)
    write(client, "PATCH", f"{BASE}/{launch}", {"archived": True})
    as_(client, google, pia)

    response = invite(client, launch)

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "PROJECT_ARCHIVED"


@pytest.mark.parametrize(
    ("body", "field"),
    [
        ({"email": "not-an-email", "role": "member"}, "email"),
        ({"email": NEW, "role": "admin"}, "role"),
        ({"email": NEW}, "role"),
        ({"email": NEW, "role": "member", "extra": 1}, "extra"),
    ],
)
def test_a_bad_invite_is_refused(
    client: TestClient,
    google: FakeGoogle,
    pia: User,
    launch: int,
    body: dict[str, Any],
    field: str,
) -> None:
    as_(client, google, pia)

    response = write(client, "POST", f"{BASE}/{launch}/invites", body)

    assert response.status_code == 422
    assert [d["field"] for d in response.json()["error"]["details"]] == [field]


def test_project_members_see_the_pending_invites(
    client: TestClient, google: FakeGoogle, pia: User, max_: User, launch: int
) -> None:
    join(client, google, launch, max_, "observer", by=pia)
    invite(client, launch)
    as_(client, google, max_)

    assert [i["email"] for i in client.get(f"{BASE}/{launch}/invites").json()] == [NEW]


# --- revoking --------------------------------------------------------------------------------


def test_a_revoked_project_invite_lets_nobody_in(
    client: TestClient, google: FakeGoogle, control: Database, pia: User, launch: int
) -> None:
    as_(client, google, pia)
    made = invite(client, launch).json()

    assert write(client, "DELETE", f"{BASE}/{launch}/invites/{made['id']}").status_code == 204
    assert client.get(f"{BASE}/{launch}/invites").json() == []

    client.cookies.clear()
    refused = sign_in(client, google, sub="sub-new", email=NEW, name="New")
    assert "refused" in refused.headers["location"]
    assert company_role(control, NEW) is None


def test_only_those_who_may_make_an_invite_revoke_it(
    client: TestClient, google: FakeGoogle, pia: User, max_: User, launch: int
) -> None:
    join(client, google, launch, max_, "member", by=pia)
    write(client, "PATCH", f"{BASE}/{launch}", {"members_can_invite": True})
    owner_invite = invite(client, launch, email="o@example.com", role="owner").json()
    member_invite = invite(client, launch, email="m@example.com", role="member").json()
    as_(client, google, max_)

    assert (
        write(client, "DELETE", f"{BASE}/{launch}/invites/{owner_invite['id']}").status_code == 403
    )
    assert (
        write(client, "DELETE", f"{BASE}/{launch}/invites/{member_invite['id']}").status_code == 204
    )


def test_an_invite_is_revoked_only_under_its_own_project(
    client: TestClient,
    google: FakeGoogle,
    boss: User,
    pia: User,
    max_: User,
    launch: int,
    other: int,
) -> None:
    as_(client, google, pia)
    made = invite(client, launch).json()
    as_(client, google, boss)
    company = write(
        client, "POST", "/api/orgs/acme/invites", {"email": "c@example.com", "role": "member"}
    ).json()
    as_(client, google, max_)

    assert write(client, "DELETE", f"{BASE}/{other}/invites/{made['id']}").status_code == 404
    as_(client, google, pia)
    assert write(client, "DELETE", f"{BASE}/{launch}/invites/{company['id']}").status_code == 404
    assert write(client, "DELETE", f"{BASE}/{launch}/invites/{made['id']}").status_code == 204
    assert write(client, "DELETE", f"{BASE}/{launch}/invites/{made['id']}").status_code == 409


# --- what changed before the invite was used --------------------------------------------------


def test_a_project_deleted_before_the_sign_in_leaves_a_plain_company_member(
    client: TestClient, google: FakeGoogle, control: Database, boss: User, pia: User, launch: int
) -> None:
    as_(client, google, pia)
    invite(client, launch)
    as_(client, google, boss)
    assert write(client, "DELETE", f"{BASE}/{launch}").status_code == 204

    sign_in_as(client, google, NEW)

    assert company_role(control, NEW) == "member"
    assert client.get(BASE).json() == []
    assert len(audit(control, "invite.accepted")) == 1


def test_someone_removed_from_the_company_cannot_come_back_on_a_pending_invite(
    client: TestClient,
    google: FakeGoogle,
    control: Database,
    acme: Org,
    boss: User,
    pia: User,
    launch: int,
) -> None:
    as_(client, google, pia)
    invite(client, launch)
    sign_in_as(client, google, NEW)  # joined the company, never opened it
    new_id = user_id(control, NEW)
    as_(client, google, boss)
    assert write(client, "DELETE", f"/api/orgs/acme/members/{new_id}").status_code == 204

    client.cookies.clear()
    sign_in(client, google, sub="sub-new", email=NEW, name="New")

    assert company_role(control, NEW) is None


def test_a_company_owner_joining_by_invite_is_audit_logged(
    client: TestClient,
    google: FakeGoogle,
    control: Database,
    tenants: Tenants,
    acme: Org,
    pia: User,
    launch: int,
) -> None:
    second = person(control, tenants, acme, "olga", "owner")
    as_(client, google, pia)
    invite(client, launch, email=second.email, role="member")

    as_(client, google, second)
    client.get(BASE)

    logged = audit(control, "project.company_owner_added")
    assert [(r["target"], json.loads(r["detail"])) for r in logged] == [
        (second.email, {"role": "member", "project": "Launch"})
    ]


# --- checked again when used -------------------------------------------------------------


def test_an_invite_dies_when_its_maker_may_no_longer_make_it(
    client: TestClient, google: FakeGoogle, control: Database, pia: User, max_: User, launch: int
) -> None:
    join(client, google, launch, max_, "member", by=pia)
    write(client, "PATCH", f"{BASE}/{launch}", {"members_can_invite": True})
    as_(client, google, max_)
    assert invite(client, launch).status_code == 201
    as_(client, google, pia)
    write(client, "PATCH", f"{BASE}/{launch}", {"members_can_invite": False})

    sign_in_as(client, google, NEW)

    assert company_role(control, NEW) == "member"
    assert client.get(BASE).json() == []
    revoked = audit(control, "invite.revoked")
    assert [json.loads(r["detail"])["reason"] for r in revoked] == ["inviter_not_allowed"]
    assert audit(control, "invite.accepted") == []


def test_an_invite_to_an_archived_project_waits_until_it_is_restored(
    client: TestClient, google: FakeGoogle, boss: User, pia: User, max_: User, launch: int
) -> None:
    as_(client, google, pia)
    invite(client, launch, email=max_.email)
    as_(client, google, boss)
    write(client, "PATCH", f"{BASE}/{launch}", {"archived": True})
    as_(client, google, max_)
    assert client.get(BASE).json() == []
    as_(client, google, boss)
    write(client, "PATCH", f"{BASE}/{launch}", {"archived": False})

    as_(client, google, max_)

    assert [p["id"] for p in client.get(BASE).json()] == [launch]


def test_someone_taken_off_a_project_does_not_come_back_on_a_pending_invite(
    client: TestClient, google: FakeGoogle, tenants: Tenants, pia: User, max_: User, launch: int
) -> None:
    as_(client, google, pia)
    invite(client, launch, email=max_.email)
    added = write(
        client, "POST", f"{BASE}/{launch}/members", {"user_id": max_.id, "role": "member"}
    )
    assert added.status_code == 201
    assert write(client, "DELETE", f"{BASE}/{launch}/members/{max_.id}").status_code == 204

    as_(client, google, max_)

    assert client.get(BASE).json() == []
    assert max_.id not in roles(tenants, launch)


def test_a_personal_account_on_a_workspace_address_uses_no_project_invite(
    client: TestClient,
    google: FakeGoogle,
    control: Database,
    tenants: Tenants,
    acme: Org,
    pia: User,
    launch: int,
) -> None:
    # given Bo linked a personal account on bo@corp.example, and corp.example
    # became known as a Workspace after that
    bo = person(control, tenants, acme, "bo", "member")
    control.write(
        lambda c: c.execute("UPDATE users SET email = 'bo@corp.example' WHERE id = ?", (bo.id,))
    )
    client.cookies.clear()
    sign_in(client, google, sub="sub-bo", email="bo@corp.example", name="Bo")
    session = dict(client.cookies)
    control.write(
        lambda c: c.execute(
            "INSERT INTO workspace_domains (domain, first_seen_at)"
            " VALUES ('corp.example', '2026-11-25T00:00:00.000Z')"
        )
    )
    as_(client, google, pia)
    invite(client, launch, email="bo@corp.example")

    # when Bo's personal account opens the company
    client.cookies.clear()
    client.cookies.update(session)
    projects = client.get(BASE).json()

    # then the invite is not used
    assert projects == []
    assert bo.id not in roles(tenants, launch)


def test_the_company_route_cannot_revoke_a_project_invite(
    client: TestClient, google: FakeGoogle, control: Database, boss: User, pia: User, launch: int
) -> None:
    as_(client, google, pia)
    made = invite(client, launch).json()
    as_(client, google, boss)

    response = write(client, "DELETE", f"/api/orgs/acme/invites/{made['id']}")

    assert response.status_code == 404
    assert audit(control, "invite.revoked") == []


def test_a_project_takes_at_most_500_pending_invites(
    client: TestClient, google: FakeGoogle, control: Database, acme: Org, pia: User, launch: int
) -> None:
    control.write(
        lambda c: c.executemany(
            "INSERT INTO invites (org_id, email, role, project_id, project_role, created_by,"
            " created_at, expires_at) VALUES (?, ?, 'member', ?, 'member', ?,"
            " '2026-11-25T00:00:00.000Z', '2999-01-01T00:00:00.000Z')",
            [(acme.id, f"p{n}@example.com", launch, pia.id) for n in range(500)],
        )
    )
    as_(client, google, pia)

    response = invite(client, launch)

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "TOO_MANY_INVITES"
