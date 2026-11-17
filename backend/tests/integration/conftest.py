"""Fixtures for API tests: an app wired to the fake Google, served at API."""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi import FastAPI
from fastapi.testclient import TestClient

from tazko.core.config import Settings, load_settings
from tazko.db import Database
from tazko.main import create_app
from tazko.modules.auth.google import get_provider
from tests.integration.oidc import API, CLIENT_ID, WEB, FakeGoogle


@pytest.fixture(scope="module")
def private_key() -> rsa.RSAPrivateKey:
    return rsa.generate_private_key(public_exponent=65537, key_size=2048)


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    return load_settings(
        web_origin=WEB, public_url=API, data_dir=tmp_path / "data", google_client_id=CLIENT_ID
    )


@pytest.fixture
def google(private_key: rsa.RSAPrivateKey) -> FakeGoogle:
    return FakeGoogle(private_key)


@pytest.fixture
def app(settings: Settings, google: FakeGoogle) -> FastAPI:
    app = create_app(settings)
    app.dependency_overrides[get_provider] = lambda: google
    return app


@pytest.fixture
def client(app: FastAPI) -> Iterator[TestClient]:
    with TestClient(app, base_url=API, follow_redirects=False) as test_client:
        yield test_client


@pytest.fixture
def control(client: TestClient) -> Database:
    db: Database = client.app.state.control  # type: ignore[attr-defined]  # TestClient.app is typed as ASGIApp
    return db
