"""The one way to set and clear cookies. Every Tazko cookie is host-only on the
API host (no Domain, `__Host-` names), HttpOnly, Secure and SameSite=Lax:
web and API are same-site (D13), and the Google callback is a top-level
navigation, which Lax still sends cookies with.

Browsers treat http://localhost as secure, so Secure cookies also work in
development through the Vite proxy.
"""

from __future__ import annotations

from starlette.responses import Response


def set_cookie(response: Response, name: str, value: str, *, max_age: int) -> None:
    response.set_cookie(
        name, value, max_age=max_age, path="/", secure=True, httponly=True, samesite="lax"
    )


def clear_cookie(response: Response, name: str) -> None:
    response.delete_cookie(name, path="/", secure=True, httponly=True, samesite="lax")
