"""Sign-in routes on the API host. The browser is always sent back to
TAZKO_WEB_ORIGIN, never to an address taken from the request."""

from __future__ import annotations

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, Request, Response
from fastapi.responses import RedirectResponse

from tazko.core.cookies import clear_cookie, set_cookie
from tazko.core.deps import ControlDep, CurrentUser, SameOrigin, SecretDep, SettingsDep
from tazko.core.errors import NotFound
from tazko.modules.auth import service
from tazko.modules.auth.google import IdentityProvider, get_provider
from tazko.modules.auth.schemas import MeOut, RefusalOut

log = logging.getLogger(__name__)
router = APIRouter()

ProviderDep = Annotated[IdentityProvider, Depends(get_provider)]
CALLBACK_PATH = "/auth/google/callback"


@router.get("/auth/google/start")
def start(settings: SettingsDep, secret: SecretDep, provider: ProviderDep) -> RedirectResponse:
    begun = service.start_sign_in(
        provider,
        client_id=settings.google_client_id,
        redirect_uri=settings.api_url + CALLBACK_PATH,
        secret=secret,
    )
    response = RedirectResponse(begun.url, status_code=302)
    set_cookie(response, service.FLOW_COOKIE, begun.flow_cookie, max_age=service.FLOW_SECONDS)
    return response


@router.get(CALLBACK_PATH)
def callback(
    request: Request,
    settings: SettingsDep,
    control: ControlDep,
    secret: SecretDep,
    provider: ProviderDep,
    code: str | None = None,
    state: str | None = None,
    error: str | None = None,
) -> RedirectResponse:
    web = settings.web_origin
    try:
        if error:
            raise service.SignInFailed(f"Google answered {error[:60]!r}")
        result = service.finish_sign_in(
            control,
            provider,
            flow_cookie=request.cookies.get(service.FLOW_COOKIE),
            code=code,
            state=state,
            client_id=settings.google_client_id,
            redirect_uri=settings.api_url + CALLBACK_PATH,
            secret=secret,
            old_token=request.cookies.get(service.SESSION_COOKIE),
            ip=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
        )
    except service.SignInFailed as err:
        log.warning("sign-in failed: %s", err)
        response = RedirectResponse(f"{web}/signin?error=failed", status_code=302)
    else:
        if isinstance(result, service.SignedIn):
            response = RedirectResponse(f"{web}/", status_code=302)
            set_cookie(
                response,
                service.SESSION_COOKIE,
                result.token,
                max_age=service.SESSION_DAYS * 86400,
            )
        else:
            log.info("sign-in refused: %s", result.reason)
            response = RedirectResponse(f"{web}/signin/refused", status_code=302)
            set_cookie(
                response,
                service.REFUSAL_COOKIE,
                service.refusal_cookie(result, secret),
                max_age=service.REFUSAL_SECONDS,
            )
    # The state, nonce and verifier work once.
    clear_cookie(response, service.FLOW_COOKIE)
    return response


@router.get("/auth/refusal")
def refusal(request: Request, secret: SecretDep) -> RefusalOut:
    email = service.refused_email(request.cookies.get(service.REFUSAL_COOKIE), secret)
    if email is None:
        raise NotFound()
    return RefusalOut(email=email)


@router.post("/auth/signout", status_code=204, dependencies=[SameOrigin])
def sign_out(request: Request, control: ControlDep) -> Response:
    service.sign_out(control, request.cookies.get(service.SESSION_COOKIE))
    response = Response(status_code=204)
    clear_cookie(response, service.SESSION_COOKIE)
    return response


@router.get("/api/me")
def me(user: CurrentUser) -> MeOut:
    return MeOut(
        id=user.id,
        email=user.email,
        name=user.name,
        avatar_url=user.avatar_url,
        is_super_admin=user.is_super_admin,
    )
