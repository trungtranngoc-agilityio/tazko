"""Super admin console API under /admin/api (M1-06).

Every route depends on `get_console`, which answers 401 without a session and
403 for anyone who is not a super admin. Members and invites go through the
same services as Company settings, with the super admin as the actor.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Path, Response

from tazko.core.deps import (
    ClientIp,
    ConsoleCompanyDep,
    ConsoleDep,
    ControlDep,
    get_console,
)
from tazko.modules.admin.schemas import AnyInviteOut, CompanyIn, CompanyRef, CompanySummaryOut
from tazko.modules.invites import service as invites
from tazko.modules.invites.schemas import InviteIn, InviteOut
from tazko.modules.orgs import service as orgs
from tazko.modules.orgs.schemas import MemberOut, RoleIn

router = APIRouter(prefix="/admin/api", dependencies=[Depends(get_console)])

# A SQLite integer: a bigger id would crash the query instead of answering 404.
Id = Annotated[int, Path(ge=1, le=2**63 - 1)]


# --- companies -------------------------------------------------------------------------


@router.get("/companies")
def companies(console: ConsoleDep) -> list[CompanySummaryOut]:
    """At most 500 companies, by name."""
    return [CompanySummaryOut.from_summary(s) for s in console.companies()]


@router.post("/companies", status_code=201)
def create_company(body: CompanyIn, response: Response, console: ConsoleDep) -> CompanySummaryOut:
    org = console.create(slug=body.slug, name=body.name)
    response.headers["Location"] = f"/admin/api/companies/{org.slug}"
    return CompanySummaryOut.from_summary(console.company(org.slug))


@router.get("/companies/{slug}")
def company(slug: str, console: ConsoleDep) -> CompanySummaryOut:
    return CompanySummaryOut.from_summary(console.company(slug))


# --- company detail: members and invites ---------------------------------------------------


@router.get("/companies/{slug}/members")
def members(
    company: ConsoleCompanyDep, console: ConsoleDep, control: ControlDep
) -> list[MemberOut]:
    rows = orgs.list_members(control, company, actor_id=console.actor_id)
    return [MemberOut.from_row(row) for row in rows]


@router.patch("/companies/{slug}/members/{user_id}")
def change_role(
    user_id: Id,
    body: RoleIn,
    company: ConsoleCompanyDep,
    console: ConsoleDep,
    control: ControlDep,
    ip: ClientIp,
) -> MemberOut:
    row = orgs.change_role(
        control, company, user_id=user_id, role=body.role, actor_id=console.actor_id, ip=ip
    )
    return MemberOut.from_row(row)


@router.delete("/companies/{slug}/members/{user_id}", status_code=204)
def remove_member(
    user_id: Id, company: ConsoleCompanyDep, console: ConsoleDep, control: ControlDep, ip: ClientIp
) -> Response:
    orgs.remove_member(control, company, user_id=user_id, actor_id=console.actor_id, ip=ip)
    return Response(status_code=204)


@router.get("/companies/{slug}/invites")
def company_invites(
    company: ConsoleCompanyDep, console: ConsoleDep, control: ControlDep
) -> list[InviteOut]:
    rows = invites.list_pending(control, company, actor_id=console.actor_id)
    return [InviteOut.from_pending(i) for i in rows]


@router.post("/companies/{slug}/invites", status_code=201)
def invite(
    body: InviteIn,
    response: Response,
    company: ConsoleCompanyDep,
    console: ConsoleDep,
    control: ControlDep,
    ip: ClientIp,
) -> InviteOut:
    made = invites.create_invite(
        control, org=company.org, email=body.email, role=body.role, actor_id=console.actor_id, ip=ip
    )
    response.headers["Location"] = f"/admin/api/companies/{company.org.slug}/invites/{made.id}"
    return InviteOut.from_pending(made)


@router.delete("/companies/{slug}/invites/{invite_id}", status_code=204)
def revoke_company_invite(
    invite_id: Id,
    company: ConsoleCompanyDep,
    console: ConsoleDep,
    control: ControlDep,
    ip: ClientIp,
) -> Response:
    invites.revoke_invite(
        control, org=company.org, invite_id=invite_id, actor_id=console.actor_id, ip=ip
    )
    return Response(status_code=204)


# --- invites across companies ------------------------------------------------------------


@router.get("/invites")
def all_invites(console: ConsoleDep, control: ControlDep) -> list[AnyInviteOut]:
    """At most 500 pending invites of every company, newest first."""
    return [
        AnyInviteOut(
            **InviteOut.from_pending(row.invite).model_dump(),
            company=CompanyRef(slug=row.org_slug, name=row.org_name),
        )
        for row in invites.list_everywhere(control, actor_id=console.actor_id)
    ]


@router.delete("/invites/{invite_id}", status_code=204)
def revoke_any(invite_id: Id, console: ConsoleDep, control: ControlDep, ip: ClientIp) -> Response:
    invites.revoke_anywhere(control, invite_id=invite_id, actor_id=console.actor_id, ip=ip)
    return Response(status_code=204)
