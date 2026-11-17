"""Short-lived values the server hands to the browser and reads back unchanged:
the sign-in state cookie and the refusal cookie.

A value is `<base64url JSON>.<base64url HMAC-SHA256>`. The HMAC key is derived
from the server secret and a purpose, so a value made for one cookie is never
accepted by another. The JSON carries its own expiry. Nothing in it is
encrypted: never put a secret the browser must not see in it.
"""

from __future__ import annotations

import base64
import binascii
import hashlib
import hmac
import json
from typing import Any

from tazko.core import clock


def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def _unb64(text: str) -> bytes:
    return base64.urlsafe_b64decode(text + "=" * (-len(text) % 4))


def _mac(secret: bytes, purpose: str, body: str) -> bytes:
    key = hmac.new(secret, f"tazko.signing.{purpose}".encode(), hashlib.sha256).digest()
    return hmac.new(key, body.encode(), hashlib.sha256).digest()


def sign(payload: dict[str, Any], secret: bytes, *, purpose: str, max_age: int) -> str:
    expires = int(clock.now().timestamp()) + max_age
    body = _b64(json.dumps({"v": payload, "exp": expires}, separators=(",", ":")).encode())
    return f"{body}.{_b64(_mac(secret, purpose, body))}"


def unsign(value: str, secret: bytes, *, purpose: str) -> dict[str, Any] | None:
    """The payload, or None when the value was changed, made for another
    purpose or secret, or has expired."""
    body, _, mac = value.partition(".")
    try:
        if not hmac.compare_digest(_unb64(mac), _mac(secret, purpose, body)):
            return None
        data = json.loads(_unb64(body))
    except (binascii.Error, ValueError):
        return None
    if not isinstance(data, dict) or not isinstance(data.get("exp"), int):
        return None
    if data["exp"] <= clock.now().timestamp():
        return None
    payload = data.get("v")
    return payload if isinstance(payload, dict) else None
