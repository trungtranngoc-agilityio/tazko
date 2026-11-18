"""API contract for company invites."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel

from tazko.modules.invites import service

Role = Literal["owner", "member"]


class InviteIn(BaseModel):
    email: str
    role: Role


class InviteOut(BaseModel):
    """A pending invite. `account` says which kind of Google account the address
    will sign in with, when that is known; `invited_by` is the inviter's name
    (None for the command line or a person since removed)."""

    id: int
    email: str
    role: Role
    account: Literal["workspace", "personal"] | None
    invited_by: str | None
    created_at: str
    expires_at: str

    @classmethod
    def from_pending(cls, invite: service.PendingInvite) -> InviteOut:
        return cls(
            id=invite.id,
            email=invite.email,
            role=invite.role,
            account=service.account_kind(invite),
            invited_by=invite.invited_by,
            created_at=invite.created_at,
            expires_at=invite.expires_at,
        )
