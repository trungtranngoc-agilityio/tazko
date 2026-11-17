"""FastAPI dependencies shared by every module. Routers ask for what they need
through these annotations instead of reaching into `request.app.state`.

Database work blocks, so routes that use ControlDep, CurrentUser or
CompanyDep are plain `def` routes (FastAPI runs them in its thread pool),
never `async def`.

TODO(M1-05): apply SameOrigin to every write route and the WebSocket handshake.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends, Request, Response

from tazko.core.config import Settings
from tazko.core.cookies import set_cookie
from tazko.core.errors import Forbidden, Unauthorized
from tazko.db import Database
from tazko.modules.orgs import service as orgs
from tazko.modules.orgs.service import Company
from tazko.modules.users.service import User


def get_settings(request: Request) -> Settings:
    settings: Settings = request.app.state.settings
    return settings


def get_control(request: Request) -> Database:
    control: Database = request.app.state.control
    return control


def get_secret(request: Request) -> bytes:
    secret: bytes = request.app.state.secret
    return secret


SettingsDep = Annotated[Settings, Depends(get_settings)]


def require_same_origin(request: Request, settings: SettingsDep) -> None:
    """403 unless the request's Origin is exactly TAZKO_WEB_ORIGIN. A missing
    Origin is refused too. SameSite=Lax still lets other sites send top-level
    POSTs, and lets sibling hosts under the same site send cookies."""
    if request.headers.get("origin") != settings.web_origin:
        raise Forbidden("request from another origin")


SameOrigin = Depends(require_same_origin)
ControlDep = Annotated[Database, Depends(get_control)]
SecretDep = Annotated[bytes, Depends(get_secret)]


def get_current_user(request: Request, response: Response, control: ControlDep) -> User:
    """The person of the session cookie, or 401. Sessions of disabled people
    and expired sessions count as no session."""
    # Imported here: the auth module's router imports this file.
    from tazko.modules.auth import service as auth

    token = request.cookies.get(auth.SESSION_COOKIE)
    found = auth.current_user(control, token) if token else None
    if found is None:
        raise Unauthorized()
    user, extended = found
    if extended and token:
        set_cookie(response, auth.SESSION_COOKIE, token, max_age=auth.SESSION_DAYS * 86400)
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def get_company(slug: str, user: CurrentUser, request: Request, control: ControlDep) -> Company:
    """The company named by the path's `{slug}`, opened for the signed-in
    person. Not a member, suspended or unknown: 404.

    The only route to a company's file. There is deliberately no dependency
    for the company cache itself; tests/unit/test_architecture.py guards this.
    """
    return orgs.open_company(control, request.app.state.tenants, user_id=user.id, slug=slug)


CompanyDep = Annotated[Company, Depends(get_company)]
