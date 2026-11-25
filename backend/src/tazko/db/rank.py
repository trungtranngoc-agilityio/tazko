"""Fractional ranks for ordered rows: lists on a board, cards in a list.

A rank is a base-62 fraction (0-9A-Za-z) that sorts as plain text and never
ends in "0". A move writes one row; when keys grow past REBALANCE_AT, the
list is spread again in the same transaction. No UNIQUE index is needed: all
writes run on the company's one writer thread, and a new key always sorts
strictly between two existing ones. Call only inside `Database.write`.
"""

from __future__ import annotations

import sqlite3
from typing import Literal

DIGITS = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"
BASE = len(DIGITS)
VALUE = {digit: value for value, digit in enumerate(DIGITS)}
MAX_LENGTH = 32  # the CHECK on lists.rank and cards.rank (tenant migration 0002)
REBALANCE_AT = 24  # a rebalance leaves keys of 3 characters for up to 238 000 rows

type Kind = Literal["list", "card"]

# Table and the column that groups its rows. SQL below is built only from these.
SCOPES: dict[Kind, tuple[str, str]] = {
    "list": ("lists", "board_id"),
    "card": ("cards", "list_id"),
}


def is_rank(key: str) -> bool:
    return 1 <= len(key) <= MAX_LENGTH and key[-1] != "0" and all(ch in VALUE for ch in key)


def between(lo: str | None, hi: str | None) -> str:
    """The shortest-ish key strictly between `lo` and `hi`. None is an open
    end: `between(None, x)` sorts before x, `between(x, None)` after it."""
    for key in (lo, hi):
        if key is not None and not is_rank(key):
            raise ValueError(f"not a rank: {key!r}")
    if lo is not None and hi is not None and lo >= hi:
        raise ValueError(f"{lo!r} must sort before {hi!r}")
    return _middle(lo or "", hi)


def _middle(lo: str, hi: str | None) -> str:
    # lo "" stands for 0 and hi None for 1; lo < hi and neither ends in "0".
    if hi is not None:
        # Keep the digits both share (lo padded with "0"), then split below them.
        shared = 0
        while shared < len(hi) and (lo[shared] if shared < len(lo) else "0") == hi[shared]:
            shared += 1
        if shared:
            return hi[:shared] + _middle(lo[shared:], hi[shared:])
    low = VALUE[lo[0]] if lo else 0
    high = VALUE[hi[0]] if hi is not None else BASE
    if high - low > 1:
        return DIGITS[(low + high) // 2]
    if hi is not None and len(hi) > 1:
        return hi[0]  # above lo's first digit, below hi itself
    # Neighbouring first digits: keep lo's and go above the rest of lo.
    return DIGITS[low] + _middle(lo[1:], None)


def spread(n: int) -> list[str]:
    """n sorted, unique keys spaced evenly over the whole range, as short as possible."""
    width = 1
    while BASE**width <= n:
        width += 1
    step = BASE**width // (n + 1)
    return [_digits((i + 1) * step, width).rstrip("0") for i in range(n)]


def _digits(value: int, width: int) -> str:
    out = []
    for _ in range(width):
        value, digit = divmod(value, BASE)
        out.append(DIGITS[digit])
    return "".join(reversed(out))


def at_end(conn: sqlite3.Connection, kind: Kind, scope_id: int) -> str:
    """The rank for a new row after every row of the list or board `scope_id`."""
    key = _after_last(conn, kind, scope_id)
    if len(key) > REBALANCE_AT:
        _respread(conn, kind, scope_id, skip=None)
        key = _after_last(conn, kind, scope_id)
    return key


def _after_last(conn: sqlite3.Connection, kind: Kind, scope_id: int) -> str:
    table, scope = SCOPES[kind]
    last = conn.execute(f"SELECT max(rank) FROM {table} WHERE {scope} = ?", (scope_id,))
    return between(last.fetchone()[0], None)


def move(
    conn: sqlite3.Connection, kind: Kind, item_id: int, scope_id: int, after_id: int | None
) -> str:
    """Put the row `item_id` into list or board `scope_id`, right after
    `after_id` (None: first). Raises LookupError when `after_id` is not
    another row of that scope or `item_id` does not exist. Returns the rank."""
    table, scope = SCOPES[kind]
    key = _slot(conn, kind, item_id, scope_id, after_id)
    if len(key) > REBALANCE_AT:
        _respread(conn, kind, scope_id, skip=item_id)
        key = _slot(conn, kind, item_id, scope_id, after_id)
    moved = conn.execute(
        f"UPDATE {table} SET {scope} = ?, rank = ? WHERE id = ?", (scope_id, key, item_id)
    )
    if moved.rowcount != 1:
        raise LookupError(f"no {kind} {item_id}")
    return key


def _slot(
    conn: sqlite3.Connection, kind: Kind, item_id: int, scope_id: int, after_id: int | None
) -> str:
    """A key right after `after_id` among the other rows of the scope."""
    table, scope = SCOPES[kind]
    lo: str | None = None
    if after_id is not None:
        row = conn.execute(
            f"SELECT rank FROM {table} WHERE id = ? AND {scope} = ? AND id != ?",
            (after_id, scope_id, item_id),
        ).fetchone()
        if row is None:
            raise LookupError(f"{kind} {after_id} is not another {kind} of {scope} {scope_id}")
        lo = row[0]
    # rank > lo, not >=: the next key up is strictly above lo, so between() holds.
    following = f"SELECT rank FROM {table} WHERE {scope} = ? AND id != ?"
    if lo is None:
        row = conn.execute(f"{following} ORDER BY rank LIMIT 1", (scope_id, item_id))
    else:
        row = conn.execute(
            f"{following} AND rank > ? ORDER BY rank LIMIT 1", (scope_id, item_id, lo)
        )
    hi = row.fetchone()
    return between(lo, hi[0] if hi else None)


def _respread(conn: sqlite3.Connection, kind: Kind, scope_id: int, *, skip: int | None) -> None:
    """Give every row of the scope but `skip` an evenly spaced rank, keeping the order."""
    table, scope = SCOPES[kind]
    ids = [
        row[0]
        for row in conn.execute(
            f"SELECT id FROM {table} WHERE {scope} = ? AND id IS NOT ? ORDER BY rank, id",
            (scope_id, skip),
        )
    ]
    conn.executemany(
        f"UPDATE {table} SET rank = ? WHERE id = ?", zip(spread(len(ids)), ids, strict=True)
    )
