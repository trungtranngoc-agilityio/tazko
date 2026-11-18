"""Company switcher and company settings (members) for owners. Every check is
in the service; routes only parse and shape."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Path, Response

from tazko.core.deps import ClientIp, CompanyDep, ControlDep, CurrentUser
from tazko.modules.orgs import service
from tazko.modules.orgs.schemas import CompanyOut, MemberOut, RoleIn

router = APIRouter()

# A SQLite integer: a bigger id would crash the query instead of answering 404.
UserId = Annotated[int, Path(ge=1, le=2**63 - 1)]


@router.get("/api/orgs")
def my_companies(user: CurrentUser, control: ControlDep) -> list[CompanyOut]:
    """The signed-in person's companies, by name (deleted ones never appear)."""
    return [
        CompanyOut(
            slug=m.org.slug,
            name=m.org.name,
            role=m.role,
            status=m.org.status,
        )
        for m in service.companies_of(control, user.id)
    ]


@router.get("/api/orgs/{slug}/members")
def members(company: CompanyDep, user: CurrentUser, control: ControlDep) -> list[MemberOut]:
    """At most 500 members, by name."""
    rows = service.list_members(control, company, actor_id=user.id)
    return [MemberOut.from_row(row) for row in rows]


@router.patch("/api/orgs/{slug}/members/{user_id}")
def change_role(
    user_id: UserId,
    body: RoleIn,
    company: CompanyDep,
    user: CurrentUser,
    control: ControlDep,
    ip: ClientIp,
) -> MemberOut:
    row = service.change_role(
        control, company, user_id=user_id, role=body.role, actor_id=user.id, ip=ip
    )
    return MemberOut.from_row(row)


@router.delete("/api/orgs/{slug}/members/{user_id}", status_code=204)
def remove(
    user_id: UserId, company: CompanyDep, user: CurrentUser, control: ControlDep, ip: ClientIp
) -> Response:
    service.remove_member(control, company, user_id=user_id, actor_id=user.id, ip=ip)
    return Response(status_code=204)
