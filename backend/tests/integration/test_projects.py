"""Projects and project members over HTTP (M2-02 part 1, D39). Every route
runs with a real session; rows are checked in the company file."""

from __future__ import annotations

import sqlite3
from typing import Any

import pytest
from fastapi.testclient import TestClient

from tazko.db import Database
from tazko.db.tenant import Tenants
from tazko.modules.orgs import service as orgs
from tazko.modules.orgs.service import Org
from tazko.modules.users import service as users
from tazko.modules.users.service import User
from tests.integration.oidc import SAME_ORIGIN, FakeGoogle, audit, sign_in

BASE = "/api/orgs/acme/projects"


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


@pytest.fixture
def boss(control: Database, tenants: Tenants, acme: Org) -> User:
    """A company owner."""
    return person(control, tenants, acme, "boss", "owner")


@pytest.fixture
def pia(control: Database, tenants: Tenants, acme: Org) -> User:
    """A company member who becomes the project's owner."""
    return person(control, tenants, acme, "pia", "member")


@pytest.fixture
def max_(control: Database, tenants: Tenants, acme: Org) -> User:
    """Another company member."""
    return person(control, tenants, acme, "max", "member")


def as_(client: TestClient, google: FakeGoogle, user: User) -> None:
    client.cookies.clear()
    sign_in(client, google, sub=f"sub-{user.id}", email=user.email, name=user.name)


def write(client: TestClient, method: str, path: str, body: Any = None) -> Any:
    return client.request(method, path, json=body, headers=SAME_ORIGIN)


def company_rows(tenants: Tenants, sql: str, *args: object) -> list[sqlite3.Row]:
    return tenants.get("acme").db.read(lambda c: c.execute(sql, args).fetchall())


@pytest.fixture
def launch(client: TestClient, google: FakeGoogle, boss: User, pia: User) -> int:
    """Project "Launch", made by the company owner with Pia as its owner."""
    as_(client, google, boss)
    made = write(client, "POST", BASE, {"name": "Launch", "owner_id": pia.id})
    assert made.status_code == 201, made.text
    project_id: int = made.json()["id"]
    return project_id


def join(
    client: TestClient, google: FakeGoogle, project: int, user: User, role: str, by: User
) -> None:
    as_(client, google, by)
    added = write(client, "POST", f"{BASE}/{project}/members", {"user_id": user.id, "role": role})
    assert added.status_code == 201, added.text


# --- creating and listing --------------------------------------------------------------


def test_a_company_member_who_is_not_an_owner_cannot_create_a_project(
    client: TestClient, google: FakeGoogle, pia: User
) -> None:
    as_(client, google, pia)

    response = write(client, "POST", BASE, {"name": "Mine", "owner_id": pia.id})

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "FORBIDDEN"


def test_a_company_owner_creates_a_project_with_its_first_owner(
    client: TestClient, google: FakeGoogle, tenants: Tenants, boss: User, pia: User
) -> None:
    as_(client, google, boss)

    response = write(client, "POST", BASE, {"name": " Launch ", "owner_id": pia.id})

    assert response.status_code == 201
    body = response.json()
    assert response.headers["location"] == f"{BASE}/{body['id']}"
    assert body["name"] == "Launch"
    assert body["members_can_create_boards"] is True
    assert body["members_can_invite"] is False
    assert (body["aging_enabled"], body["aging_days"]) == (True, 7)
    assert body["role"] is None  # the company owner is not in it
    assert [
        tuple(r) for r in company_rows(tenants, "SELECT person_id, role FROM project_members")
    ] == [(pia.id, "owner")]
    assert [r[0] for r in company_rows(tenants, "SELECT type FROM events ORDER BY id")][-1] == (
        "project.created"
    )


@pytest.mark.parametrize("bad", [{"name": "   "}, {"name": "x" * 101}, {"name": "P", "color": ""}])
def test_a_project_needs_a_valid_name_and_fields(
    client: TestClient, google: FakeGoogle, boss: User, pia: User, bad: dict[str, Any]
) -> None:
    as_(client, google, boss)

    response = write(client, "POST", BASE, {"owner_id": pia.id, **bad})

    assert response.status_code == 422


def test_the_first_owner_must_be_in_the_company(
    client: TestClient, google: FakeGoogle, control: Database, boss: User
) -> None:
    stranger = users.get_or_create(control, "stranger@example.com", name="Stranger")
    as_(client, google, boss)

    response = write(client, "POST", BASE, {"name": "Launch", "owner_id": stranger.id})

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "NOT_A_COMPANY_MEMBER"
    assert response.json()["error"]["details"][0]["field"] == "owner_id"


def test_people_see_only_the_projects_they_belong_to(
    client: TestClient, google: FakeGoogle, boss: User, pia: User, max_: User, launch: int
) -> None:
    as_(client, google, pia)
    assert [p["id"] for p in client.get(BASE).json()] == [launch]
    assert client.get(BASE).json()[0]["role"] == "owner"

    as_(client, google, max_)
    assert client.get(BASE).json() == []

    as_(client, google, boss)  # made it, but is not in it
    assert client.get(BASE).json() == []


def test_company_owners_see_every_project_on_the_manage_view(
    client: TestClient, google: FakeGoogle, boss: User, pia: User, launch: int
) -> None:
    as_(client, google, boss)

    response = client.get(BASE, params={"view": "manage"})

    assert response.status_code == 200
    (row,) = response.json()
    assert row["id"] == launch
    assert row["owners"] == [{"user_id": pia.id, "name": "Pia"}]
    assert (row["members"], row["boards"]) == (1, 0)


def test_the_manage_view_is_for_company_owners_only(
    client: TestClient, google: FakeGoogle, pia: User, launch: int
) -> None:
    as_(client, google, pia)

    assert client.get(BASE, params={"view": "manage"}).status_code == 403


# --- who sees a project ------------------------------------------------------------------


def test_a_company_member_outside_the_project_cannot_see_it(
    client: TestClient, google: FakeGoogle, max_: User, launch: int
) -> None:
    as_(client, google, max_)

    assert client.get(f"{BASE}/{launch}").status_code == 404
    assert client.get(f"{BASE}/{launch}/members").status_code == 404
    assert write(client, "PATCH", f"{BASE}/{launch}", {"description": "x"}).status_code == 404
    assert client.get(f"{BASE}/999").status_code == 404


def test_an_observer_cannot_change_anything(
    client: TestClient, google: FakeGoogle, pia: User, max_: User, launch: int
) -> None:
    join(client, google, launch, max_, "observer", by=pia)
    as_(client, google, max_)

    assert client.get(f"{BASE}/{launch}").json()["role"] == "observer"
    assert write(client, "PATCH", f"{BASE}/{launch}", {"description": "x"}).status_code == 403
    assert write(client, "DELETE", f"{BASE}/{launch}/members/{pia.id}").status_code == 403


# --- settings and management ---------------------------------------------------------------


def test_a_project_owner_changes_the_settings(
    client: TestClient, google: FakeGoogle, tenants: Tenants, pia: User, launch: int
) -> None:
    as_(client, google, pia)
    changes = {
        "name": "Launch 2",
        "description": "Ship it",
        "color": "teal",
        "default_background": "sea",
        "members_can_create_boards": False,
        "members_can_invite": True,
        "aging_enabled": False,
        "aging_days": 14,
    }

    response = write(client, "PATCH", f"{BASE}/{launch}", changes)

    assert response.status_code == 200
    assert {k: response.json()[k] for k in changes} == changes
    assert client.get(f"{BASE}/{launch}").json()["description"] == "Ship it"
    assert company_rows(tenants, "SELECT type FROM events ORDER BY id DESC LIMIT 1")[0][0] == (
        "project.updated"
    )


def test_aging_days_are_one_of_the_offered_choices(
    client: TestClient, google: FakeGoogle, pia: User, launch: int
) -> None:
    as_(client, google, pia)

    assert write(client, "PATCH", f"{BASE}/{launch}", {"aging_days": 5}).status_code == 422


def test_a_project_owner_cannot_archive_or_delete_the_project(
    client: TestClient, google: FakeGoogle, pia: User, launch: int
) -> None:
    as_(client, google, pia)

    assert write(client, "PATCH", f"{BASE}/{launch}", {"archived": True}).status_code == 403
    assert write(client, "DELETE", f"{BASE}/{launch}").status_code == 403


def test_a_company_owner_cannot_change_the_settings_of_a_project_they_are_not_in(
    client: TestClient, google: FakeGoogle, boss: User, launch: int
) -> None:
    as_(client, google, boss)

    assert write(client, "PATCH", f"{BASE}/{launch}", {"description": "x"}).status_code == 403
    renamed = write(client, "PATCH", f"{BASE}/{launch}", {"name": "Renamed"})
    assert renamed.status_code == 200
    assert renamed.json()["name"] == "Renamed"


def test_an_archived_project_can_be_read_but_not_changed_until_restored(
    client: TestClient, google: FakeGoogle, boss: User, pia: User, launch: int
) -> None:
    as_(client, google, boss)
    archived = write(client, "PATCH", f"{BASE}/{launch}", {"archived": True})
    assert archived.status_code == 200
    assert archived.json()["archived_at"] is not None

    as_(client, google, pia)
    assert client.get(f"{BASE}/{launch}").status_code == 200
    refused = write(client, "PATCH", f"{BASE}/{launch}", {"description": "x"})
    assert refused.status_code == 409
    assert refused.json()["error"]["code"] == "PROJECT_ARCHIVED"

    as_(client, google, boss)
    assert (
        write(client, "PATCH", f"{BASE}/{launch}", {"archived": False}).json()["archived_at"]
        is None
    )
    as_(client, google, pia)
    assert write(client, "PATCH", f"{BASE}/{launch}", {"description": "x"}).status_code == 200


def test_a_deleted_project_is_gone_for_everyone(
    client: TestClient, google: FakeGoogle, tenants: Tenants, boss: User, pia: User, launch: int
) -> None:
    as_(client, google, boss)

    assert write(client, "DELETE", f"{BASE}/{launch}").status_code == 204

    assert client.get(BASE, params={"view": "manage"}).json() == []
    assert write(client, "DELETE", f"{BASE}/{launch}").status_code == 404
    as_(client, google, pia)
    assert client.get(BASE).json() == []
    assert client.get(f"{BASE}/{launch}").status_code == 404
    # In trash, not removed: the row stays for 30 days.
    assert company_rows(tenants, "SELECT deleted_at IS NOT NULL FROM projects")[0][0] == 1


# --- project members ---------------------------------------------------------------------------


def test_a_project_owner_adds_lists_and_changes_members(
    client: TestClient, google: FakeGoogle, pia: User, max_: User, launch: int
) -> None:
    join(client, google, launch, max_, "member", by=pia)

    changed = write(client, "PATCH", f"{BASE}/{launch}/members/{max_.id}", {"role": "observer"})

    assert changed.status_code == 200
    assert changed.json()["role"] == "observer"
    listed = client.get(f"{BASE}/{launch}/members").json()
    assert [(m["name"], m["role"]) for m in listed] == [("Max", "observer"), ("Pia", "owner")]


def test_a_person_outside_the_company_cannot_be_added(
    client: TestClient, google: FakeGoogle, control: Database, pia: User, launch: int
) -> None:
    stranger = users.get_or_create(control, "stranger@example.com", name="Stranger")
    as_(client, google, pia)

    response = write(
        client, "POST", f"{BASE}/{launch}/members", {"user_id": stranger.id, "role": "member"}
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "NOT_A_COMPANY_MEMBER"


def test_adding_someone_already_in_the_project_is_a_conflict(
    client: TestClient, google: FakeGoogle, pia: User, max_: User, launch: int
) -> None:
    join(client, google, launch, max_, "member", by=pia)

    again = write(client, "POST", f"{BASE}/{launch}/members", {"user_id": max_.id, "role": "owner"})

    assert again.status_code == 409
    assert again.json()["error"]["code"] == "ALREADY_PROJECT_MEMBER"


def test_a_member_adds_people_only_when_the_project_allows_it(
    client: TestClient,
    google: FakeGoogle,
    control: Database,
    tenants: Tenants,
    acme: Org,
    pia: User,
    max_: User,
    launch: int,
) -> None:
    eve = person(control, tenants, acme, "eve", "member")
    join(client, google, launch, max_, "member", by=pia)
    as_(client, google, max_)
    body = {"user_id": eve.id, "role": "member"}
    assert write(client, "POST", f"{BASE}/{launch}/members", body).status_code == 403

    as_(client, google, pia)
    write(client, "PATCH", f"{BASE}/{launch}", {"members_can_invite": True})
    as_(client, google, max_)
    assert write(client, "POST", f"{BASE}/{launch}/members", body).status_code == 201
    owner = {"role": "owner"}
    assert write(client, "PATCH", f"{BASE}/{launch}/members/{eve.id}", owner).status_code == 403


def test_a_company_owner_adds_themselves_and_it_is_audit_logged(
    client: TestClient, google: FakeGoogle, control: Database, boss: User, launch: int
) -> None:
    as_(client, google, boss)

    response = write(
        client, "POST", f"{BASE}/{launch}/members", {"user_id": boss.id, "role": "owner"}
    )

    assert response.status_code == 201
    assert client.get(f"{BASE}/{launch}").json()["role"] == "owner"
    (row,) = audit(control, "project.self_added")
    assert (row["actor_id"], row["target"]) == (boss.id, "Launch")


def test_a_company_owner_manages_project_owners_but_not_plain_members(
    client: TestClient, google: FakeGoogle, boss: User, pia: User, max_: User, launch: int
) -> None:
    as_(client, google, boss)

    owner = write(client, "POST", f"{BASE}/{launch}/members", {"user_id": max_.id, "role": "owner"})
    demote = write(client, "PATCH", f"{BASE}/{launch}/members/{max_.id}", {"role": "member"})
    then = write(client, "PATCH", f"{BASE}/{launch}/members/{max_.id}", {"role": "observer"})

    assert (owner.status_code, demote.status_code, then.status_code) == (201, 200, 403)


def test_the_last_project_owner_is_never_demoted_or_removed(
    client: TestClient, google: FakeGoogle, boss: User, pia: User, launch: int
) -> None:
    as_(client, google, pia)

    demote = write(client, "PATCH", f"{BASE}/{launch}/members/{pia.id}", {"role": "member"})
    remove = write(client, "DELETE", f"{BASE}/{launch}/members/{pia.id}")

    assert (demote.status_code, remove.status_code) == (409, 409)
    assert demote.json()["error"]["code"] == remove.json()["error"]["code"] == "LAST_OWNER"
    as_(client, google, boss)
    assert write(client, "DELETE", f"{BASE}/{launch}/members/{pia.id}").status_code == 409


def test_removing_a_member_unassigns_them_and_ends_their_board_access(
    client: TestClient, google: FakeGoogle, tenants: Tenants, pia: User, max_: User, launch: int
) -> None:
    """D6: their cards stay; they come off assignees, watchers and restricted boards."""
    join(client, google, launch, max_, "member", by=pia)

    def seed(conn: sqlite3.Connection) -> None:
        at = "2026-11-23T09:00:00.000Z"
        board = conn.execute(
            "INSERT INTO boards (project_id, name, restricted, created_at) VALUES (?, 'B', 1, ?)"
            " RETURNING id",
            (launch, at),
        ).fetchone()[0]
        lst = conn.execute(
            "INSERT INTO lists (board_id, name, rank, created_at) VALUES (?, 'L', 'V', ?)"
            " RETURNING id",
            (board, at),
        ).fetchone()[0]
        card = conn.execute(
            "INSERT INTO cards (list_id, title, rank, created_at, updated_at)"
            " VALUES (?, 'C', 'V', ?, ?) RETURNING id",
            (lst, at, at),
        ).fetchone()[0]
        conn.execute("INSERT INTO board_access VALUES (?, ?)", (board, max_.id))
        conn.execute("INSERT INTO card_members VALUES (?, ?)", (card, max_.id))
        conn.execute("INSERT INTO card_watchers VALUES (?, ?)", (card, max_.id))

    tenants.get("acme").db.write(seed)

    assert write(client, "DELETE", f"{BASE}/{launch}/members/{max_.id}").status_code == 204

    for table in ("board_access", "card_members", "card_watchers"):
        assert company_rows(tenants, f"SELECT count(*) FROM {table}")[0][0] == 0  # noqa: S608 (fixed names)
    assert company_rows(tenants, "SELECT count(*) FROM cards")[0][0] == 1
    types = [r[0] for r in company_rows(tenants, "SELECT type FROM events ORDER BY id")]
    assert types[-1] == "project.member_removed"


def test_null_clears_the_colour_but_is_not_a_name(
    client: TestClient, google: FakeGoogle, pia: User, launch: int
) -> None:
    as_(client, google, pia)
    write(client, "PATCH", f"{BASE}/{launch}", {"color": "teal"})

    cleared = write(client, "PATCH", f"{BASE}/{launch}", {"color": None})
    refused = write(client, "PATCH", f"{BASE}/{launch}", {"name": None})

    assert (cleared.status_code, cleared.json()["color"]) == (200, None)
    assert refused.status_code == 422


def test_giving_someone_the_role_they_have_changes_nothing(
    client: TestClient, google: FakeGoogle, tenants: Tenants, pia: User, max_: User, launch: int
) -> None:
    join(client, google, launch, max_, "member", by=pia)
    before = company_rows(tenants, "SELECT count(*) FROM events")[0][0]

    same = write(client, "PATCH", f"{BASE}/{launch}/members/{max_.id}", {"role": "member"})

    assert (same.status_code, same.json()["role"]) == (200, "member")
    assert company_rows(tenants, "SELECT count(*) FROM events")[0][0] == before


def test_changing_someone_who_is_not_in_the_project_is_404(
    client: TestClient, google: FakeGoogle, pia: User, max_: User, launch: int
) -> None:
    as_(client, google, pia)

    assert (
        write(client, "PATCH", f"{BASE}/{launch}/members/{max_.id}", {"role": "member"}).status_code
        == 404
    )
    assert write(client, "DELETE", f"{BASE}/{launch}/members/{max_.id}").status_code == 404
