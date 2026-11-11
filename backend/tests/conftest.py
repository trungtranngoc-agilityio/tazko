"""Shared fixtures. Tests never see the developer's .env or TAZKO_* variables."""

from __future__ import annotations

import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from tazko.core.config import Settings, load_settings
from tazko.main import create_app

WEB_ORIGIN = "https://tazko.example.com"


@pytest.fixture(autouse=True)
def isolated_env(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    for key in list(os.environ):
        if key.startswith("TAZKO_"):
            monkeypatch.delenv(key)
    monkeypatch.chdir(tmp_path)  # no .env here


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    return load_settings(web_origin=WEB_ORIGIN, data_dir=tmp_path / "data")


@pytest.fixture
def client(settings: Settings) -> TestClient:
    return TestClient(create_app(settings))
