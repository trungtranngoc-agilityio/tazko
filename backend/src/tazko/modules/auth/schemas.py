from __future__ import annotations

from typing import Literal

from pydantic import BaseModel


class MeOut(BaseModel):
    """The signed-in person. Never carries `google_sub` or session data."""

    id: int
    email: str
    name: str
    avatar_url: str | None
    is_super_admin: bool


class RefusalOut(BaseModel):
    """Which Google account was just refused, for the refusal page. A cookie
    from the previous release has no reason and reads as not_invited."""

    email: str
    reason: Literal["not_invited", "company_suspended"] = "not_invited"
