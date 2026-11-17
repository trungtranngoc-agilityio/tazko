"""Google sign-in (OIDC authorization code flow with PKCE) and sessions.

1. `start_sign_in` makes a fresh state, nonce and PKCE verifier, kept in a
   signed cookie for 10 minutes, and the Google URL to send the browser to.
2. `finish_sign_in` checks the state against that cookie, exchanges the code
   (with the verifier), verifies the ID token's signature against Google's
   keys plus audience, issuer, expiry and nonce, and requires a verified email.
3. The account is matched to a person (users.service.match_google_account).
   No person, or a disabled one: refused and audit-logged. Otherwise a new
   random session token is issued and any session the browser had is deleted.

Sessions last 30 days from last use. The token is never stored, only its SHA-256.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import secrets
import sqlite3
from dataclasses import dataclass
from datetime import timedelta

import jwt

from tazko.core import clock
from tazko.core.signing import sign, unsign
from tazko.db import Database
from tazko.modules.audit import service as audit
from tazko.modules.auth import repository as repo
from tazko.modules.auth.google import ISSUERS, IdentityProvider, ProviderError
from tazko.modules.users import service as users
from tazko.modules.users.service import GoogleAccount, Refused, User

SESSION_COOKIE = "__Host-tazko_session"
FLOW_COOKIE = "__Host-tazko_signin"
REFUSAL_COOKIE = "__Host-tazko_refused"
SESSION_DAYS = 30
FLOW_SECONDS = 600
REFUSAL_SECONDS = 600
# A session's end moves out on use, but is written at most this often.
TOUCH_AFTER = timedelta(hours=1)
CLOCK_SKEW_SECONDS = 60


class SignInFailed(Exception):
    """The sign-in could not be trusted or finished (state, token, Google).
    The person sees "try again"; the reason goes to the log only."""


@dataclass(frozen=True)
class SignInStart:
    url: str
    flow_cookie: str


@dataclass(frozen=True)
class SignedIn:
    user: User
    token: str


@dataclass(frozen=True)
class Refusal:
    email: str
    reason: str


def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def _hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def start_sign_in(
    provider: IdentityProvider, *, client_id: str, redirect_uri: str, secret: bytes
) -> SignInStart:
    state = secrets.token_urlsafe(32)
    nonce = secrets.token_urlsafe(32)
    verifier = secrets.token_urlsafe(64)
    url = provider.authorization_url(
        {
            "response_type": "code",
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "scope": "openid email profile",
            "state": state,
            "nonce": nonce,
            "code_challenge": _b64(hashlib.sha256(verifier.encode()).digest()),
            "code_challenge_method": "S256",
            "prompt": "select_account",
        }
    )
    flow = {"state": state, "nonce": nonce, "verifier": verifier}
    return SignInStart(url, sign(flow, secret, purpose="signin", max_age=FLOW_SECONDS))


def finish_sign_in(
    control: Database,
    provider: IdentityProvider,
    *,
    flow_cookie: str | None,
    code: str | None,
    state: str | None,
    client_id: str,
    redirect_uri: str,
    secret: bytes,
    old_token: str | None,
    ip: str | None,
    user_agent: str | None,
) -> SignedIn | Refusal:
    flow = unsign(flow_cookie, secret, purpose="signin") if flow_cookie else None
    if flow is None:
        raise SignInFailed("no valid sign-in cookie (expired, replayed or another browser)")
    if not code or not state or not hmac.compare_digest(state, str(flow.get("state"))):
        raise SignInFailed("state does not match")
    try:
        id_token = provider.exchange(
            code=code, code_verifier=str(flow["verifier"]), redirect_uri=redirect_uri
        )
    except ProviderError as err:
        raise SignInFailed(f"code exchange: {err}") from None
    account = verify_id_token(provider, id_token, client_id=client_id, nonce=str(flow["nonce"]))

    def run(conn: sqlite3.Connection) -> SignedIn | Refusal:
        match = users.match_google_account(conn, account, ip=ip)
        if isinstance(match, Refused):
            audit.record(
                conn,
                "signin.refused",
                actor_id=None,
                target=account.email,
                detail={"reason": match.reason},
                ip=ip,
            )
            return Refusal(account.email, match.reason)
        if old_token:
            repo.delete_session(conn, _hash(old_token))
        token = secrets.token_urlsafe(32)
        now = clock.now()
        repo.insert_session(
            conn,
            token_hash=_hash(token),
            user_id=match.id,
            now=clock.iso(now),
            expires_at=clock.iso(now + timedelta(days=SESSION_DAYS)),
            ip=ip,
            user_agent=user_agent[:300] if user_agent else None,
        )
        return SignedIn(match, token)

    return control.write(run)


def verify_id_token(
    provider: IdentityProvider, token: str, *, client_id: str, nonce: str
) -> GoogleAccount:
    try:
        key = _signing_key(provider, jwt.get_unverified_header(token).get("kid"))
        claims = jwt.decode(
            token,
            key,
            algorithms=["RS256"],
            audience=client_id,
            issuer=ISSUERS,
            leeway=CLOCK_SKEW_SECONDS,
            options={"require": ["iss", "aud", "exp", "iat", "sub", "nonce"]},
        )
    except jwt.PyJWTError as err:
        raise SignInFailed(f"ID token: {err}") from None
    if not hmac.compare_digest(str(claims["nonce"]), nonce):
        raise SignInFailed("ID token: nonce does not match")
    if claims.get("email_verified") is not True:
        raise SignInFailed("ID token: email not verified")
    email = claims.get("email")
    if not isinstance(email, str) or not email:
        raise SignInFailed("ID token: no email")
    picture = claims.get("picture")
    hd = claims.get("hd")
    return GoogleAccount(
        sub=str(claims["sub"]),
        email=email[:254],
        name=str(claims.get("name") or "")[:200],
        avatar_url=picture if isinstance(picture, str) and picture.startswith("https://") else None,
        hd=hd[:253] if isinstance(hd, str) else None,
    )


def _signing_key(provider: IdentityProvider, kid: object) -> jwt.PyJWK:
    """The key the token names; refetch once in case Google rotated its keys."""
    for refresh in (False, True):
        try:
            key_set = jwt.PyJWKSet.from_dict(provider.keys(refresh=refresh))
        except ProviderError as err:
            raise SignInFailed(f"signing keys: {err}") from None
        for key in key_set.keys:
            if key.key_id == kid:
                return key
    raise SignInFailed("ID token: signed by an unknown key")


def refusal_cookie(refusal: Refusal, secret: bytes) -> str:
    return sign({"email": refusal.email}, secret, purpose="refused", max_age=REFUSAL_SECONDS)


def refused_email(cookie: str | None, secret: bytes) -> str | None:
    value = unsign(cookie, secret, purpose="refused") if cookie else None
    email = value.get("email") if value else None
    return email if isinstance(email, str) else None


def current_user(control: Database, token: str) -> tuple[User, bool] | None:
    """The signed-in person, and whether the session's end was just moved out
    (the cookie should then be sent again)."""
    token_hash = _hash(token)
    now = clock.now()
    found = control.read(lambda c: repo.session_user(c, token_hash, now=clock.iso(now)))
    if found is None:
        return None
    user, last_used_at = found
    if last_used_at > clock.iso(now - TOUCH_AFTER):
        return user, False
    control.write(
        lambda c: repo.touch_session(
            c,
            token_hash,
            now=clock.iso(now),
            expires_at=clock.iso(now + timedelta(days=SESSION_DAYS)),
        )
    )
    return user, True


def sign_out(control: Database, token: str | None) -> None:
    if token:
        control.write(lambda c: repo.delete_session(c, _hash(token)))
