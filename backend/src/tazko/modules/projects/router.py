"""Projects and project members under /api/orgs/{slug}/projects. Every check
is in the service (access.decide); routes only parse and shape."""

from __future__ import annotations

from typing import Annotated, Literal

from fastapi import APIRouter, Path, Query, Response

from tazko.core.deps import ClientIp, CompanyDep, ControlDep, CurrentUser
from tazko.modules.projects import service
from tazko.modules.projects.schemas import (
    MemberIn,
    ProjectIn,
    ProjectMemberOut,
    ProjectOut,
    ProjectPatch,
    ProjectSummaryOut,
    RoleIn,
)

router = APIRouter(prefix="/api/orgs/{slug}/projects")

# SQLite integers: a bigger id would crash the query instead of answering 404.
ProjectId = Annotated[int, Path(ge=1, le=2**63 - 1)]
UserId = Annotated[int, Path(ge=1, le=2**63 - 1)]
BoardId = Annotated[int, Path(ge=1, le=2**63 - 1)]


@router.get("")
def projects(
    company: CompanyDep,
    user: CurrentUser,
    view: Annotated[Literal["mine", "manage"], Query()] = "mine",
) -> list[ProjectOut] | list[ProjectSummaryOut]:
    """`mine`: the projects you are in. `manage`: every project, for company
    owners (Manage projects). At most 500, by name."""
    if view == "manage":
        return [ProjectSummaryOut.of(s) for s in service.manage_view(company)]
    return [ProjectOut.of(seen) for seen in service.mine(company, actor_id=user.id)]


@router.post("", status_code=201)
def create(
    body: ProjectIn, response: Response, company: CompanyDep, user: CurrentUser, control: ControlDep
) -> ProjectOut:
    seen = service.create(
        control,
        company,
        actor_id=user.id,
        name=body.name,
        description=body.description,
        color=body.color,
        owner_id=body.owner_id,
    )
    response.headers["Location"] = f"/api/orgs/{company.org.slug}/projects/{seen.project.id}"
    return ProjectOut.of(seen)


@router.get("/{project_id}")
def project(project_id: ProjectId, company: CompanyDep, user: CurrentUser) -> ProjectOut:
    return ProjectOut.of(service.get(company, actor_id=user.id, project_id=project_id))


@router.patch("/{project_id}")
def update(
    project_id: ProjectId, body: ProjectPatch, company: CompanyDep, user: CurrentUser
) -> ProjectOut:
    seen = service.update(
        company,
        actor_id=user.id,
        project_id=project_id,
        changes=body.changes(),
        archived=body.archived,
    )
    return ProjectOut.of(seen)


@router.delete("/{project_id}", status_code=204)
def delete(project_id: ProjectId, company: CompanyDep, user: CurrentUser) -> Response:
    service.delete(company, actor_id=user.id, project_id=project_id)
    return Response(status_code=204)


@router.get("/{project_id}/members")
def members(
    project_id: ProjectId, company: CompanyDep, user: CurrentUser
) -> list[ProjectMemberOut]:
    """At most 500, by name."""
    rows = service.members(company, actor_id=user.id, project_id=project_id)
    return [ProjectMemberOut.of(row) for row in rows]


@router.post("/{project_id}/members", status_code=201)
def add_member(
    project_id: ProjectId,
    body: MemberIn,
    response: Response,
    company: CompanyDep,
    user: CurrentUser,
    control: ControlDep,
    ip: ClientIp,
) -> ProjectMemberOut:
    added = service.add_member(
        control,
        company,
        actor_id=user.id,
        project_id=project_id,
        user_id=body.user_id,
        role=body.role,
        ip=ip,
    )
    response.headers["Location"] = (
        f"/api/orgs/{company.org.slug}/projects/{project_id}/members/{added.user_id}"
    )
    return ProjectMemberOut.of(added)


@router.patch("/{project_id}/members/{user_id}")
def change_role(
    project_id: ProjectId,
    user_id: UserId,
    body: RoleIn,
    company: CompanyDep,
    user: CurrentUser,
    control: ControlDep,
    ip: ClientIp,
) -> ProjectMemberOut:
    changed = service.change_role(
        control,
        company,
        actor_id=user.id,
        project_id=project_id,
        user_id=user_id,
        role=body.role,
        ip=ip,
    )
    return ProjectMemberOut.of(changed)


@router.delete("/{project_id}/members/{user_id}", status_code=204)
def remove_member(
    project_id: ProjectId,
    user_id: UserId,
    company: CompanyDep,
    user: CurrentUser,
    control: ControlDep,
) -> Response:
    service.remove_member(
        control, company, actor_id=user.id, project_id=project_id, user_id=user_id
    )
    return Response(status_code=204)
