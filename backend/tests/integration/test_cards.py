"""Lists and cards on a board over HTTP: adding, renaming, moving, archiving
and restoring them, and who may. Fixtures: conftest.py (boss, pia, max_,
launch); helpers: company.py."""

from __future__ import annotations

import json
from typing import Any

import pytest
from fastapi.testclient import TestClient

from tazko.db.tenant import Tenants
from tazko.modules.cards import repository as cards_repo
from tazko.modules.cards import service as cards_service
from tazko.modules.users.service import User
from tests.integration.company import BASE, as_, company_rows, join, write
from tests.integration.oidc import FakeGoogle


def board_path(project: int, board: int) -> str:
    return f"{BASE}/{project}/boards/{board}"


def make_board(client: TestClient, project: int, name: str = "Sprint") -> str:
    made = write(client, "POST", f"{BASE}/{project}/boards", {"name": name})
    assert made.status_code == 201, made.text
    return board_path(project, made.json()["id"])


def add_list(client: TestClient, board: str, name: str) -> int:
    made = write(client, "POST", f"{board}/lists", {"name": name})
    assert made.status_code == 201, made.text
    list_id: int = made.json()["id"]
    return list_id


def add_card(client: TestClient, board: str, list_id: int, title: str) -> int:
    made = write(client, "POST", f"{board}/lists/{list_id}/cards", {"title": title})
    assert made.status_code == 201, made.text
    card_id: int = made.json()["id"]
    return card_id


def layout(client: TestClient, board: str) -> list[tuple[str, list[str]]]:
    """The board as the screen draws it: lists in order, each with its cards in order."""
    got = client.get(f"{board}/lists")
    assert got.status_code == 200, got.text
    return [(lst["name"], [c["title"] for c in lst["cards"]]) for lst in got.json()]


def move_card(client: TestClient, board: str, card: int, list_id: int, after: int | None) -> Any:
    return write(
        client, "PUT", f"{board}/cards/{card}/position", {"list_id": list_id, "after_id": after}
    )


def event_types(tenants: Tenants) -> list[str]:
    return [r[0] for r in company_rows(tenants, "SELECT type FROM events ORDER BY id")]


@pytest.fixture
def board(client: TestClient, google: FakeGoogle, pia: User, max_: User, launch: int) -> str:
    """A board of Launch, where Max is a member; signed in as Max at the end."""
    join(client, google, launch, max_, "member", by=pia)
    path = make_board(client, launch)
    as_(client, google, max_)
    return path


# --- adding and reading -------------------------------------------------------------------


def test_a_member_adds_lists_and_cards_and_the_board_shows_them_in_order(
    client: TestClient, tenants: Tenants, board: str
) -> None:
    made = write(client, "POST", f"{board}/lists", {"name": " To do "})
    todo = made.json()["id"]
    doing = add_list(client, board, "Doing")
    card = write(client, "POST", f"{board}/lists/{todo}/cards", {"title": " Write the plan "})
    add_card(client, board, todo, "Ship it")
    add_card(client, board, doing, "Review")

    assert made.status_code == 201
    assert made.headers["location"] == f"{board}/lists/{todo}"
    assert (made.json()["name"], made.json()["cards"]) == ("To do", [])
    assert card.headers["location"] == f"{board}/cards/{card.json()['id']}"
    assert (card.json()["title"], card.json()["list_id"]) == ("Write the plan", todo)
    assert client.get(card.headers["location"]).json()["title"] == "Write the plan"
    assert layout(client, board) == [
        ("To do", ["Write the plan", "Ship it"]),
        ("Doing", ["Review"]),
    ]
    assert event_types(tenants)[-5:] == [
        "list.created",
        "list.created",
        "card.created",
        "card.created",
        "card.created",
    ]


@pytest.mark.parametrize(
    ("what", "body"),
    [
        ("list", {"name": "  "}),
        ("list", {"name": "x" * 101}),
        ("card", {"title": " "}),
        ("card", {"title": "x" * 513}),
    ],
)
def test_a_list_needs_a_name_and_a_card_a_title(
    client: TestClient, board: str, what: str, body: dict[str, Any]
) -> None:
    todo = add_list(client, board, "To do")
    path = f"{board}/lists" if what == "list" else f"{board}/lists/{todo}/cards"

    assert write(client, "POST", path, body).status_code == 422


def test_an_observer_reads_the_board_but_cannot_change_it(
    client: TestClient, google: FakeGoogle, tenants: Tenants, pia: User, max_: User, launch: int
) -> None:
    as_(client, google, pia)
    board = make_board(client, launch)
    todo = add_list(client, board, "To do")
    card = add_card(client, board, todo, "Plan")
    join(client, google, launch, max_, "observer", by=pia)
    as_(client, google, max_)
    events = len(event_types(tenants))

    assert layout(client, board) == [("To do", ["Plan"])]
    for method, path, body in [
        ("POST", f"{board}/lists", {"name": "Mine"}),
        ("POST", f"{board}/lists/{todo}/cards", {"title": "Mine"}),
        ("PATCH", f"{board}/lists/{todo}", {"name": "Mine"}),
        ("PATCH", f"{board}/cards/{card}", {"archived": True}),
        ("PUT", f"{board}/lists/{todo}/position", {"after_id": None}),
        ("PUT", f"{board}/cards/{card}/position", {"list_id": todo, "after_id": None}),
    ]:
        assert write(client, method, path, body).status_code == 403, (method, path)
    assert layout(client, board) == [("To do", ["Plan"])]
    assert len(event_types(tenants)) == events


# --- moving -------------------------------------------------------------------------------


def test_a_member_moves_a_card_within_its_list_and_to_another(
    client: TestClient, tenants: Tenants, board: str
) -> None:
    todo, done = add_list(client, board, "To do"), add_list(client, board, "Done")
    a, b, c = (add_card(client, board, todo, t) for t in "ABC")

    assert move_card(client, board, c, todo, None).status_code == 200
    assert layout(client, board) == [("To do", ["C", "A", "B"]), ("Done", [])]
    moved = move_card(client, board, a, done, None)
    assert moved.status_code == 200
    assert moved.json()["list_id"] == done
    assert move_card(client, board, b, done, a).status_code == 200

    assert layout(client, board) == [("To do", ["C"]), ("Done", ["A", "B"])]
    moves = company_rows(tenants, "SELECT payload FROM events WHERE type = 'card.moved'")
    payloads = [json.loads(row[0]) for row in moves]
    assert payloads[1] == {"card_id": a, "from_list": todo, "to_list": done, "after_id": None}


def test_a_member_moves_a_list(client: TestClient, tenants: Tenants, board: str) -> None:
    todo, doing, done = (add_list(client, board, n) for n in ("To do", "Doing", "Done"))

    first = write(client, "PUT", f"{board}/lists/{done}/position", {"after_id": None})
    middle = write(client, "PUT", f"{board}/lists/{todo}/position", {"after_id": doing})

    assert (first.status_code, middle.status_code) == (200, 200)
    assert [name for name, _ in layout(client, board)] == ["Done", "Doing", "To do"]
    assert event_types(tenants).count("list.moved") == 2


def test_moving_next_to_something_out_of_place_is_refused(
    client: TestClient, google: FakeGoogle, pia: User, launch: int, board: str
) -> None:
    todo, done = add_list(client, board, "To do"), add_list(client, board, "Done")
    a, b = add_card(client, board, todo, "A"), add_card(client, board, done, "B")
    as_(client, google, pia)
    other = make_board(client, launch, "Other")
    elsewhere = add_list(client, other, "Elsewhere")

    refusals = [
        move_card(client, board, a, todo, b),  # b is in another list
        move_card(client, board, a, todo, a),  # after itself
        move_card(client, board, a, elsewhere, None),  # a list of another board
        write(client, "PUT", f"{board}/lists/{todo}/position", {"after_id": todo}),
        write(client, "PUT", f"{board}/lists/{todo}/position", {"after_id": elsewhere}),
    ]

    assert [r.status_code for r in refusals] == [422] * 5
    assert layout(client, board) == [("To do", ["A"]), ("Done", ["B"])]


# --- renaming, archiving and restoring ----------------------------------------------------


def test_lists_and_cards_are_renamed_archived_and_restored_in_place(
    client: TestClient, tenants: Tenants, board: str
) -> None:
    todo, done = add_list(client, board, "To do"), add_list(client, board, "Done")
    a, b = add_card(client, board, todo, "A"), add_card(client, board, todo, "B")

    renamed = write(client, "PATCH", f"{board}/cards/{a}", {"title": "Alpha"})
    write(client, "PATCH", f"{board}/lists/{done}", {"name": "Shipped"})
    archived = write(client, "PATCH", f"{board}/cards/{b}", {"archived": True})
    write(client, "PATCH", f"{board}/lists/{todo}", {"archived": True})

    assert renamed.json()["title"] == "Alpha"
    assert archived.json()["archived_at"] is not None
    assert layout(client, board) == [("Shipped", [])]
    write(client, "PATCH", f"{board}/lists/{todo}", {"archived": False})
    assert layout(client, board) == [("To do", ["Alpha"]), ("Shipped", [])]
    write(client, "PATCH", f"{board}/cards/{b}", {"archived": False})
    assert layout(client, board) == [("To do", ["Alpha", "B"]), ("Shipped", [])]
    assert event_types(tenants)[-6:] == [
        "card.updated",
        "list.updated",
        "card.archived",
        "list.archived",
        "list.restored",
        "card.restored",
    ]


def test_archiving_twice_changes_nothing(client: TestClient, tenants: Tenants, board: str) -> None:
    todo = add_list(client, board, "To do")
    card = add_card(client, board, todo, "A")
    write(client, "PATCH", f"{board}/cards/{card}", {"archived": True})
    events = len(event_types(tenants))

    again = write(client, "PATCH", f"{board}/cards/{card}", {"archived": True})

    assert again.status_code == 200
    assert len(event_types(tenants)) == events


@pytest.mark.parametrize(
    ("what", "body"),
    [
        ("card", {"title": None}),
        ("card", {"name": "x"}),
        ("card", {"archived": None}),
        ("card", {}),
        ("list", {"name": None}),
        ("list", {"title": "x"}),
        ("list", {"archived": None}),
        ("list", {}),
    ],
)
def test_a_change_must_say_what_changes(
    client: TestClient, board: str, what: str, body: dict[str, Any]
) -> None:
    todo = add_list(client, board, "To do")
    card = add_card(client, board, todo, "A")
    path = f"{board}/cards/{card}" if what == "card" else f"{board}/lists/{todo}"

    assert write(client, "PATCH", path, body).status_code == 422


def test_renaming_to_the_same_name_writes_nothing(
    client: TestClient, tenants: Tenants, board: str
) -> None:
    todo = add_list(client, board, "To do")
    card = add_card(client, board, todo, "A")
    events = len(event_types(tenants))

    write(client, "PATCH", f"{board}/lists/{todo}", {"name": "To do"})
    write(client, "PATCH", f"{board}/cards/{card}", {"title": "A"})

    assert len(event_types(tenants)) == events


def test_a_move_counts_as_activity_on_the_card(
    client: TestClient, board: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    todo, done = add_list(client, board, "To do"), add_list(client, board, "Done")
    card = add_card(client, board, todo, "A")
    monkeypatch.setattr(cards_service, "now_iso", lambda: "2099-01-01T00:00:00Z")

    moved = move_card(client, board, card, done, None)

    assert moved.json()["updated_at"] == "2099-01-01T00:00:00Z"


def test_nothing_goes_into_an_archived_list_and_an_archived_card_stays_put(
    client: TestClient, board: str
) -> None:
    todo, old = add_list(client, board, "To do"), add_list(client, board, "Old")
    card, gone = add_card(client, board, todo, "A"), add_card(client, board, todo, "Gone")
    write(client, "PATCH", f"{board}/lists/{old}", {"archived": True})
    write(client, "PATCH", f"{board}/cards/{gone}", {"archived": True})

    into_list = write(client, "POST", f"{board}/lists/{old}/cards", {"title": "B"})
    moved_in = move_card(client, board, card, old, None)
    moved_out = move_card(client, board, gone, todo, None)

    assert [r.json()["error"]["code"] for r in (into_list, moved_in)] == ["LIST_ARCHIVED"] * 2
    assert (moved_out.status_code, moved_out.json()["error"]["code"]) == (409, "CARD_ARCHIVED")
    renamed = write(client, "PATCH", f"{board}/cards/{gone}", {"title": "Back"})
    assert renamed.json()["error"]["code"] == "CARD_ARCHIVED"
    restored = write(client, "PATCH", f"{board}/cards/{gone}", {"title": "Back", "archived": False})
    assert restored.json()["title"] == "Back"


def test_an_archived_list_keeps_its_cards_until_it_is_restored(
    client: TestClient, board: str
) -> None:
    """A stale screen cannot drag a hidden card back out, or move or rename the hidden list."""
    todo, old = add_list(client, board, "To do"), add_list(client, board, "Old")
    hidden = add_card(client, board, old, "Hidden")
    write(client, "PATCH", f"{board}/lists/{old}", {"archived": True})

    refusals = [
        move_card(client, board, hidden, todo, None),
        write(client, "PATCH", f"{board}/cards/{hidden}", {"title": "X"}),
        write(client, "PATCH", f"{board}/cards/{hidden}", {"archived": True}),
        write(client, "PUT", f"{board}/lists/{old}/position", {"after_id": None}),
        write(client, "PATCH", f"{board}/lists/{old}", {"name": "X"}),
    ]

    assert [(r.status_code, r.json()["error"]["code"]) for r in refusals] == [
        (409, "LIST_ARCHIVED")
    ] * 5
    assert layout(client, board) == [("To do", [])]
    write(client, "PATCH", f"{board}/lists/{old}", {"name": "Back", "archived": False})
    assert layout(client, board) == [("To do", []), ("Back", ["Hidden"])]


def test_a_move_never_goes_next_to_an_archived_row(client: TestClient, board: str) -> None:
    todo, old = add_list(client, board, "To do"), add_list(client, board, "Old")
    a, gone = add_card(client, board, todo, "A"), add_card(client, board, todo, "Gone")
    write(client, "PATCH", f"{board}/cards/{gone}", {"archived": True})
    write(client, "PATCH", f"{board}/lists/{old}", {"archived": True})

    after_card = move_card(client, board, a, todo, gone)
    after_list = write(client, "PUT", f"{board}/lists/{todo}/position", {"after_id": old})

    assert (after_card.status_code, after_list.status_code) == (422, 422)


def test_a_closed_board_and_an_archived_project_are_read_only(
    client: TestClient, google: FakeGoogle, boss: User, pia: User, launch: int, board: str
) -> None:
    todo = add_list(client, board, "To do")
    write(client, "PATCH", board, {"archived": True})

    closed = write(client, "POST", f"{board}/lists/{todo}/cards", {"title": "A"})

    assert (closed.status_code, closed.json()["error"]["code"]) == (409, "BOARD_CLOSED")
    write(client, "PATCH", board, {"archived": False})
    as_(client, google, boss)
    write(client, "PATCH", f"{BASE}/{launch}", {"archived": True})
    as_(client, google, pia)
    refused = write(client, "POST", f"{board}/lists", {"name": "B"})
    assert (refused.status_code, refused.json()["error"]["code"]) == (409, "PROJECT_ARCHIVED")
    assert layout(client, board) == [("To do", [])]


# --- who sees lists and cards -------------------------------------------------------------


def test_a_hidden_board_hides_its_lists_and_cards(
    client: TestClient, google: FakeGoogle, tenants: Tenants, pia: User, max_: User, launch: int
) -> None:
    """Restricted without Max on its list: every route answers 404, never 403."""
    join(client, google, launch, max_, "member", by=pia)
    secret = make_board(client, launch, "Secret")
    todo = add_list(client, secret, "To do")
    card = add_card(client, secret, todo, "A")
    write(client, "PUT", f"{secret}/access", {"restricted": True, "people": []})
    as_(client, google, max_)
    events = len(event_types(tenants))

    for method, path, body in [
        ("GET", f"{secret}/lists", None),
        ("GET", f"{secret}/cards/{card}", None),
        ("GET", f"{secret}/lists/{todo}", None),
        ("POST", f"{secret}/lists", {"name": "Mine"}),
        ("PATCH", f"{secret}/lists/{todo}", {"name": "Mine"}),
        ("PUT", f"{secret}/lists/{todo}/position", {"after_id": None}),
        ("POST", f"{secret}/lists/{todo}/cards", {"title": "Mine"}),
        ("PATCH", f"{secret}/cards/{card}", {"title": "Mine"}),
        ("PUT", f"{secret}/cards/{card}/position", {"list_id": todo, "after_id": None}),
    ]:
        assert write(client, method, path, body).status_code == 404, (method, path)
    assert len(event_types(tenants)) == events


def test_a_list_or_card_answers_only_under_its_own_board(
    client: TestClient, google: FakeGoogle, pia: User, launch: int, board: str
) -> None:
    todo = add_list(client, board, "To do")
    card = add_card(client, board, todo, "A")
    as_(client, google, pia)
    other = make_board(client, launch, "Other")

    assert client.get(f"{other}/cards/{card}").status_code == 404
    assert client.get(f"{other}/lists/{todo}").status_code == 404
    assert write(client, "PATCH", f"{other}/lists/{todo}", {"name": "X"}).status_code == 404
    assert write(client, "POST", f"{other}/lists/{todo}/cards", {"title": "X"}).status_code == 404


# --- caps ---------------------------------------------------------------------------------


def test_a_board_holds_a_bounded_number_of_open_lists_and_cards(
    client: TestClient, board: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(cards_repo, "OPEN_LISTS_CAP", 2)
    monkeypatch.setattr(cards_repo, "OPEN_CARDS_CAP", 2)
    todo, done = add_list(client, board, "To do"), add_list(client, board, "Done")
    add_card(client, board, todo, "A")
    b = add_card(client, board, done, "B")

    lists_full = write(client, "POST", f"{board}/lists", {"name": "Third"})
    cards_full = write(client, "POST", f"{board}/lists/{todo}/cards", {"title": "C"})
    write(client, "PATCH", f"{board}/cards/{b}", {"archived": True})
    room_again = write(client, "POST", f"{board}/lists/{todo}/cards", {"title": "C"})
    restore = write(client, "PATCH", f"{board}/cards/{b}", {"archived": False})

    assert (lists_full.status_code, lists_full.json()["error"]["code"]) == (409, "TOO_MANY_LISTS")
    assert (cards_full.status_code, cards_full.json()["error"]["code"]) == (409, "TOO_MANY_CARDS")
    assert room_again.status_code == 201
    assert restore.json()["error"]["code"] == "TOO_MANY_CARDS"
    write(client, "PATCH", f"{board}/lists/{done}", {"archived": True})
    add_list(client, board, "Third")
    list_back = write(client, "PATCH", f"{board}/lists/{done}", {"archived": False})
    assert (list_back.status_code, list_back.json()["error"]["code"]) == (409, "TOO_MANY_LISTS")
