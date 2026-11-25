"""API contract for company invites."""

from __future__ import annotations

from typing import Literal, cast

from pydantic import BaseModel, ConfigDict

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


ProjectRole = Literal["owner", "member", "observer"]


class ProjectInviteIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: str
    role: ProjectRole


class ProjectInviteOut(BaseModel):
    """A pending invite to one project. `role` is the role in the project;
    in the company the person is always a plain member."""

    id: int
    email: str
    role: ProjectRole
    account: Literal["workspace", "personal"] | None
    invited_by: str | None
    created_at: str
    expires_at: str

    @classmethod
    def from_pending(cls, invite: service.PendingInvite) -> ProjectInviteOut:
        return cls(
            id=invite.id,
            email=invite.email,
            role=cast(ProjectRole, invite.project_role),  # invites.project_role CHECK
            account=service.account_kind(invite),
            invited_by=invite.invited_by,
            created_at=invite.created_at,
            expires_at=invite.expires_at,
        )
