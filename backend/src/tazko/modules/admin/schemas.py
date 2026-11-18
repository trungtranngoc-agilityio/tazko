"""API contract of the super admin console."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel

from tazko.modules.invites.schemas import InviteOut
from tazko.modules.orgs import service as orgs


class CompanyIn(BaseModel):
    slug: str
    name: str


class CompanySummaryOut(BaseModel):
    """A row of the Companies page. Boards are counted from M2."""

    slug: str
    name: str
    status: Literal["active", "suspended"]
    members: int
    storage_bytes: int
    storage_limit_bytes: int | None
    last_activity_at: str | None

    @classmethod
    def from_summary(cls, summary: orgs.CompanySummary) -> CompanySummaryOut:
        return cls(
            slug=summary.org.slug,
            name=summary.org.name,
            status=summary.org.status,
            members=summary.members,
            storage_bytes=summary.storage_bytes,
            storage_limit_bytes=summary.storage_limit_bytes,
            last_activity_at=summary.last_activity_at,
        )


class CompanyRef(BaseModel):
    slug: str
    name: str


class AnyInviteOut(InviteOut):
    """A pending invite on the console's Invites page, with its company."""

    company: CompanyRef
