"""API contract of the super admin console."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, model_validator

from tazko.modules.admin import service as admin
from tazko.modules.invites.schemas import InviteOut
from tazko.modules.orgs.console import CompanySummary
from tazko.modules.users import service as users


class CompanyIn(BaseModel):
    slug: str
    name: str


class DeleteCompanyIn(BaseModel):
    """The short name typed again, as in the prototype's confirm dialog."""

    confirm: str = Field(max_length=40)


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
    def from_summary(cls, summary: CompanySummary) -> CompanySummaryOut:
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


class PersonCompany(BaseModel):
    slug: str
    name: str
    role: Literal["owner", "member"]


class PersonOut(BaseModel):
    """A row of the People page. `account` is None until they first sign in."""

    id: int
    name: str
    email: str
    avatar_url: str | None
    account: Literal["workspace", "personal"] | None
    companies: list[PersonCompany]
    last_seen_at: str | None
    is_super_admin: bool
    active: bool

    @classmethod
    def from_person(cls, person: users.Person) -> PersonOut:
        row = person.row
        return cls(
            id=row.id,
            name=row.name,
            email=row.email,
            avatar_url=row.avatar_url,
            account=person.account,
            companies=[
                PersonCompany(slug=c.slug, name=c.name, role=c.role) for c in person.companies
            ],
            last_seen_at=row.last_seen_at,
            is_super_admin=row.is_super_admin,
            active=not row.disabled,
        )


class PeoplePage(BaseModel):
    items: list[PersonOut]
    next: int | None


class PersonFlagsIn(BaseModel):
    """At least one of the two switches on the People page."""

    is_super_admin: bool | None = None
    active: bool | None = None

    @model_validator(mode="after")
    def _one(self) -> PersonFlagsIn:
        if self.is_super_admin is None and self.active is None:
            raise ValueError("send is_super_admin, active or both")
        return self


class Actor(BaseModel):
    id: int
    name: str
    email: str


class AuditEntryOut(BaseModel):
    """One audit row. `actor` is None for the command line or a refused sign-in;
    `company` is None when the action is not about one company."""

    id: int
    at: str
    action: str
    actor: Actor | None
    company: CompanyRef | None
    target: str | None
    detail: dict[str, object] | None
    ip: str | None

    @classmethod
    def from_entry(cls, entry: admin.Entry) -> AuditEntryOut:
        actor = None
        if entry.actor_id is not None and entry.actor_email is not None:
            actor = Actor(id=entry.actor_id, name=entry.actor_name or "", email=entry.actor_email)
        company = None
        if entry.org_slug is not None and entry.org_name is not None:
            company = CompanyRef(slug=entry.org_slug, name=entry.org_name)
        return cls(
            id=entry.id,
            at=entry.at,
            action=entry.action,
            actor=actor,
            company=company,
            target=entry.target,
            detail=entry.detail,
            ip=entry.ip,
        )


class AuditPage(BaseModel):
    items: list[AuditEntryOut]
    next: int | None


class EmailOut(BaseModel):
    enabled: bool
    host: str | None
    port: int | None
    sender: str | None


class ServerOut(BaseModel):
    """The Server page. `last_backup` arrives with the backup command (M1-08)."""

    version: str
    public_url: str
    uptime_seconds: int
    data_bytes: int
    last_backup: None = None
    email: EmailOut

    @classmethod
    def from_info(cls, info: admin.ServerInfo) -> ServerOut:
        return cls(
            version=info.version,
            public_url=info.public_url,
            uptime_seconds=info.uptime_seconds,
            data_bytes=info.data_bytes,
            email=EmailOut(
                enabled=info.email.enabled,
                host=info.email.host,
                port=info.email.port,
                sender=info.email.sender,
            ),
        )


class WorkspaceDomainOut(BaseModel):
    domain: str
    first_seen_at: str
