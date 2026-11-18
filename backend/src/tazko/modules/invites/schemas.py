"""API contract for company invites."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel

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
