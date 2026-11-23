"""Boards in a project over HTTP (M2-02 part 2, D40): who sees and changes
them, restricted boards (KNOWN-DEVIATIONS #1) and stars. Fixtures:
conftest.py (acme, boss, pia, max_, launch); helpers: company.py."""

from __future__ import annotations

from typing import Any

import pytest
from fastapi.testclient import TestClient

from tazko.db import Database
from tazko.db.tenant import Tenants
from tazko.modules.orgs.service import Org
from tazko.modules.users.service import User
from tests.integration.company import BASE, as_, company_rows, join, person, write
from tests.integration.oidc import FakeGoogle


def boards_of(project: int) -> str:
    return f"{BASE}/{project}/boards"


def make_board(client: TestClient, project: int, name: str = "Sprint", **more: Any) -> int:
    made = write(client, "POST", boards_of(project), {"name": name, **more})
    assert made.status_code == 201, made.text
    board_id: int = made.json()["id"]
    return board_id


def names(client: TestClient, project: int) -> list[str]:
    listed = client.get(boards_of(project))
    assert listed.status_code == 200, listed.text
    return [b["name"] for b in listed.json()]


@pytest.fixture
def team(client: TestClient, google: FakeGoogle, pia: User, max_: User, launch: int) -> int:
    """Launch with Max as a member; signed in as Pia (its owner) at the end."""
    join(client, google, launch, max_, "member", by=pia)
    return launch


# --- creating and listing ----------------------------------------------------------------


def test_a_project_member_creates_a_board_that_the_project_sees(
    client: TestClient, google: FakeGoogle, tenants: Tenants, pia: User, max_: User, team: int
) -> None:
    as_(client, google, max_)

    made = write(client, "POST", boards_of(team), {"name": " Sprint 1 "})

    assert made.status_code == 201
    body = made.json()
    assert made.headers["location"] == f"{boards_of(team)}/{body['id']}"
    assert (body["name"], body["restricted"], body["starred"]) == ("Sprint 1", False, False)
    as_(client, google, pia)
    assert names(client, team) == ["Sprint 1"]
    (event,) = company_rows(
        tenants, "SELECT type, board_id FROM events WHERE type = 'board.created'"
    )
    assert tuple(event) == ("board.created", body["id"])


def test_a_new_board_takes_the_project_background_unless_given_one(
    client: TestClient, google: FakeGoogle, pia: User, launch: int
) -> None:
    as_(client, google, pia)
    write(client, "PATCH", f"{BASE}/{launch}", {"default_background": "sea"})

    plain = client.get(f"{boards_of(launch)}/{make_board(client, launch, 'A')}").json()
    own = client.get(
        f"{boards_of(launch)}/{make_board(client, launch, 'B', background='dusk')}"
    ).json()

    assert (plain["background"], own["background"]) == ("sea", "dusk")


def test_an_observer_cannot_create_a_board(
    client: TestClient, google: FakeGoogle, tenants: Tenants, pia: User, max_: User, launch: int
) -> None:
    join(client, google, launch, max_, "observer", by=pia)
    as_(client, google, max_)

    assert write(client, "POST", boards_of(launch), {"name": "Mine"}).status_code == 403
    assert company_rows(tenants, "SELECT count(*) FROM boards")[0][0] == 0


def test_members_cannot_create_boards_when_the_project_says_so(
    client: TestClient, google: FakeGoogle, tenants: Tenants, pia: User, max_: User, team: int
) -> None:
    as_(client, google, pia)
    write(client, "PATCH", f"{BASE}/{team}", {"members_can_create_boards": False})
    as_(client, google, max_)

    assert write(client, "POST", boards_of(team), {"name": "Mine"}).status_code == 403
    assert company_rows(tenants, "SELECT count(*) FROM boards")[0][0] == 0


@pytest.mark.parametrize(
    "bad", [{"name": "  "}, {"name": "x" * 101}, {"name": "B", "background": ""}]
)
def test_a_board_needs_a_valid_name(
    client: TestClient, google: FakeGoogle, pia: User, launch: int, bad: dict[str, Any]
) -> None:
    as_(client, google, pia)

    assert write(client, "POST", boards_of(launch), bad).status_code == 422


# --- who opens boards ----------------------------------------------------------------------


def test_a_company_owner_opens_boards_only_once_added_to_the_project(
    client: TestClient, google: FakeGoogle, boss: User, pia: User, launch: int
) -> None:
    as_(client, google, pia)
    board = make_board(client, launch)
    as_(client, google, boss)

    listed = client.get(boards_of(launch))
    opened = client.get(f"{boards_of(launch)}/{board}")
    made = write(client, "POST", boards_of(launch), {"name": "Mine"})

    assert (listed.status_code, opened.status_code, made.status_code) == (403, 403, 403)
    assert listed.json()["error"]["code"] == "NOT_IN_PROJECT"
    join(client, google, launch, boss, "member", by=boss)
    assert names(client, launch) == ["Sprint"]


def test_a_company_member_outside_the_project_finds_no_boards(
    client: TestClient, google: FakeGoogle, pia: User, max_: User, launch: int
) -> None:
    as_(client, google, pia)
    board = make_board(client, launch)
    as_(client, google, max_)

    assert client.get(boards_of(launch)).status_code == 404
    assert client.get(f"{boards_of(launch)}/{board}").status_code == 404


def test_a_board_is_found_only_under_its_own_project(
    client: TestClient, google: FakeGoogle, boss: User, pia: User, launch: int
) -> None:
    as_(client, google, boss)
    other = write(client, "POST", BASE, {"name": "Other", "owner_id": pia.id}).json()["id"]
    as_(client, google, pia)
    board = make_board(client, launch)

    assert client.get(f"{boards_of(other)}/{board}").status_code == 404
    assert write(client, "PATCH", f"{boards_of(other)}/{board}", {"name": "X"}).status_code == 404


# --- restricted boards (KNOWN-DEVIATIONS #1) ------------------------------------------------


def restrict(client: TestClient, project: int, board: int, people: list[int]) -> Any:
    return write(
        client,
        "PUT",
        f"{boards_of(project)}/{board}/access",
        {"restricted": True, "people": people},
    )


def test_a_restricted_board_is_hidden_from_project_members_not_on_its_list(
    client: TestClient, google: FakeGoogle, tenants: Tenants, pia: User, max_: User, team: int
) -> None:
    """KNOWN-DEVIATIONS #1: not listed, and every route answers 404, never 403."""
    as_(client, google, pia)
    board = make_board(client, team, "Secret")
    make_board(client, team, "Open")
    assert restrict(client, team, board, []).status_code == 200
    as_(client, google, max_)

    path = f"{boards_of(team)}/{board}"
    assert names(client, team) == ["Open"]
    assert client.get(path).status_code == 404
    assert write(client, "PATCH", path, {"name": "Mine"}).status_code == 404
    assert write(client, "PUT", f"{path}/star").status_code == 404
    assert restrict(client, team, board, [max_.id]).status_code == 404
    assert company_rows(tenants, "SELECT name FROM boards WHERE id = ?", board)[0][0] == "Secret"
    assert company_rows(tenants, "SELECT count(*) FROM board_stars")[0][0] == 0


def test_listed_members_and_project_owners_open_a_restricted_board(
    client: TestClient,
    google: FakeGoogle,
    control: Database,
    tenants: Tenants,
    acme: Org,
    pia: User,
    max_: User,
    team: int,
) -> None:
    eve = person(control, tenants, acme, "eve", "member")
    join(client, google, team, eve, "member", by=pia)
    board = make_board(client, team, "Secret")

    shown = restrict(client, team, board, [max_.id])

    assert shown.status_code == 200
    assert (shown.json()["restricted"], shown.json()["access"]) == (True, [max_.id])
    assert names(client, team) == ["Secret"]  # Pia, the project owner, is not listed
    as_(client, google, max_)
    assert names(client, team) == ["Secret"]
    assert client.get(f"{boards_of(team)}/{board}").json()["access"] is None  # owners only
    as_(client, google, eve)
    assert names(client, team) == []


def test_only_project_owners_restrict_a_board(
    client: TestClient, google: FakeGoogle, tenants: Tenants, max_: User, team: int
) -> None:
    as_(client, google, max_)
    board = make_board(client, team)

    assert restrict(client, team, board, [max_.id]).status_code == 403
    assert company_rows(tenants, "SELECT restricted FROM boards")[0][0] == 0


def test_a_restricted_board_lists_only_project_members(
    client: TestClient, google: FakeGoogle, boss: User, pia: User, team: int
) -> None:
    as_(client, google, pia)
    board = make_board(client, team)

    refused = restrict(client, team, board, [boss.id])

    assert refused.status_code == 422
    assert refused.json()["error"]["code"] == "NOT_A_PROJECT_MEMBER"


def test_opening_a_restricted_board_to_everyone_clears_its_list(
    client: TestClient, google: FakeGoogle, tenants: Tenants, pia: User, max_: User, team: int
) -> None:
    as_(client, google, pia)
    board = make_board(client, team)
    restrict(client, team, board, [max_.id])

    opened = write(
        client, "PUT", f"{boards_of(team)}/{board}/access", {"restricted": False, "people": []}
    )

    assert (opened.status_code, opened.json()["restricted"]) == (200, False)
    assert company_rows(tenants, "SELECT count(*) FROM board_access")[0][0] == 0


# --- changing boards and stars -----------------------------------------------------------------


def test_a_member_renames_and_closes_a_board_and_an_observer_cannot(
    client: TestClient,
    google: FakeGoogle,
    control: Database,
    tenants: Tenants,
    acme: Org,
    pia: User,
    max_: User,
    team: int,
) -> None:
    eve = person(control, tenants, acme, "eve", "member")
    join(client, google, team, eve, "observer", by=pia)
    board = make_board(client, team)
    path = f"{boards_of(team)}/{board}"
    as_(client, google, max_)

    renamed = write(client, "PATCH", path, {"name": "Sprint 2", "background": "rose"})
    closed = write(client, "PATCH", path, {"archived": True})

    assert (renamed.json()["name"], renamed.json()["background"]) == ("Sprint 2", "rose")
    assert closed.json()["archived_at"] is not None
    as_(client, google, eve)
    assert write(client, "PATCH", path, {"archived": False}).status_code == 403
    assert company_rows(tenants, "SELECT archived_at IS NOT NULL FROM boards")[0][0] == 1
    types = [
        r[0] for r in company_rows(tenants, "SELECT type FROM events WHERE board_id = ?", board)
    ]
    assert types == ["board.created", "board.updated", "board.archived"]


def test_stars_are_personal(
    client: TestClient, google: FakeGoogle, pia: User, max_: User, team: int
) -> None:
    board = make_board(client, team)
    as_(client, google, max_)

    assert write(client, "PUT", f"{boards_of(team)}/{board}/star").status_code == 204
    assert (
        write(client, "PUT", f"{boards_of(team)}/{board}/star").status_code == 204
    )  # twice is fine
    assert client.get(boards_of(team)).json()[0]["starred"] is True
    as_(client, google, pia)
    assert client.get(boards_of(team)).json()[0]["starred"] is False
    as_(client, google, max_)
    assert write(client, "DELETE", f"{boards_of(team)}/{board}/star").status_code == 204
    assert client.get(boards_of(team)).json()[0]["starred"] is False


def test_boards_of_an_archived_project_are_read_only(
    client: TestClient, google: FakeGoogle, boss: User, pia: User, launch: int
) -> None:
    as_(client, google, pia)
    board = make_board(client, launch)
    as_(client, google, boss)
    write(client, "PATCH", f"{BASE}/{launch}", {"archived": True})
    as_(client, google, pia)

    assert names(client, launch) == ["Sprint"]
    refused = write(client, "PATCH", f"{boards_of(launch)}/{board}", {"name": "X"})
    assert refused.status_code == 409
    assert refused.json()["error"]["code"] == "PROJECT_ARCHIVED"
    assert write(client, "POST", boards_of(launch), {"name": "New"}).status_code == 409
