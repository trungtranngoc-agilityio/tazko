"""The Google client: the two HTTP calls and the key cache, with a fake network."""

from __future__ import annotations

import io
import json
from typing import Any
from urllib.error import URLError
from urllib.parse import parse_qs, urlsplit
from urllib.request import Request

import pytest

from tazko.modules.auth.google import GoogleProvider, ProviderError


class FakeNetwork:
    def __init__(self, *answers: Any) -> None:
        self.answers = list(answers)
        self.requests: list[Request] = []

    def __call__(self, request: Request, timeout: float) -> io.BytesIO:
        self.requests.append(request)
        answer = self.answers.pop(0)
        if isinstance(answer, Exception):
            raise answer
        return io.BytesIO(json.dumps(answer).encode())


def provider(network: FakeNetwork) -> GoogleProvider:
    return GoogleProvider("client-1", "secret-1", opener=network)


def test_authorization_url_points_at_google_with_the_parameters() -> None:
    url = provider(FakeNetwork()).authorization_url({"state": "s", "scope": "openid email"})

    assert url.startswith("https://accounts.google.com/o/oauth2/v2/auth?")
    assert parse_qs(urlsplit(url).query) == {"state": ["s"], "scope": ["openid email"]}


def test_exchange_posts_the_code_and_verifier_and_returns_the_id_token() -> None:
    network = FakeNetwork({"id_token": "header.payload.sig", "access_token": "unused"})

    token = provider(network).exchange(code="c", code_verifier="v", redirect_uri="https://api/cb")

    assert token == "header.payload.sig"
    sent = network.requests[0]
    assert sent.full_url == "https://oauth2.googleapis.com/token"
    assert isinstance(sent.data, bytes)
    assert parse_qs(sent.data.decode()) == {
        "grant_type": ["authorization_code"],
        "code": ["c"],
        "code_verifier": ["v"],
        "redirect_uri": ["https://api/cb"],
        "client_id": ["client-1"],
        "client_secret": ["secret-1"],
    }


@pytest.mark.parametrize(
    "answer",
    [
        pytest.param(URLError("down"), id="network error"),
        pytest.param({"error": "invalid_grant"}, id="no id_token"),
    ],
)
def test_failed_exchange_raises_provider_error(answer: Any) -> None:
    with pytest.raises(ProviderError):
        provider(FakeNetwork(answer)).exchange(code="c", code_verifier="v", redirect_uri="r")


def test_keys_are_fetched_once_and_cached() -> None:
    network = FakeNetwork({"keys": [{"kid": "a"}]})
    google = provider(network)

    assert google.keys() == {"keys": [{"kid": "a"}]}
    assert google.keys() == {"keys": [{"kid": "a"}]}
    assert len(network.requests) == 1
    assert network.requests[0].full_url == "https://www.googleapis.com/oauth2/v3/certs"


def test_refresh_fetches_new_keys_at_most_once_a_minute() -> None:
    network = FakeNetwork({"keys": [{"kid": "a"}]}, {"keys": [{"kid": "b"}]})
    google = provider(network)
    google.keys()

    # a refresh right after a fetch keeps the cached keys
    assert google.keys(refresh=True) == {"keys": [{"kid": "a"}]}
    google.fetched_at -= 61
    assert google.keys(refresh=True) == {"keys": [{"kid": "b"}]}


def test_stale_keys_are_kept_when_google_cannot_be_reached() -> None:
    network = FakeNetwork({"keys": [{"kid": "a"}]}, URLError("down"))
    google = provider(network)
    google.keys()
    google.fetched_at -= 3601

    assert google.keys() == {"keys": [{"kid": "a"}]}


def test_unreachable_key_endpoint_raises_provider_error() -> None:
    with pytest.raises(ProviderError):
        provider(FakeNetwork(URLError("down"))).keys()
