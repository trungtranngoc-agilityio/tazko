"""Fixtures for unit tests that need a real company file."""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest

from tazko.db import Database


@pytest.fixture
def company(tmp_path: Path) -> Iterator[Database]:
    """An empty, migrated company file (data/orgs/<slug>/tazko.db)."""
    db = Database(tmp_path / "tazko.db", "tenant")
    try:
        yield db
    finally:
        db.close()
