"""Company invites: made for one email, valid 14 days, used once, accepted at
sign-in. Sign-in runs against the fake Google in oidc.py."""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timedelta
from typing import Any

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from tazko.core import clock
from tazko.core.deps import CompanyDep
from tazko.core.errors import Conflict, Forbidden, Invalid, NotFound
from tazko.db import Database
from tazko.db.tenant import Tenants
from tazko.modules.invites import repository as invite_repo
from tazko.modules.invites import service as invites
from tazko.modules.orgs import service as orgs
from tazko.modules.orgs.service import Org
from tazko.modules.users import service as users
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


def acme_events(tenants: Tenants, kind: str) -> int:
    return int(
        tenants.get("acme").db.read(
            lambda c: c.execute("SELECT count(*) FROM events WHERE type = ?", (kind,)).fetchone()[0]
        )
    )


def refusal_reasons(control: Database) -> list[str]:
    return [json.loads(row["detail"])["reason"] for row in audit(control, "signin.refused")]


# --- making invites ------------------------------------------------------------------


def test_invite_expires_14_days_after_it_is_made(control: Database, acme: Org) -> None:
    invite = invites.create_invite(
        control, org=acme, email="Bo@Example.com", role="member", actor_id=None
    )

    assert invite.email == "bo@example.com"
    made = datetime.fromisoformat(invite.created_at)
    assert datetime.fromisoformat(invite.expires_at) - made == timedelta(days=14)
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


def test_revoking_an_unknown_invite_is_not_found(control: Database, acme: Org) -> None:
    with pytest.raises(NotFound):
        invites.revoke_invite(control, org=acme, invite_id=9999, actor_id=None)


def test_revoking_twice_is_a_conflict(control: Database, acme: Org) -> None:
    invite = invites.create_invite(
        control, org=acme, email="bo@example.com", role="member", actor_id=None
    )
    invites.revoke_invite(control, org=acme, invite_id=invite.id, actor_id=None)

    with pytest.raises(Conflict) as err:
        invites.revoke_invite(control, org=acme, invite_id=invite.id, actor_id=None)
    assert err.value.code == "INVITE_REVOKED"


def test_revoking_a_used_invite_is_a_conflict(
    client: TestClient, google: FakeGoogle, control: Database, acme: Org
) -> None:
    invite = invites.create_invite(
        control, org=acme, email="bo@example.com", role="member", actor_id=None
    )
    sign_in(client, google, **BO)

    with pytest.raises(Conflict) as err:
        invites.revoke_invite(control, org=acme, invite_id=invite.id, actor_id=None)
    assert err.value.code == "INVITE_USED"


def test_inviting_a_member_is_a_conflict(control: Database, tenants: Tenants, acme: Org) -> None:
    bo = users.get_or_create(control, "bo@example.com")
    orgs.add_member(control, tenants, org=acme, user=bo, role="member", actor_id=None)

    with pytest.raises(Conflict) as err:
        invites.create_invite(
            control, org=acme, email="Bo@example.com", role="owner", actor_id=None
        )
    assert err.value.code == "ALREADY_MEMBER"


def test_inviting_into_a_suspended_company_is_a_conflict(control: Database, acme: Org) -> None:
    control.write(lambda c: c.execute("UPDATE orgs SET status = 'suspended'"))
    suspended = Org(id=acme.id, slug=acme.slug, name=acme.name, status="suspended")

    with pytest.raises(Conflict) as err:
        invites.create_invite(
            control, org=suspended, email="bo@example.com", role="member", actor_id=None
        )
    assert err.value.code == "COMPANY_NOT_ACTIVE"


def test_only_an_owner_or_super_admin_may_invite_or_revoke(
    control: Database, tenants: Tenants, acme: Org
) -> None:
    owner = users.get_or_create(control, "owner@example.com")
    member = users.get_or_create(control, "member@example.com")
    stranger = users.get_or_create(control, "stranger@example.com")
    admin, _ = users.grant_super_admin(control, "admin@example.com", actor_id=None)
    orgs.add_member(control, tenants, org=acme, user=owner, role="owner", actor_id=None)
    orgs.add_member(control, tenants, org=acme, user=member, role="member", actor_id=None)

    made = invites.create_invite(
        control, org=acme, email="bo@example.com", role="member", actor_id=owner.id
    )
    invites.create_invite(
        control, org=acme, email="cy@example.com", role="owner", actor_id=admin.id
    )
    with pytest.raises(Forbidden):
        invites.create_invite(
            control, org=acme, email="di@example.com", role="member", actor_id=member.id
        )
    with pytest.raises(NotFound):  # another company's people learn nothing about it
        invites.create_invite(
            control, org=acme, email="di@example.com", role="owner", actor_id=stranger.id
        )
    with pytest.raises(Forbidden):
        invites.revoke_invite(control, org=acme, invite_id=made.id, actor_id=member.id)
    invites.revoke_invite(control, org=acme, invite_id=made.id, actor_id=owner.id)


def test_an_invite_is_revoked_only_through_its_own_company(
    control: Database, tenants: Tenants, acme: Org
) -> None:
    beta = orgs.create_company(control, tenants, slug="beta", name="Beta", actor_id=None)
    invite = invites.create_invite(
        control, org=acme, email="bo@example.com", role="member", actor_id=None
    )

    with pytest.raises(NotFound):
        invites.revoke_invite(control, org=beta, invite_id=invite.id, actor_id=None)
    assert control.read(lambda c: invite_repo.by_id(c, invite.id)).revoked_at is None  # type: ignore[union-attr]  # the invite exists


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
    app: FastAPI,
    client: TestClient,
    google: FakeGoogle,
    control: Database,
    tenants: Tenants,
    acme: Org,
) -> None:
    @app.get("/api/orgs/{slug}/people")
    def people(company: CompanyDep) -> list[str]:
        return company.tenant.db.read(
            lambda c: [row["email"] for row in c.execute("SELECT email FROM people")]
        )

    invites.create_invite(control, org=acme, email="bo@example.com", role="member", actor_id=None)
    sign_in(client, google, **BO)

    assert client.get("/api/orgs/acme/people").json() == ["bo@example.com"]
    client.get("/api/orgs/acme/people")
    joined = acme_events(tenants, "member.joined")
    assert joined == 1  # copied once, not on every open


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
    invites.revoke_invite(control, org=acme, invite_id=invite.id, actor_id=None)

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
    client: TestClient, google: FakeGoogle, control: Database, tenants: Tenants, acme: Org
) -> None:
    # given an invite as member is pending, and Bo was made an owner another way since
    invites.create_invite(control, org=acme, email="bo@example.com", role="member", actor_id=None)
    bo = users.get_or_create(control, "bo@example.com")
    orgs.add_member(control, tenants, org=acme, user=bo, role="owner", actor_id=None)

    sign_in(client, google, **BO)

    assert member_role(control, acme, "bo@example.com") == "owner"


def test_invite_does_not_let_a_disabled_person_in(
    client: TestClient, google: FakeGoogle, control: Database, tenants: Tenants, acme: Org
) -> None:
    invites.create_invite(control, org=acme, email="bo@example.com", role="member", actor_id=None)
    sign_in(client, google, **BO)
    control.write(lambda c: c.execute("UPDATE users SET disabled_at = '2026-01-01T00:00:00.000Z'"))
    beta = orgs.create_company(control, tenants, slug="beta", name="Beta", actor_id=None)
    invites.create_invite(control, org=beta, email="bo@example.com", role="owner", actor_id=None)

    response = sign_in(client, google, **BO)

    assert response.headers["location"] == f"{WEB}/signin/refused"
    assert refusal_reasons(control) == ["disabled"]
    assert member_role(control, beta, "bo@example.com") is None


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


# --- the refusal lookup ---------------------------------------------------------------


def test_refusal_lookup_finds_the_newest_unused_invite(control: Database, acme: Org) -> None:
    first = invites.create_invite(
        control, org=acme, email="bo@example.com", role="member", actor_id=None
    )
    invites.revoke_invite(control, org=acme, invite_id=first.id, actor_id=None)
    second = invites.create_invite(
        control, org=acme, email="bo@example.com", role="owner", actor_id=None
    )
    control.write(
        lambda c: c.execute(
            "UPDATE invites SET accepted_at = created_at WHERE id = ?", (second.id,)
        )
    )

    found = control.read(lambda c: invite_repo.latest_unused(c, "bo@example.com"))

    assert found is not None
    assert found.id == first.id  # the accepted one is skipped, the revoked one counts


def test_refusal_lookup_uses_the_unused_invites_index(control: Database) -> None:
    # Anyone can trigger this lookup by signing in, so it must not scan the table.
    def plan(conn: sqlite3.Connection) -> list[str]:
        statements: list[str] = []
        conn.set_trace_callback(statements.append)
        try:
            invite_repo.latest_unused(conn, "bo@example.com")
        finally:
            conn.set_trace_callback(None)
        query = statements[-1].replace("'bo@example.com'", "?")
        return [row[3] for row in conn.execute("EXPLAIN QUERY PLAN " + query, ("bo@example.com",))]

    assert any("invites_unused_by_email" in step for step in control.read(plan))


# --- Workspace domains ------------------------------------------------------------

CORP = "corp.example"


def seen_workspace(client: TestClient, google: FakeGoogle, control: Database, acme: Org) -> None:
    """Someone from corp.example signed in with its Workspace, so the domain is known."""
    invites.create_invite(control, org=acme, email=f"ana@{CORP}", role="member", actor_id=None)
    sign_in(client, google, sub="sub-ana", email=f"ana@{CORP}", hd=CORP)
    client.cookies.clear()


def test_personal_account_cannot_use_an_invite_for_a_workspace_address(
    client: TestClient, google: FakeGoogle, control: Database, acme: Org
) -> None:
    seen_workspace(client, google, control, acme)
    invites.create_invite(control, org=acme, email=f"bo@{CORP}", role="owner", actor_id=None)

    response = sign_in(client, google, sub="sub-ghost", email=f"bo@{CORP}")

    assert response.headers["location"] == f"{WEB}/signin/refused"
    assert refusal_reasons(control) == ["workspace_required"]
    assert member_role(control, acme, f"bo@{CORP}") is None


def test_workspace_account_uses_the_invite_for_its_address(
    client: TestClient, google: FakeGoogle, control: Database, acme: Org
) -> None:
    seen_workspace(client, google, control, acme)
    invites.create_invite(control, org=acme, email=f"bo@{CORP}", role="member", actor_id=None)

    sign_in(client, google, sub="sub-bo", email=f"bo@{CORP}", hd=CORP)

    assert member_role(control, acme, f"bo@{CORP}") == "member"


def test_domain_never_seen_with_a_workspace_accepts_a_personal_account(
    client: TestClient, google: FakeGoogle, control: Database, acme: Org
) -> None:
    # A company whose email is not on Google signs in with personal Google accounts.
    invites.create_invite(control, org=acme, email="bo@mail.example", role="member", actor_id=None)

    sign_in(client, google, sub="sub-bo", email="bo@mail.example")

    assert member_role(control, acme, "bo@mail.example") == "member"


def test_alias_domain_of_a_workspace_is_protected_too(
    client: TestClient, google: FakeGoogle, control: Database, acme: Org
) -> None:
    # Ana's address is on the Workspace's second domain; Google reports the main one.
    invites.create_invite(
        control, org=acme, email="ana@corp.example.io", role="member", actor_id=None
    )
    sign_in(client, google, sub="sub-ana", email="ana@corp.example.io", hd=CORP)
    client.cookies.clear()
    invites.create_invite(
        control, org=acme, email="bo@corp.example.io", role="owner", actor_id=None
    )

    sign_in(client, google, sub="sub-ghost", email="bo@corp.example.io")

    assert refusal_reasons(control) == ["workspace_required"]


def test_workspace_domain_is_matched_without_case(
    client: TestClient, google: FakeGoogle, control: Database, acme: Org
) -> None:
    invites.create_invite(control, org=acme, email=f"ana@{CORP}", role="member", actor_id=None)
    sign_in(client, google, sub="sub-ana", email=f"ana@{CORP}", hd="Corp.Example")
    client.cookies.clear()
    invites.create_invite(control, org=acme, email=f"bo@{CORP}", role="owner", actor_id=None)

    sign_in(client, google, sub="sub-ghost", email=f"bo@{CORP}")

    assert refusal_reasons(control) == ["workspace_required"]


def test_workspace_stays_known_after_its_people_are_gone(
    client: TestClient, google: FakeGoogle, control: Database, acme: Org
) -> None:
    seen_workspace(client, google, control, acme)
    control.write(lambda c: c.execute("DELETE FROM users"))
    invites.create_invite(control, org=acme, email=f"bo@{CORP}", role="owner", actor_id=None)

    sign_in(client, google, sub="sub-ghost", email=f"bo@{CORP}")

    assert refusal_reasons(control) == ["workspace_required"]


def test_personal_account_cannot_move_onto_a_workspace_address(
    client: TestClient, google: FakeGoogle, control: Database, tenants: Tenants, acme: Org
) -> None:
    # given Bo signs in with a personal account on another address, and corp is a Workspace
    invites.create_invite(control, org=acme, email="bo@mail.example", role="member", actor_id=None)
    sign_in(client, google, sub="sub-bo", email="bo@mail.example")
    client.cookies.clear()
    seen_workspace(client, google, control, acme)
    beta = orgs.create_company(control, tenants, slug="beta", name="Beta", actor_id=None)
    invites.create_invite(control, org=beta, email=f"bo@{CORP}", role="owner", actor_id=None)

    # when the personal account's email changes to the Workspace address at Google
    sign_in(client, google, sub="sub-bo", email=f"bo@{CORP}")

    # then the stored address stays, and the Workspace address's invite is not used
    assert client.get("/api/me").json()["email"] == "bo@mail.example"
    assert member_role(control, beta, f"bo@{CORP}") is None


def test_personal_account_linked_before_the_domain_was_known_uses_no_new_invites(
    client: TestClient, google: FakeGoogle, control: Database, tenants: Tenants, acme: Org
) -> None:
    # given Bo linked a personal account on bo@corp before corp was known as a Workspace
    invites.create_invite(control, org=acme, email=f"bo@{CORP}", role="member", actor_id=None)
    sign_in(client, google, sub="sub-bo", email=f"bo@{CORP}")
    client.cookies.clear()
    seen_workspace(client, google, control, acme)
    beta = orgs.create_company(control, tenants, slug="beta", name="Beta", actor_id=None)
    invites.create_invite(control, org=beta, email=f"bo@{CORP}", role="owner", actor_id=None)

    # when Bo signs in again
    response = sign_in(client, google, sub="sub-bo", email=f"bo@{CORP}")

    # then Bo still signs in (linked by sub) but the new invite is not used
    assert response.headers["location"] == f"{WEB}/"
    assert member_role(control, beta, f"bo@{CORP}") is None
