"""API contract for companies and their members."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel

from tazko.modules.orgs import service

Role = Literal["owner", "member"]
AccountKind = Literal["workspace", "personal"]


class CompanyOut(BaseModel):
    """One entry of the company switcher."""

    slug: str
    name: str
    role: Role
    status: Literal["active", "suspended"]


class MemberOut(BaseModel):
    """A member as the company settings page shows them. `account` is None
    until they first sign in; `last_seen_at` is their last sign-in."""

    user_id: int
    name: str
    email: str
    avatar_url: str | None
    account: AccountKind | None
    role: Role
    last_seen_at: str | None

    @classmethod
    def from_row(cls, row: service.MemberRow) -> MemberOut:
        return cls(
            user_id=row.user_id,
            name=row.name,
            email=row.email,
            avatar_url=row.avatar_url,
            account=service.account_kind(row),
            role=row.role,
            last_seen_at=row.last_seen_at,
        )


class RoleIn(BaseModel):
    role: Role
