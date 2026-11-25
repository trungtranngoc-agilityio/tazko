"""Every write must come from TAZKO_WEB_ORIGIN. SameSite=Lax still lets
sibling sites under the same domain send the cookie, so the server checks Origin
itself, on every route, not only the ones that remember to ask."""

from __future__ import annotations

from collections.abc import Iterable, Iterator

import pytest
from fastapi import FastAPI
from fastapi.routing import APIRoute
from fastapi.testclient import TestClient
from starlette.routing import BaseRoute

from tests.integration.oidc import WEB

WRITES = {"POST", "PUT", "PATCH", "DELETE"}
FOREIGN = ["https://evil.example", "https://other.example.com", "null", WEB + ".evil.example"]


def walk(routes: Iterable[BaseRoute], prefix: str = "") -> Iterator[tuple[str, APIRoute]]:
    """Every APIRoute with its full path. FastAPI keeps included routers as
    wrappers holding the original router, so this walks into them."""
    for route in routes:
        if isinstance(route, APIRoute):
            yield prefix + route.path, route
        inner = getattr(route, "original_router", None)
        if inner is not None:
            context = getattr(route, "include_context", None)
            yield from walk(inner.routes, prefix + getattr(context, "prefix", ""))


def write_routes(app: FastAPI) -> list[tuple[str, str]]:
    return [
        (method, path)
        for path, route in walk(app.routes)
        for method in sorted((route.methods or set()) & WRITES)
    ]


def test_the_app_has_write_routes_to_check(app: FastAPI) -> None:
    assert ("POST", "/auth/signout") in write_routes(app)


@pytest.mark.parametrize("origin", [*FOREIGN, None])
def test_every_write_route_refuses_a_foreign_or_missing_origin(
    app: FastAPI, client: TestClient, origin: str | None
) -> None:
    headers = {"origin": origin} if origin else {}
    for method, path in write_routes(app):
        response = client.request(method, path, headers=headers)
        assert response.status_code == 403, (method, path)
        assert response.json()["error"]["code"] == "FORBIDDEN"


@pytest.mark.parametrize("method", sorted(WRITES))
def test_a_new_write_route_is_checked_without_asking(
    app: FastAPI, client: TestClient, method: str
) -> None:
    app.add_api_route("/api/probe", lambda: {"ok": True}, methods=[method])

    assert (
        client.request(method, "/api/probe", headers={"origin": "https://evil.example"}).status_code
        == 403
    )
    assert client.request(method, "/api/probe").status_code == 403
    assert client.request(method, "/api/probe", headers={"origin": WEB}).json() == {"ok": True}


def test_reads_from_another_origin_are_not_refused(client: TestClient) -> None:
    # CORS decides what another site's page may read; the server still answers.
    assert client.get("/health", headers={"origin": "https://evil.example"}).status_code == 200
