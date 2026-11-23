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
from tazko.db.tenant import Tenants
from tazko.main import create_app
from tazko.modules.auth.google import get_provider
from tazko.modules.orgs import service as orgs
from tazko.modules.orgs.service import Org
from tazko.modules.users.service import User
from tests.integration.company import BASE, as_, person, write
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


# --- a company with people, for the project and board tests (M2-02) -----------------
# test_members.py and others define their own `tenants` and `acme`; theirs win there.


@pytest.fixture
def tenants(client: TestClient) -> Tenants:
    found: Tenants = client.app.state.tenants  # type: ignore[attr-defined]  # TestClient.app is typed as ASGIApp
    return found


@pytest.fixture
def acme(control: Database, tenants: Tenants) -> Org:
    return orgs.create_company(control, tenants, slug="acme", name="Acme", actor_id=None)


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


@pytest.fixture
def launch(client: TestClient, google: FakeGoogle, boss: User, pia: User) -> int:
    """Project "Launch", made by the company owner with Pia as its owner."""
    as_(client, google, boss)
    made = write(client, "POST", BASE, {"name": "Launch", "owner_id": pia.id})
    assert made.status_code == 201, made.text
    project_id: int = made.json()["id"]
    return project_id
