"""The HTTP contract every module relies on: health, error shape, CORS."""

from fastapi.testclient import TestClient
from httpx2 import Response

from tests.conftest import WEB_ORIGIN


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
    assert response.json() == {"error": "not found"}


def test_wrong_method_uses_the_same_error_shape(client: TestClient) -> None:
    response = client.post("/health")
    assert response.status_code == 405
    assert set(response.json()) == {"error"}


def test_cors_allows_the_web_origin_with_credentials(client: TestClient) -> None:
    headers = preflight(client, WEB_ORIGIN).headers
    assert headers["access-control-allow-origin"] == WEB_ORIGIN
    assert headers["access-control-allow-credentials"] == "true"


def test_cors_ignores_other_origins(client: TestClient) -> None:
    headers = preflight(client, "https://evil.example.net").headers
    assert "access-control-allow-origin" not in headers
