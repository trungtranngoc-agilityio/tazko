"""The one place that reads the time, so tests can move it (invite expiry, sessions)."""

from __future__ import annotations

from datetime import UTC, datetime


def now() -> datetime:
    return datetime.now(UTC)


def iso(moment: datetime) -> str:
    """UTC ISO 8601 with milliseconds and Z; sorts as text."""
    return (
        moment.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%S.") + f"{moment.microsecond // 1000:03d}Z"
    )


def now_iso() -> str:
    return iso(now())
