"""A fake Google for sign-in tests, and helpers that drive the sign-in flow.

The fake signs real RS256 ID tokens with a test key and checks the PKCE
verifier, so the server's own checks all run for real.
"""

from __future__ import annotations

import base64
import hashlib
import json
import sqlite3
import time
from collections.abc import Mapping
from typing import Any
from urllib.parse import parse_qs, urlsplit

import jwt
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi.testclient import TestClient
from httpx2 import Response
from jwt.algorithms import RSAAlgorithm

from tazko.db import Database
from tazko.modules.auth.google import ProviderError

WEB = "https://tazko.example.com"
API = "https://testserver"
CLIENT_ID = "client-123.apps.googleusercontent.com"
SAME_ORIGIN = {"origin": WEB}


class FakeGoogle:
    """Hands out one code per authorization; the code turns into an ID token
    with the nonce the server sent, unless a test overrides claims."""

    def __init__(self, key: rsa.RSAPrivateKey) -> None:
        self.key = key
        self.codes: dict[str, tuple[str, dict[str, Any]]] = {}
        public = json.loads(RSAAlgorithm.to_jwk(key.public_key()))
        self.jwks = {"keys": [{**public, "kid": "k1", "alg": "RS256", "use": "sig"}]}

    def authorization_url(self, params: Mapping[str, str]) -> str:
        return "https://accounts.google.test/o/oauth2/v2/auth?" + "&".join(
            f"{k}={v}" for k, v in params.items()
        )

    def authorize(self, location: str, **claims: Any) -> str:
        params = {k: v[0] for k, v in parse_qs(urlsplit(location).query).items()}
        now = int(time.time())
        token_claims = {
            "iss": "https://accounts.google.com",
            "aud": CLIENT_ID,
            "sub": "sub-ana",
            "email": "ana@example.com",
            "email_verified": True,
            "name": "Ana",
            "picture": "https://lh3.googleusercontent.com/a/ana",
            "iat": now,
            "exp": now + 3600,
            "nonce": params["nonce"],
            **claims,
        }
        code = f"code-{len(self.codes)}"
        self.codes[code] = (params["code_challenge"], token_claims)
        return code

    def exchange(self, *, code: str, code_verifier: str, redirect_uri: str) -> str:
        assert redirect_uri == f"{API}/auth/google/callback"
        if code not in self.codes:
            raise ProviderError("unknown code")
        challenge, claims = self.codes.pop(code)
        digest = hashlib.sha256(code_verifier.encode()).digest()
        if base64.urlsafe_b64encode(digest).rstrip(b"=").decode() != challenge:
            raise ProviderError("PKCE verifier does not match")
        claims = {k: v for k, v in claims.items() if v is not None}
        return jwt.encode(claims, self.key, algorithm="RS256", headers={"kid": "k1"})

    def keys(self, *, refresh: bool = False) -> dict[str, Any]:
        return self.jwks


def sign_in(
    client: TestClient,
    google: FakeGoogle,
    *,
    headers: Mapping[str, str] | None = None,
    **claims: Any,
) -> Response:
    start = client.get("/auth/google/start")
    assert start.status_code == 302
    code = google.authorize(start.headers["location"], **claims)
    state = parse_qs(urlsplit(start.headers["location"]).query)["state"][0]
    return client.get(
        "/auth/google/callback", params={"code": code, "state": state}, headers=headers
    )


def audit(control: Database, action: str) -> list[sqlite3.Row]:
    return control.read(
        lambda c: c.execute(
            "SELECT target, detail, actor_id, org_id, ip FROM audit_log WHERE action = ?",
            (action,),
        ).fetchall()
    )


def session_count(control: Database) -> int:
    return int(control.read(lambda c: c.execute("SELECT count(*) FROM sessions").fetchone()[0]))
