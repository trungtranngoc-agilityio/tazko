"""The two calls to Google: exchange the code for an ID token, and fetch the
keys that sign ID tokens. Stdlib HTTP only; both run in route threads.

Tests replace the provider through FastAPI's dependency overrides
(`app.dependency_overrides[get_provider]`), so no test reaches Google.
"""

from __future__ import annotations

import json
import logging
import threading
import time
from collections.abc import Callable, Mapping
from typing import Any, BinaryIO, Protocol
from urllib.error import URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from fastapi import Request as HttpRequest

log = logging.getLogger(__name__)

AUTHORIZE_URL = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_URL = "https://oauth2.googleapis.com/token"  # noqa: S105 (a URL, not a password)
KEYS_URL = "https://www.googleapis.com/oauth2/v3/certs"
ISSUERS = ("https://accounts.google.com", "accounts.google.com")
TIMEOUT = 10.0
KEYS_MAX_AGE = 3600.0
# Google rotates keys, so an unknown key id triggers one refetch, but at most
# this often: a stream of bad tokens cannot turn into a stream of requests.
KEYS_MIN_REFRESH = 60.0

Opener = Callable[..., BinaryIO]


class ProviderError(Exception):
    """Google could not be reached or did not answer as expected."""


class IdentityProvider(Protocol):
    def authorization_url(self, params: Mapping[str, str]) -> str: ...

    def exchange(self, *, code: str, code_verifier: str, redirect_uri: str) -> str:
        """The ID token (a JWT, not yet verified) for an authorization code."""
        ...

    def keys(self, *, refresh: bool = False) -> dict[str, Any]:
        """The JSON Web Key Set that signs ID tokens."""
        ...


class GoogleProvider:
    def __init__(self, client_id: str, client_secret: str, *, opener: Opener = urlopen) -> None:
        self.client_id = client_id
        self._client_secret = client_secret
        self._open = opener
        self._lock = threading.Lock()
        self._keys: dict[str, Any] | None = None
        self.fetched_at = 0.0

    def authorization_url(self, params: Mapping[str, str]) -> str:
        return f"{AUTHORIZE_URL}?{urlencode(params)}"

    def exchange(self, *, code: str, code_verifier: str, redirect_uri: str) -> str:
        form = urlencode(
            {
                "grant_type": "authorization_code",
                "code": code,
                "code_verifier": code_verifier,
                "redirect_uri": redirect_uri,
                "client_id": self.client_id,
                "client_secret": self._client_secret,
            }
        ).encode()
        request = Request(TOKEN_URL, data=form, method="POST")
        request.add_header("Content-Type", "application/x-www-form-urlencoded")
        token = self._json(request).get("id_token")
        if not isinstance(token, str):
            raise ProviderError("token endpoint answered without an id_token")
        return token

    def keys(self, *, refresh: bool = False) -> dict[str, Any]:
        with self._lock:
            age = time.monotonic() - self.fetched_at
            stale = age > KEYS_MAX_AGE
            if self._keys is None or stale or (refresh and age > KEYS_MIN_REFRESH):
                try:
                    self._keys = self._json(Request(KEYS_URL))
                except ProviderError:
                    # Keys rotate slowly: an hour-old set beats no sign-in at all.
                    if self._keys is None:
                        raise
                    log.warning("Google keys unreachable; using the cached ones")
                self.fetched_at = time.monotonic()
            return self._keys

    def _json(self, request: Request) -> dict[str, Any]:
        try:
            with self._open(request, timeout=TIMEOUT) as response:
                data = json.loads(response.read())
        except (URLError, OSError, ValueError) as err:
            # HTTPError is a URLError; its body may hold the reason but never
            # anything the person needs to see.
            raise ProviderError(f"{request.full_url}: {err}") from None
        if not isinstance(data, dict):
            raise ProviderError(f"{request.full_url}: not a JSON object")
        return data


def get_provider(request: HttpRequest) -> IdentityProvider:
    provider: IdentityProvider = request.app.state.identity_provider
    return provider
