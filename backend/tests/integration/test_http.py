"""The HTTP contract every module relies on: health, error shape, CORS."""

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from httpx2 import Response
from pydantic import BaseModel, Field

from tazko.core.config import Settings
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

    with TestClient(app, raise_server_exceptions=False) as test_client:
        yield test_client


def test_invalid_body_is_422_with_one_detail_per_field(app_with_routes: TestClient) -> None:
    response = app_with_routes.post("/test/things", json={"name": "", "size": "big"})
    assert response.status_code == 422
    error = response.json()["error"]
    assert error["code"] == "VALIDATION_ERROR"
    assert {d["field"] for d in error["details"]} == {"name", "size"}


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
