"""Signed, short-lived values for cookies (sign-in state, refusal)."""

from __future__ import annotations

from datetime import timedelta

import pytest

from tazko.core import clock
from tazko.core.signing import sign, unsign

SECRET = b"s" * 32


def test_signed_value_reads_back() -> None:
    value = sign({"state": "abc"}, SECRET, purpose="signin", max_age=600)

    assert unsign(value, SECRET, purpose="signin") == {"state": "abc"}


@pytest.mark.parametrize(
    "tamper",
    [
        pytest.param(lambda v: "x" + v, id="body changed"),
        pytest.param(lambda v: v[:-2] + "AA", id="signature changed"),
        pytest.param(lambda v: v.replace(".", ""), id="no separator"),
        pytest.param(lambda v: "", id="empty"),
        pytest.param(lambda v: "%%%.%%%", id="not base64"),
    ],
)
def test_tampered_value_is_refused(tamper: object) -> None:
    value = sign({"state": "abc"}, SECRET, purpose="signin", max_age=600)

    assert unsign(tamper(value), SECRET, purpose="signin") is None  # type: ignore[operator]


def test_value_for_another_purpose_is_refused() -> None:
    value = sign({"email": "a@example.com"}, SECRET, purpose="refused", max_age=600)

    assert unsign(value, SECRET, purpose="signin") is None


def test_value_signed_with_another_secret_is_refused() -> None:
    value = sign({"state": "abc"}, b"t" * 32, purpose="signin", max_age=600)

    assert unsign(value, SECRET, purpose="signin") is None


def test_expired_value_is_refused(monkeypatch: pytest.MonkeyPatch) -> None:
    value = sign({"state": "abc"}, SECRET, purpose="signin", max_age=600)
    later = clock.now() + timedelta(seconds=601)
    monkeypatch.setattr(clock, "now", lambda: later)

    assert unsign(value, SECRET, purpose="signin") is None
