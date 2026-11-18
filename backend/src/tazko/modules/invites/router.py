"""Invites of one company, for its owners. Every check is in the service."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Path, Response

from tazko.core.deps import ClientIp, CompanyDep, ControlDep, CurrentUser
from tazko.modules.invites import service
from tazko.modules.invites.schemas import InviteIn, InviteOut

router = APIRouter()

# A SQLite integer: a bigger id would crash the query instead of answering 404.
InviteId = Annotated[int, Path(ge=1, le=2**63 - 1)]


@router.get("/api/orgs/{slug}/invites")
def pending(company: CompanyDep, user: CurrentUser, control: ControlDep) -> list[InviteOut]:
    """At most 500 pending invites, newest first."""
    return [
        InviteOut.from_pending(i) for i in service.list_pending(control, company, actor_id=user.id)
    ]


@router.post("/api/orgs/{slug}/invites", status_code=201)
def invite(
    body: InviteIn,
    response: Response,
    company: CompanyDep,
    user: CurrentUser,
    control: ControlDep,
    ip: ClientIp,
) -> InviteOut:
    made = service.create_invite(
        control, org=company.org, email=body.email, role=body.role, actor_id=user.id, ip=ip
    )
    # Identifies the invite (DELETE answers there); there is no GET for one invite.
    response.headers["Location"] = f"/api/orgs/{company.org.slug}/invites/{made.id}"
    return InviteOut.from_pending(made)


@router.delete("/api/orgs/{slug}/invites/{invite_id}", status_code=204)
def revoke(
    invite_id: InviteId, company: CompanyDep, user: CurrentUser, control: ControlDep, ip: ClientIp
) -> Response:
    service.revoke_invite(control, org=company.org, invite_id=invite_id, actor_id=user.id, ip=ip)
    return Response(status_code=204)
