"""Company invites: made for one email, valid 14 days, used once, accepted at
sign-in (M1-05). Sign-in runs against the fake Google in oidc.py."""

from __future__ import annotations

import json
from datetime import timedelta
from typing import Any

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from tazko.core import clock
from tazko.core.deps import CompanyDep
from tazko.core.errors import Conflict, Invalid, NotFound
from tazko.db import Database
from tazko.db.tenant import Tenants
from tazko.modules.invites import service as invites
from tazko.modules.orgs import service as orgs
from tazko.modules.orgs.service import Org
from tests.integration.oidc import WEB, FakeGoogle, audit, sign_in

BO: dict[str, Any] = {"sub": "sub-bo", "email": "bo@example.com", "name": "Bo"}


@pytest.fixture
def tenants(client: TestClient) -> Tenants:
    found: Tenants = client.app.state.tenants  # type: ignore[attr-defined]  # TestClient.app is typed as ASGIApp
    return found


@pytest.fixture
def acme(control: Database, tenants: Tenants) -> Org:
    return orgs.create_company(control, tenants, slug="acme", name="Acme", actor_id=None)


def member_role(control: Database, org: Org, email: str) -> str | None:
    row = control.read(
        lambda c: c.execute(
            "SELECT m.role FROM org_members m JOIN users u ON u.id = m.user_id"
            " WHERE m.org_id = ? AND u.email = ?",
            (org.id, email),
        ).fetchone()
    )
    return str(row["role"]) if row else None


def user_count(control: Database) -> int:
    return int(control.read(lambda c: c.execute("SELECT count(*) FROM users").fetchone()[0]))


def refusal_reasons(control: Database) -> list[str]:
    return [json.loads(row["detail"])["reason"] for row in audit(control, "signin.refused")]


# --- making invites ------------------------------------------------------------------


def test_invite_expires_14_days_after_it_is_made(control: Database, acme: Org) -> None:
    invite = invites.create_invite(
        control, org=acme, email="Bo@Example.com", role="member", actor_id=None
    )

    assert invite.email == "bo@example.com"
    made = invites.parse_time(invite.created_at)
    assert invites.parse_time(invite.expires_at) - made == timedelta(days=14)
    assert [(r["target"], r["org_id"]) for r in audit(control, "invite.created")] == [
        ("bo@example.com", acme.id)
    ]


def test_second_pending_invite_for_the_same_email_is_refused(control: Database, acme: Org) -> None:
    invites.create_invite(control, org=acme, email="bo@example.com", role="member", actor_id=None)

    with pytest.raises(Conflict) as err:
        invites.create_invite(
            control, org=acme, email="BO@example.com", role="owner", actor_id=None
        )
    assert err.value.code == "INVITE_PENDING"


@pytest.mark.parametrize(
    ("email", "role"), [("not-an-email", "member"), ("bo@example.com", "boss")]
)
def test_bad_invite_is_refused(control: Database, acme: Org, email: str, role: str) -> None:
    with pytest.raises(Invalid):
        invites.create_invite(control, org=acme, email=email, role=role, actor_id=None)  # type: ignore[arg-type]  # a bad role on purpose


def test_revoking_an_unknown_or_used_invite_is_not_found(control: Database, acme: Org) -> None:
    invite = invites.create_invite(
        control, org=acme, email="bo@example.com", role="member", actor_id=None
    )
    invites.revoke_invite(control, invite_id=invite.id, actor_id=None)

    with pytest.raises(NotFound):
        invites.revoke_invite(control, invite_id=invite.id, actor_id=None)
    with pytest.raises(NotFound):
        invites.revoke_invite(control, invite_id=9999, actor_id=None)


# --- accepting at sign-in -----------------------------------------------------------


def test_invited_person_signs_in_and_joins_the_company(
    client: TestClient, google: FakeGoogle, control: Database, acme: Org
) -> None:
    invites.create_invite(control, org=acme, email="bo@example.com", role="member", actor_id=None)

    response = sign_in(client, google, **BO)

    assert response.headers["location"] == f"{WEB}/"
    assert client.get("/api/me").json()["email"] == "bo@example.com"
    assert member_role(control, acme, "bo@example.com") == "member"
    accepted = audit(control, "invite.accepted")
    assert [(r["target"], r["org_id"]) for r in accepted] == [("bo@example.com", acme.id)]


def test_invited_person_finds_themselves_in_the_company_file(
    app: FastAPI, client: TestClient, google: FakeGoogle, control: Database, acme: Org
) -> None:
    @app.get("/api/orgs/{slug}/people")
    def people(company: CompanyDep) -> list[str]:
        return company.tenant.db.read(
            lambda c: [row["email"] for row in c.execute("SELECT email FROM people")]
        )

    invites.create_invite(control, org=acme, email="bo@example.com", role="member", actor_id=None)
    sign_in(client, google, **BO)

    assert client.get("/api/orgs/acme/people").json() == ["bo@example.com"]


def test_invite_a_moment_before_14_days_is_accepted(
    client: TestClient,
    google: FakeGoogle,
    control: Database,
    acme: Org,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    made = clock.now()
    invites.create_invite(control, org=acme, email="bo@example.com", role="member", actor_id=None)

    monkeypatch.setattr(clock, "now", lambda: made + timedelta(days=14, seconds=-5))
    sign_in(client, google, **BO)

    assert member_role(control, acme, "bo@example.com") == "member"


def test_expired_invite_is_refused(
    client: TestClient,
    google: FakeGoogle,
    control: Database,
    acme: Org,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    made = clock.now()
    invites.create_invite(control, org=acme, email="bo@example.com", role="member", actor_id=None)

    monkeypatch.setattr(clock, "now", lambda: made + timedelta(days=14, seconds=1))
    response = sign_in(client, google, **BO)

    assert response.headers["location"] == f"{WEB}/signin/refused"
    assert refusal_reasons(control) == ["invite_expired"]
    assert user_count(control) == 0


def test_revoked_invite_is_refused(
    client: TestClient, google: FakeGoogle, control: Database, acme: Org
) -> None:
    invite = invites.create_invite(
        control, org=acme, email="bo@example.com", role="member", actor_id=None
    )
    invites.revoke_invite(control, invite_id=invite.id, actor_id=None)

    response = sign_in(client, google, **BO)

    assert response.headers["location"] == f"{WEB}/signin/refused"
    assert refusal_reasons(control) == ["invite_revoked"]
    assert [r["target"] for r in audit(control, "invite.revoked")] == ["bo@example.com"]


def test_used_invite_cannot_be_used_twice(
    client: TestClient, google: FakeGoogle, control: Database, acme: Org
) -> None:
    # given Bo joined through the invite and was later taken out of the company
    invites.create_invite(control, org=acme, email="bo@example.com", role="member", actor_id=None)
    sign_in(client, google, **BO)
    control.write(lambda c: c.execute("DELETE FROM org_members WHERE org_id = ?", (acme.id,)))

    # when Bo signs in again
    sign_in(client, google, **BO)

    # then the used invite does not bring Bo back
    assert member_role(control, acme, "bo@example.com") is None
    assert len(audit(control, "invite.accepted")) == 1


def test_invites_from_two_companies_are_both_accepted(
    client: TestClient, google: FakeGoogle, control: Database, tenants: Tenants, acme: Org
) -> None:
    beta = orgs.create_company(control, tenants, slug="beta", name="Beta", actor_id=None)
    invites.create_invite(control, org=acme, email="bo@example.com", role="member", actor_id=None)
    invites.create_invite(control, org=beta, email="bo@example.com", role="owner", actor_id=None)

    sign_in(client, google, **BO)

    assert member_role(control, acme, "bo@example.com") == "member"
    assert member_role(control, beta, "bo@example.com") == "owner"


def test_existing_person_accepts_a_new_invite_at_the_next_sign_in(
    client: TestClient, google: FakeGoogle, control: Database, tenants: Tenants, acme: Org
) -> None:
    invites.create_invite(control, org=acme, email="bo@example.com", role="member", actor_id=None)
    sign_in(client, google, **BO)
    beta = orgs.create_company(control, tenants, slug="beta", name="Beta", actor_id=None)
    invites.create_invite(control, org=beta, email="bo@example.com", role="member", actor_id=None)

    sign_in(client, google, **BO)

    assert member_role(control, beta, "bo@example.com") == "member"


def test_accepting_never_changes_an_existing_role(
    client: TestClient, google: FakeGoogle, control: Database, acme: Org
) -> None:
    # given Bo is already an owner of Acme and an invite as member is pending
    invites.create_invite(control, org=acme, email="bo@example.com", role="owner", actor_id=None)
    sign_in(client, google, **BO)
    invites.create_invite(control, org=acme, email="bo@example.com", role="member", actor_id=None)

    sign_in(client, google, **BO)

    assert member_role(control, acme, "bo@example.com") == "owner"


def test_invite_does_not_let_a_disabled_person_in(
    client: TestClient, google: FakeGoogle, control: Database, acme: Org
) -> None:
    invites.create_invite(control, org=acme, email="bo@example.com", role="member", actor_id=None)
    sign_in(client, google, **BO)
    control.write(lambda c: c.execute("UPDATE users SET disabled_at = '2026-01-01T00:00:00.000Z'"))
    invites.create_invite(control, org=acme, email="bo@example.com", role="owner", actor_id=None)

    response = sign_in(client, google, **BO)

    assert response.headers["location"] == f"{WEB}/signin/refused"
    assert refusal_reasons(control) == ["disabled"]


def test_invite_of_a_suspended_company_is_not_accepted(
    client: TestClient, google: FakeGoogle, control: Database, acme: Org
) -> None:
    invites.create_invite(control, org=acme, email="bo@example.com", role="member", actor_id=None)
    control.write(lambda c: c.execute("UPDATE orgs SET status = 'suspended'"))

    response = sign_in(client, google, **BO)

    assert response.headers["location"] == f"{WEB}/signin/refused"
    assert refusal_reasons(control) == ["not_invited"]


# --- client address ---------------------------------------------------------------


def test_audit_log_stores_the_address_cloudflare_reports(
    client: TestClient, google: FakeGoogle, control: Database, acme: Org
) -> None:
    invites.create_invite(control, org=acme, email="bo@example.com", role="member", actor_id=None)

    sign_in(client, google, headers={"cf-connecting-ip": "203.0.113.7"}, **BO)

    assert [r["ip"] for r in audit(control, "invite.accepted")] == ["203.0.113.7"]
    sessions = control.read(lambda c: [r["ip"] for r in c.execute("SELECT ip FROM sessions")])
    assert sessions == ["203.0.113.7"]


@pytest.mark.parametrize("header", ["not-an-address", "203.0.113.7, 10.0.0.1", ""])
def test_unusable_cloudflare_address_falls_back_to_the_peer(
    client: TestClient, google: FakeGoogle, control: Database, header: str
) -> None:
    sign_in(client, google, headers={"cf-connecting-ip": header}, **BO)

    assert [r["ip"] for r in audit(control, "signin.refused")] == ["testclient"]
