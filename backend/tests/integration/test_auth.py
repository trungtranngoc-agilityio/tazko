"""Google sign-in, sessions and sign-out, against a fake Google (M1-04).

The fake signs real RS256 ID tokens with a test key and checks the PKCE
verifier, so the server's own checks (signature, audience, issuer, expiry,
nonce, state, email_verified) all run for real.
"""

from __future__ import annotations

import hashlib
import json
import time
from datetime import timedelta
from typing import Any
from urllib.parse import parse_qs, urlsplit

import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi import FastAPI
from fastapi.testclient import TestClient

from tazko.core import clock
from tazko.core.deps import CompanyDep
from tazko.db import Database
from tazko.modules.auth.service import SESSION_COOKIE
from tazko.modules.orgs import service as orgs
from tazko.modules.users import service as users
from tests.integration.oidc import (
    API,
    CLIENT_ID,
    SAME_ORIGIN,
    WEB,
    FakeGoogle,
    audit,
    session_count,
    sign_in,
)

# --- start -----------------------------------------------------------------------


def test_start_sends_the_browser_to_google_with_pkce(client: TestClient) -> None:
    response = client.get("/auth/google/start")

    assert response.status_code == 302
    params = parse_qs(urlsplit(response.headers["location"]).query)
    assert params["client_id"] == [CLIENT_ID]
    assert params["redirect_uri"] == [f"{API}/auth/google/callback"]
    assert params["response_type"] == ["code"]
    assert params["scope"] == ["openid email profile"]
    assert params["code_challenge_method"] == ["S256"]
    assert params["prompt"] == ["select_account"]
    assert len(params["state"][0]) >= 32 and len(params["nonce"][0]) >= 32
    flow_cookie = response.headers["set-cookie"]
    assert "HttpOnly" in flow_cookie and "Secure" in flow_cookie and "Domain" not in flow_cookie


def test_every_start_uses_a_new_state_and_nonce(client: TestClient) -> None:
    first = parse_qs(urlsplit(client.get("/auth/google/start").headers["location"]).query)
    second = parse_qs(urlsplit(client.get("/auth/google/start").headers["location"]).query)

    assert first["state"] != second["state"]
    assert first["nonce"] != second["nonce"]
    assert first["code_challenge"] != second["code_challenge"]


# --- signing in ------------------------------------------------------------------


def test_personal_account_with_a_person_signs_in(
    client: TestClient, google: FakeGoogle, control: Database
) -> None:
    # given a person made by `tazko admin`, who has no Google sub yet
    users.grant_super_admin(control, "ana@example.com", actor_id=None)

    # when Ana signs in with her Gmail account
    response = sign_in(client, google)

    # then she lands on the web app with a session cookie
    assert response.status_code == 302
    assert response.headers["location"] == f"{WEB}/"
    session_cookie = next(
        c for c in response.headers.get_list("set-cookie") if c.startswith(SESSION_COOKIE)
    )
    assert "HttpOnly" in session_cookie
    assert "Secure" in session_cookie
    assert "SameSite=lax" in session_cookie
    assert "Path=/" in session_cookie
    assert "Domain" not in session_cookie
    me = client.get("/api/me")
    assert me.status_code == 200
    assert me.json() == {
        "id": me.json()["id"],
        "email": "ana@example.com",
        "name": "Ana",
        "avatar_url": "https://lh3.googleusercontent.com/a/ana",
        "is_super_admin": True,
    }


def test_workspace_account_signs_in_and_keeps_its_domain(
    client: TestClient, google: FakeGoogle, control: Database
) -> None:
    users.get_or_create(control, "bo@acme.example", name="")

    response = sign_in(client, google, sub="sub-bo", email="bo@acme.example", hd="acme.example")

    assert response.headers["location"] == f"{WEB}/"
    stored = control.read(
        lambda c: c.execute(
            "SELECT google_sub, hd FROM users WHERE email = 'bo@acme.example'"
        ).fetchone()
    )
    assert (stored["google_sub"], stored["hd"]) == ("sub-bo", "acme.example")


def test_personal_account_cannot_take_a_workspace_persons_row(
    client: TestClient, google: FakeGoogle, control: Database
) -> None:
    # given acme.example is a Workspace (Ana signed in with it) and Bo was made by
    # `tazko admin`, so Bo's row has no Google account yet
    users.get_or_create(control, "ana@acme.example")
    sign_in(client, google, sub="sub-ana", email="ana@acme.example", hd="acme.example")
    client.cookies.clear()
    users.get_or_create(control, "bo@acme.example")

    # when a personal Google account on Bo's address signs in
    response = sign_in(client, google, sub="sub-ghost", email="bo@acme.example")

    # then it is refused and Bo's row stays unlinked
    assert response.headers["location"] == f"{WEB}/signin/refused"
    assert [json.loads(r["detail"]) for r in audit(control, "signin.refused")] == [
        {"reason": "workspace_required"}
    ]
    stored = control.read(
        lambda c: c.execute(
            "SELECT google_sub FROM users WHERE email = 'bo@acme.example'"
        ).fetchone()
    )
    assert stored["google_sub"] is None


def test_session_token_is_stored_only_as_a_hash(
    client: TestClient, google: FakeGoogle, control: Database
) -> None:
    users.get_or_create(control, "ana@example.com")

    sign_in(client, google)

    token = client.cookies[SESSION_COOKIE]
    stored = control.read(lambda c: c.execute("SELECT token_hash FROM sessions").fetchone())
    assert stored["token_hash"] == hashlib.sha256(token.encode()).hexdigest()
    assert len(token) >= 43  # 32 random bytes


def test_account_with_no_person_is_refused_and_logged(
    client: TestClient, google: FakeGoogle, control: Database
) -> None:
    response = sign_in(client, google, email="jo.lee@gmail.com", sub="sub-jo")

    assert response.status_code == 302
    assert response.headers["location"] == f"{WEB}/signin/refused"
    assert SESSION_COOKIE not in client.cookies
    assert session_count(control) == 0
    rows = audit(control, "signin.refused")
    assert [(r["target"], json.loads(r["detail"])) for r in rows] == [
        ("jo.lee@gmail.com", {"reason": "not_invited"})
    ]
    # the refusal page can show which account was refused
    assert client.get("/auth/refusal").json() == {
        "email": "jo.lee@gmail.com",
        "reason": "not_invited",
    }
    assert control.read(lambda c: c.execute("SELECT count(*) FROM users").fetchone()[0]) == 0


def test_refusal_page_without_a_refusal_gets_404(client: TestClient) -> None:
    assert client.get("/auth/refusal").status_code == 404


def test_disabled_person_is_refused(
    client: TestClient, google: FakeGoogle, control: Database
) -> None:
    ana = users.get_or_create(control, "ana@example.com")
    control.write(lambda c: c.execute("UPDATE users SET disabled_at = 'x' WHERE id = ?", (ana.id,)))

    response = sign_in(client, google)

    assert response.headers["location"] == f"{WEB}/signin/refused"
    assert [json.loads(r["detail"]) for r in audit(control, "signin.refused")] == [
        {"reason": "disabled"}
    ]


def test_disabled_person_with_a_linked_account_is_refused(
    client: TestClient, google: FakeGoogle, control: Database
) -> None:
    ana = users.get_or_create(control, "ana@example.com")
    sign_in(client, google)
    client.post("/auth/signout", headers=SAME_ORIGIN)
    control.write(lambda c: c.execute("UPDATE users SET disabled_at = 'x' WHERE id = ?", (ana.id,)))

    response = sign_in(client, google)

    assert response.headers["location"] == f"{WEB}/signin/refused"
    assert [json.loads(r["detail"]) for r in audit(control, "signin.refused")] == [
        {"reason": "disabled"}
    ]
    assert session_count(control) == 0


@pytest.mark.parametrize(
    "claims",
    [
        pytest.param({"email_verified": False}, id="email not verified"),
        pytest.param({"email_verified": None}, id="email_verified missing"),
        pytest.param({"aud": "someone-else.apps.googleusercontent.com"}, id="wrong audience"),
        pytest.param({"iss": "https://evil.example"}, id="wrong issuer"),
        pytest.param({"nonce": "not-the-nonce-we-sent"}, id="wrong nonce"),
        pytest.param({"exp": int(time.time()) - 3600}, id="expired"),
    ],
)
def test_bad_id_token_is_refused(
    client: TestClient, google: FakeGoogle, control: Database, claims: dict[str, Any]
) -> None:
    users.get_or_create(control, "ana@example.com")

    response = sign_in(client, google, **claims)

    assert response.headers["location"] == f"{WEB}/signin?error=failed"
    assert SESSION_COOKIE not in client.cookies
    assert session_count(control) == 0


def test_token_signed_by_another_key_is_refused(
    client: TestClient, google: FakeGoogle, control: Database
) -> None:
    users.get_or_create(control, "ana@example.com")
    google.key = rsa.generate_private_key(public_exponent=65537, key_size=2048)

    response = sign_in(client, google)

    assert response.headers["location"] == f"{WEB}/signin?error=failed"
    assert session_count(control) == 0


def test_bad_state_is_refused(client: TestClient, google: FakeGoogle, control: Database) -> None:
    users.get_or_create(control, "ana@example.com")
    start = client.get("/auth/google/start")
    code = google.authorize(start.headers["location"])

    response = client.get("/auth/google/callback", params={"code": code, "state": "forged"})

    assert response.headers["location"] == f"{WEB}/signin?error=failed"
    assert session_count(control) == 0


def test_non_ascii_state_is_refused_not_a_crash(
    client: TestClient, google: FakeGoogle, control: Database
) -> None:
    start = client.get("/auth/google/start")
    code = google.authorize(start.headers["location"])

    response = client.get("/auth/google/callback", params={"code": code, "state": "été"})

    assert response.headers["location"] == f"{WEB}/signin?error=failed"
    assert session_count(control) == 0


def test_over_long_email_is_refused_not_cut_to_match_someone(
    client: TestClient, google: FakeGoogle, control: Database
) -> None:
    # given a person whose address is the first 254 characters of a longer one
    victim = "a" * 242 + "@example.com"  # 254, the longest allowed
    users.get_or_create(control, victim)

    response = sign_in(client, google, sub="sub-long", email=victim + "x")

    assert response.headers["location"] == f"{WEB}/signin/refused"
    assert session_count(control) == 0


def test_callback_without_the_start_cookie_is_refused(
    client: TestClient, google: FakeGoogle, control: Database
) -> None:
    users.get_or_create(control, "ana@example.com")
    start = client.get("/auth/google/start")
    code = google.authorize(start.headers["location"])
    state = parse_qs(urlsplit(start.headers["location"]).query)["state"][0]
    client.cookies.clear()

    response = client.get("/auth/google/callback", params={"code": code, "state": state})

    assert response.headers["location"] == f"{WEB}/signin?error=failed"
    assert session_count(control) == 0


def test_start_cookie_works_only_once(
    client: TestClient, google: FakeGoogle, control: Database
) -> None:
    users.get_or_create(control, "ana@example.com")
    start = client.get("/auth/google/start")
    location = start.headers["location"]
    state = parse_qs(urlsplit(location).query)["state"][0]
    first = client.get(
        "/auth/google/callback", params={"code": google.authorize(location), "state": state}
    )
    assert first.headers["location"] == f"{WEB}/"

    replay = client.get(
        "/auth/google/callback", params={"code": google.authorize(location), "state": state}
    )

    assert replay.headers["location"] == f"{WEB}/signin?error=failed"


def test_google_error_is_refused(client: TestClient) -> None:
    client.get("/auth/google/start")

    response = client.get("/auth/google/callback", params={"error": "access_denied"})

    assert response.headers["location"] == f"{WEB}/signin?error=failed"


def test_code_exchange_failure_is_refused(client: TestClient, control: Database) -> None:
    users.get_or_create(control, "ana@example.com")
    start = client.get("/auth/google/start")
    state = parse_qs(urlsplit(start.headers["location"]).query)["state"][0]

    response = client.get("/auth/google/callback", params={"code": "never-issued", "state": state})

    assert response.headers["location"] == f"{WEB}/signin?error=failed"


# --- matching people ---------------------------------------------------------------


def test_person_found_by_sub_signs_in_after_an_email_change(
    client: TestClient, google: FakeGoogle, control: Database
) -> None:
    ana = users.get_or_create(control, "ana@example.com")
    sign_in(client, google)
    client.post("/auth/signout", headers=SAME_ORIGIN)

    response = sign_in(client, google, email="ana.new@example.com")

    assert response.headers["location"] == f"{WEB}/"
    me = client.get("/api/me").json()
    assert (me["id"], me["email"]) == (ana.id, "ana.new@example.com")


def test_email_is_not_moved_onto_an_address_another_person_has(
    client: TestClient, google: FakeGoogle, control: Database
) -> None:
    ana = users.get_or_create(control, "ana@example.com")
    users.get_or_create(control, "bo@example.com")
    sign_in(client, google)

    response = sign_in(client, google, email="bo@example.com")

    assert response.headers["location"] == f"{WEB}/"
    me = client.get("/api/me").json()
    assert (me["id"], me["email"]) == (ana.id, "ana@example.com")


def test_email_match_links_the_sub_once_and_logs_it(
    client: TestClient, google: FakeGoogle, control: Database
) -> None:
    users.get_or_create(control, "ana@example.com")

    sign_in(client, google)
    sign_in(client, google)

    assert [r["target"] for r in audit(control, "account.linked")] == ["ana@example.com"]


def test_email_match_never_relinks_a_person_who_has_a_sub(
    client: TestClient, google: FakeGoogle, control: Database
) -> None:
    # given Ana already linked to her Google account
    users.get_or_create(control, "ana@example.com")
    sign_in(client, google)
    client.post("/auth/signout", headers=SAME_ORIGIN)

    # when another Google account claiming the same email signs in
    response = sign_in(client, google, sub="sub-impostor")

    # then it is refused and Ana keeps her link
    assert response.headers["location"] == f"{WEB}/signin/refused"
    assert [json.loads(r["detail"]) for r in audit(control, "signin.refused")] == [
        {"reason": "account_mismatch"}
    ]
    stored = control.read(lambda c: c.execute("SELECT google_sub FROM users").fetchone())
    assert stored["google_sub"] == "sub-ana"


def test_email_is_matched_case_insensitively(
    client: TestClient, google: FakeGoogle, control: Database
) -> None:
    users.get_or_create(control, "ana@example.com")

    response = sign_in(client, google, email="Ana@Example.com")

    assert response.headers["location"] == f"{WEB}/"


# --- sessions ----------------------------------------------------------------------


def test_me_without_a_session_gets_401(client: TestClient) -> None:
    response = client.get("/api/me")

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "UNAUTHENTICATED"


def test_made_up_session_cookie_gets_401(client: TestClient) -> None:
    client.cookies.set(SESSION_COOKIE, "made-up")

    assert client.get("/api/me").status_code == 401


def test_sign_out_deletes_the_session_and_the_old_cookie_gets_401(
    client: TestClient, google: FakeGoogle, control: Database
) -> None:
    users.get_or_create(control, "ana@example.com")
    sign_in(client, google)
    old_token = client.cookies[SESSION_COOKIE]

    response = client.post("/auth/signout", headers=SAME_ORIGIN)

    assert response.status_code == 204
    assert session_count(control) == 0
    assert SESSION_COOKIE not in client.cookies
    client.cookies.set(SESSION_COOKIE, old_token)
    assert client.get("/api/me").status_code == 401


def test_sign_out_without_a_session_still_answers_204(client: TestClient) -> None:
    assert client.post("/auth/signout", headers=SAME_ORIGIN).status_code == 204


@pytest.mark.parametrize("origin", ["https://evil.example", "https://other.example.com", None])
def test_sign_out_from_another_origin_is_refused(
    client: TestClient, google: FakeGoogle, control: Database, origin: str | None
) -> None:
    users.get_or_create(control, "ana@example.com")
    sign_in(client, google)
    headers = {"origin": origin} if origin else {}

    response = client.post("/auth/signout", headers=headers)

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "FORBIDDEN"
    assert session_count(control) == 1


def test_signing_in_again_replaces_the_previous_session(
    client: TestClient, google: FakeGoogle, control: Database
) -> None:
    users.get_or_create(control, "ana@example.com")
    sign_in(client, google)
    first_token = client.cookies[SESSION_COOKIE]

    sign_in(client, google)

    assert client.cookies[SESSION_COOKIE] != first_token
    assert session_count(control) == 1
    client.cookies.clear()
    client.cookies.set(SESSION_COOKIE, first_token)
    assert client.get("/api/me").status_code == 401


def test_session_of_a_person_disabled_later_gets_401(
    client: TestClient, google: FakeGoogle, control: Database
) -> None:
    ana = users.get_or_create(control, "ana@example.com")
    sign_in(client, google)

    control.write(lambda c: c.execute("UPDATE users SET disabled_at = 'x' WHERE id = ?", (ana.id,)))

    assert client.get("/api/me").status_code == 401


def test_session_ends_30_days_after_last_use(
    client: TestClient, google: FakeGoogle, control: Database, monkeypatch: pytest.MonkeyPatch
) -> None:
    users.get_or_create(control, "ana@example.com")
    sign_in(client, google)
    start = clock.now()

    monkeypatch.setattr(clock, "now", lambda: start + timedelta(days=20))
    assert client.get("/api/me").status_code == 200  # use slides the end out

    monkeypatch.setattr(clock, "now", lambda: start + timedelta(days=45))
    assert client.get("/api/me").status_code == 200

    monkeypatch.setattr(clock, "now", lambda: start + timedelta(days=76))
    assert client.get("/api/me").status_code == 401


# --- companies ---------------------------------------------------------------------


def test_company_dependency_opens_only_the_signed_in_persons_companies(
    app: FastAPI, client: TestClient, google: FakeGoogle, control: Database
) -> None:
    @app.get("/api/orgs/{slug}/probe")
    def probe(company: CompanyDep) -> dict[str, str]:
        return {"slug": company.org.slug, "role": company.role}

    tenants = client.app.state.tenants  # type: ignore[attr-defined]  # TestClient.app is typed as ASGIApp
    acme = orgs.create_company(control, tenants, slug="acme", name="Acme", actor_id=None)
    orgs.create_company(control, tenants, slug="beta", name="Beta", actor_id=None)
    ana = users.get_or_create(control, "ana@example.com")
    orgs.add_member(control, tenants, org=acme, user=ana, role="owner", actor_id=None)

    assert client.get("/api/orgs/acme/probe").status_code == 401
    sign_in(client, google)
    assert client.get("/api/orgs/acme/probe").json() == {"slug": "acme", "role": "owner"}
    assert client.get("/api/orgs/beta/probe").status_code == 404
    assert client.get("/api/orgs/nope/probe").status_code == 404
