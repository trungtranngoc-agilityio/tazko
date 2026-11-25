"""FastAPI dependencies shared by every module. Routers ask for what they need
through these annotations instead of reaching into `request.app.state`.

Database work blocks, so routes that use ControlDep, CurrentUser or
CompanyDep are plain `def` routes (FastAPI runs them in its thread pool),
never `async def`.
"""

from __future__ import annotations

import ipaddress
from typing import Annotated

from fastapi import Depends, Request, Response

from tazko.core.config import Settings
from tazko.core.cookies import set_cookie
from tazko.core.errors import Forbidden, Unauthorized
from tazko.db import Database
from tazko.modules.invites import projects as project_invites
from tazko.modules.orgs import service as orgs
from tazko.modules.orgs.console import Console
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


WRITE_METHODS = frozenset({"POST", "PUT", "PATCH", "DELETE"})


def require_same_origin(request: Request, settings: SettingsDep) -> None:
    """403 for a write whose Origin is not exactly TAZKO_WEB_ORIGIN, including
    a write with no Origin. SameSite=Lax still lets other sites send top-level
    POSTs, and lets sibling hosts under the same site send cookies.

    main.py installs this on the whole app, so every write route is checked
    without asking. Reads pass: CORS decides what another site may read.
    Never `app.mount` an API that writes: mounted apps skip app dependencies.
    """
    if request.method in WRITE_METHODS and request.headers.get("origin") != settings.web_origin:
        raise Forbidden("request from another origin")


def get_client_ip(request: Request) -> str | None:
    """The visitor's address. Behind the tunnel every request comes from
    loopback, so the address Cloudflare reports in CF-Connecting-IP is used.
    That header can be trusted only because nothing else reaches the server:
    TAZKO_HOST must be a loopback address (core/config.py). A header that is
    not exactly one IP address is ignored."""
    reported = request.headers.get("cf-connecting-ip", "").strip()
    try:
        return str(ipaddress.ip_address(reported))
    except ValueError:
        return request.client.host if request.client else None


ClientIp = Annotated[str | None, Depends(get_client_ip)]
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
    company = orgs.open_company(control, request.app.state.tenants, user_id=user.id, slug=slug)
    project_invites.use_project_invites(control, company, user)  # their pending project invites
    return company


CompanyDep = Annotated[Company, Depends(get_company)]


def get_console(user: CurrentUser, request: Request, control: ControlDep) -> Console:
    """The super admin console, or 403. modules/admin puts this on every route."""
    if not user.is_super_admin:
        raise Forbidden("super admins only")
    return Console(control, request.app.state.tenants, actor_id=user.id)


ConsoleDep = Annotated[Console, Depends(get_console)]


def get_console_company(slug: str, console: ConsoleDep) -> Company:
    """The company named by `{slug}`, opened for a super admin (not a member)."""
    return console.open(slug)


ConsoleCompanyDep = Annotated[Company, Depends(get_console_company)]


def get_started(request: Request) -> float:
    """When this server started, by time.monotonic()."""
    started: float = request.app.state.started
    return started


StartedDep = Annotated[float, Depends(get_started)]
