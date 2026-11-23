"""Fractional ranks: keys between two neighbours, even spreads, and moves that rebalance."""

from __future__ import annotations

import random
import re
import sqlite3
from functools import partial

import pytest

from tazko.db import Database
from tazko.db.rank import MAX_LENGTH, at_end, between, move, spread
from tests.unit.tenant_rows import add_board, add_card, add_list, add_person, card_order, ranks

KEY = re.compile(r"^[0-9A-Za-z]*[1-9A-Za-z]$")


def test_a_key_between_two_neighbours_sorts_between_them() -> None:
    rng = random.Random(7)  # noqa: S311 (a fixed seed for repeatable tests)
    keys = sorted(set(spread(50)))
    for _ in range(500):
        lo, hi = sorted(rng.sample(keys, 2))
        key = between(lo, hi)
        assert lo < key < hi
        assert KEY.match(key)
        keys = sorted({*keys, key})


def test_open_ends_give_a_first_and_a_last_key() -> None:
    first = between(None, None)
    assert KEY.match(first)
    assert between(None, first) < first < between(first, None)


def test_a_key_right_below_a_neighbour_with_a_low_digit_is_valid() -> None:
    # "1" leaves no digit below it at the same length: the key gets longer.
    key = between(None, "1")
    assert key < "1"
    assert KEY.match(key)
    assert between("0V", "1") > "0V"


@pytest.mark.parametrize(("lo", "hi"), [("b", "b"), ("c", "b")])
def test_neighbours_out_of_order_are_refused(lo: str, hi: str) -> None:
    with pytest.raises(ValueError, match="before"):
        between(lo, hi)


@pytest.mark.parametrize("bad", ["", "a0", "a-b", "x" * (MAX_LENGTH + 1)])
def test_a_malformed_neighbour_is_refused(bad: str) -> None:
    with pytest.raises(ValueError, match="rank"):
        between(bad, None)


@pytest.mark.parametrize("n", [0, 1, 2, 61, 62, 1000, 5000])
def test_a_spread_is_sorted_unique_and_short(n: int) -> None:
    keys = spread(n)
    assert len(keys) == n
    assert keys == sorted(keys)
    assert len(set(keys)) == n
    assert all(KEY.match(key) and len(key) <= 3 for key in keys)


def board_with_cards(db: Database, lists: int, cards: int) -> list[int]:
    def seed(conn: sqlite3.Connection) -> list[int]:
        add_person(conn)
        board = add_board(conn)
        ids = [add_list(conn, board, f"List {n}") for n in range(lists)]
        for list_id in ids:
            for n in range(cards):
                add_card(conn, list_id, f"Card {n}")
        return ids

    return db.write(seed)


def assert_well_ranked(conn: sqlite3.Connection, list_ids: list[int]) -> None:
    for list_id in list_ids:
        found = ranks(conn, "cards", "list_id", list_id)
        assert len(found) == len(set(found)), f"rank collision in list {list_id}"
        assert all(len(key) < MAX_LENGTH for key in found)


def test_moving_200_cards_at_random_keeps_order_and_unique_short_ranks(
    company: Database,
) -> None:
    lists = board_with_cards(company, lists=3, cards=40)
    order = {i: company.read(partial(card_order, list_id=i)) for i in lists}
    rng = random.Random(2026)  # noqa: S311 (a fixed seed for repeatable tests)

    for _ in range(200):
        source = rng.choice([i for i in lists if order[i]])
        card = rng.choice(order[source])
        target = rng.choice(lists)
        order[source].remove(card)
        slot = rng.randint(0, len(order[target]))
        after = order[target][slot - 1] if slot else None
        order[target].insert(slot, card)
        company.write(partial(move, kind="card", item_id=card, scope_id=target, after_id=after))

    def check(conn: sqlite3.Connection) -> None:
        assert {i: card_order(conn, i) for i in lists} == order
        assert_well_ranked(conn, lists)

    company.read(check)


def test_moving_200_cards_into_the_same_gap_rebalances_and_keeps_order(
    company: Database,
) -> None:
    # The worst case: every move lands between the same two cards, so each
    # new key is longer than the last until the list is spread again.
    (list_id,) = board_with_cards(company, lists=1, cards=202)
    order = company.read(lambda c: card_order(c, list_id))
    longest = 0
    for _ in range(200):
        card = order.pop()
        order.insert(1, card)
        company.write(partial(move, kind="card", item_id=card, scope_id=list_id, after_id=order[0]))
        longest = max(
            longest, *map(len, company.read(lambda c: ranks(c, "cards", "list_id", list_id)))
        )

    assert company.read(lambda c: card_order(c, list_id)) == order
    company.read(lambda c: assert_well_ranked(c, [list_id]))
    assert longest < MAX_LENGTH


def test_adding_500_cards_at_the_end_keeps_ranks_short(company: Database) -> None:
    (list_id,) = board_with_cards(company, lists=1, cards=500)
    company.read(lambda c: assert_well_ranked(c, [list_id]))
    titles = company.read(
        lambda c: [r[0] for r in c.execute("SELECT title FROM cards ORDER BY rank, id").fetchall()]
    )
    assert titles == [f"Card {n}" for n in range(500)]


def test_moving_a_list_changes_only_its_place_on_the_board(company: Database) -> None:
    def seed(conn: sqlite3.Connection) -> tuple[int, list[int]]:
        add_person(conn)
        board = add_board(conn)
        return board, [add_list(conn, board, name) for name in ("A", "B", "C", "D")]

    board, (a, _b, _c, d) = company.write(seed)
    company.write(lambda conn: move(conn, "list", d, board, a))
    company.write(lambda conn: move(conn, "list", a, board, None))

    def names(conn: sqlite3.Connection) -> list[str]:
        rows = conn.execute("SELECT name FROM lists WHERE board_id = ? ORDER BY rank", (board,))
        return [r[0] for r in rows.fetchall()]

    assert company.read(names) == ["A", "D", "B", "C"]
    assert company.read(lambda conn: at_end(conn, "list", board)) > max(
        company.read(lambda conn: ranks(conn, "lists", "board_id", board))
    )


def test_moving_after_a_card_of_another_list_is_refused(company: Database) -> None:
    first, second = board_with_cards(company, lists=2, cards=2)
    card = company.read(lambda c: card_order(c, first))[0]
    elsewhere = company.read(lambda c: card_order(c, second))[0]

    with pytest.raises(LookupError):
        company.write(lambda c: move(c, "card", card, first, elsewhere))
    with pytest.raises(LookupError):
        company.write(lambda c: move(c, "card", card, first, card))


def test_moving_a_card_that_does_not_exist_is_refused(company: Database) -> None:
    (list_id,) = board_with_cards(company, lists=1, cards=1)
    with pytest.raises(LookupError):
        company.write(lambda c: move(c, "card", 999, list_id, None))
