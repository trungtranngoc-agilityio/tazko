"""The HTTP contract every module relies on: health, error shape, CORS."""

import os
import stat
from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from httpx2 import Response
from pydantic import BaseModel, Field

from tazko.core.config import Settings, load_settings
from tazko.core.errors import Conflict
from tazko.main import create_app
from tests.conftest import WEB_ORIGIN


def test_app_start_creates_the_control_database(client: TestClient, settings: Settings) -> None:
    assert client.get("/health").status_code == 200
    assert (settings.data_dir / "control.db").exists()


def preflight(client: TestClient, origin: str) -> Response:
    return client.options(
        "/health", headers={"origin": origin, "access-control-request-method": "POST"}
    )


def test_openapi_schema_is_not_served(client: TestClient) -> None:
    # The internal API is not published; /api/v1 gets its own document in M6-01.
    assert client.get("/openapi.json").status_code == 404


@pytest.mark.skipif(os.name == "nt", reason="POSIX file modes")
def test_data_folder_and_databases_are_private(client: TestClient, settings: Settings) -> None:
    client.get("/health")
    assert stat.S_IMODE(settings.data_dir.stat().st_mode) & 0o077 == 0
    assert stat.S_IMODE((settings.data_dir / "control.db").stat().st_mode) & 0o077 == 0


def test_health_returns_200(client: TestClient) -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_unknown_path_is_a_json_404(client: TestClient) -> None:
    response = client.get("/nope")
    assert response.status_code == 404
    assert response.json() == {
        "error": {"code": "NOT_FOUND", "message": "not found", "details": []}
    }


def test_wrong_method_uses_the_same_error_shape(client: TestClient) -> None:
    response = client.post("/health")
    assert response.status_code == 405
    assert response.json()["error"]["code"] == "METHOD_NOT_ALLOWED"
    assert set(response.json()["error"]) == {"code", "message", "details"}


class Thing(BaseModel):
    name: str = Field(min_length=1)
    size: int


@pytest.fixture
def app_with_routes(settings: Settings) -> Iterator[TestClient]:
    """The real app plus two routes that exercise the error handlers."""
    app = create_app(settings)

    @app.post("/test/things")
    def make_thing(thing: Thing) -> Thing:
        return thing

    @app.post("/test/conflict")
    def conflict() -> None:
        raise Conflict("slug: already taken", code="SLUG_TAKEN", field="slug")

    @app.get("/test/crash")
    def crash() -> None:
        raise RuntimeError("secret path /var/lib/tazko/data")

    # Writes must come from the web origin (M1-05).
    with TestClient(
        app, raise_server_exceptions=False, headers={"origin": settings.web_origin}
    ) as test_client:
        yield test_client


def test_invalid_body_is_422_with_one_detail_per_field(app_with_routes: TestClient) -> None:
    response = app_with_routes.post("/test/things", json={"name": "", "size": "big"})
    assert response.status_code == 422
    error = response.json()["error"]
    assert error["code"] == "VALIDATION_ERROR"
    assert {d["field"] for d in error["details"]} == {"name", "size"}


def test_malformed_json_is_400(app_with_routes: TestClient) -> None:
    response = app_with_routes.post(
        "/test/things", content=b'{"name": ', headers={"content-type": "application/json"}
    )
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "BAD_REQUEST"
    assert response.json()["error"]["details"] == []


def test_missing_body_is_400(app_with_routes: TestClient) -> None:
    response = app_with_routes.post("/test/things")
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "BAD_REQUEST"


def test_conflict_is_409_with_its_own_code(app_with_routes: TestClient) -> None:
    response = app_with_routes.post("/test/conflict")
    assert response.status_code == 409
    assert response.json()["error"] == {
        "code": "SLUG_TAKEN",
        "message": "slug: already taken",
        "details": [{"field": "slug", "message": "already taken"}],
    }


def test_unexpected_error_hides_its_message(app_with_routes: TestClient) -> None:
    response = app_with_routes.get("/test/crash")
    assert response.status_code == 500
    assert response.json()["error"]["code"] == "INTERNAL"
    assert "/var/lib" not in response.text


def test_cors_allows_the_web_origin_with_credentials(client: TestClient) -> None:
    headers = preflight(client, WEB_ORIGIN).headers
    assert headers["access-control-allow-origin"] == WEB_ORIGIN
    assert headers["access-control-allow-credentials"] == "true"


def test_cors_ignores_other_origins(client: TestClient) -> None:
    headers = preflight(client, "https://evil.example.net").headers
    assert "access-control-allow-origin" not in headers


def test_a_stand_in_google_is_announced_at_start(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    # a server that trusts a stand-in Google says so, so nobody mistakes it for a real one
    settings = load_settings(
        env="development", data_dir=tmp_path, google_url="http://127.0.0.1:8792"
    )

    with caplog.at_level("WARNING"):
        create_app(settings)

    assert "stand-in Google at http://127.0.0.1:8792" in caplog.text
