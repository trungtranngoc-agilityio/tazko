"""People, sessions and rows for the project and board API tests (M2-02).
Fixtures that use these live in conftest.py."""

from __future__ import annotations

import sqlite3
from typing import Any

from fastapi.testclient import TestClient

from tazko.db import Database
from tazko.db.tenant import Tenants
from tazko.modules.orgs import service as orgs
from tazko.modules.orgs.service import Org
from tazko.modules.users import service as users
from tazko.modules.users.service import User
from tests.integration.oidc import SAME_ORIGIN, FakeGoogle, sign_in

BASE = "/api/orgs/acme/projects"


def person(control: Database, tenants: Tenants, org: Org, name: str, role: str) -> User:
    user = users.get_or_create(control, f"{name}@example.com", name=name.title())
    orgs.add_member(control, tenants, org=org, user=user, role=role, actor_id=None)  # type: ignore[arg-type]  # role is owner or member here
    return user


def as_(client: TestClient, google: FakeGoogle, user: User) -> None:
    """Sign in as this person (a fresh session)."""
    client.cookies.clear()
    sign_in(client, google, sub=f"sub-{user.id}", email=user.email, name=user.name)


def write(client: TestClient, method: str, path: str, body: Any = None) -> Any:
    return client.request(method, path, json=body, headers=SAME_ORIGIN)


def company_rows(tenants: Tenants, sql: str, *args: object) -> list[sqlite3.Row]:
    return tenants.get("acme").db.read(lambda c: c.execute(sql, args).fetchall())


def roles(tenants: Tenants, project: int) -> dict[int, str]:
    rows = company_rows(
        tenants, "SELECT person_id, role FROM project_members WHERE project_id = ?", project
    )
    return {r[0]: r[1] for r in rows}


def join(
    client: TestClient, google: FakeGoogle, project: int, user: User, role: str, by: User
) -> None:
    """`by` adds `user` to the project with `role`."""
    as_(client, google, by)
    added = write(client, "POST", f"{BASE}/{project}/members", {"user_id": user.id, "role": role})
    assert added.status_code == 201, added.text
