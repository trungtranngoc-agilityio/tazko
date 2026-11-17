from __future__ import annotations

from pydantic import BaseModel


class MeOut(BaseModel):
    """The signed-in person. Never carries `google_sub` or session data."""

    id: int
    email: str
    name: str
    avatar_url: str | None
    is_super_admin: bool


class RefusalOut(BaseModel):
    """Which Google account was just refused, for the refusal page."""

    email: str
