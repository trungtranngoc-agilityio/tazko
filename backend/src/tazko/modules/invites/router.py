"""Invites of one company, for its owners. Every check is in the service."""

from __future__ import annotations

from fastapi import APIRouter, Response

from tazko.core.deps import ClientIp, CompanyDep, ControlDep, CurrentUser
from tazko.modules.invites import service
from tazko.modules.invites.schemas import InviteIn, InviteOut

router = APIRouter()


def _out(invite: service.PendingInvite) -> InviteOut:
    return InviteOut(
        id=invite.id,
        email=invite.email,
        role=invite.role,
        account=service.account_kind(invite),
        invited_by=invite.invited_by,
        created_at=invite.created_at,
        expires_at=invite.expires_at,
    )


@router.get("/api/orgs/{slug}/invites")
def pending(company: CompanyDep, user: CurrentUser, control: ControlDep) -> list[InviteOut]:
    """At most 500 pending invites, newest first."""
    return [_out(i) for i in service.list_pending(control, company, actor_id=user.id)]


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
    found = next(
        i for i in service.list_pending(control, company, actor_id=user.id) if i.id == made.id
    )
    response.headers["Location"] = f"/api/orgs/{company.org.slug}/invites/{made.id}"
    return _out(found)


@router.delete("/api/orgs/{slug}/invites/{invite_id}", status_code=204)
def revoke(
    invite_id: int, company: CompanyDep, user: CurrentUser, control: ControlDep, ip: ClientIp
) -> Response:
    service.revoke_invite(control, org=company.org, invite_id=invite_id, actor_id=user.id, ip=ip)
    return Response(status_code=204)
