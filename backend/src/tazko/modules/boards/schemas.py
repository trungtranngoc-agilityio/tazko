"""API contract for projects and project members (M2-02)."""

from __future__ import annotations

from typing import Annotated, Literal, cast

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

from tazko.modules.boards import service

ProjectRole = Literal["owner", "member", "observer"]
Name = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)]
Key = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=32)]
Background = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=64)]
Description = Annotated[str, StringConstraints(max_length=2000)]
# A SQLite integer: a bigger id would crash the query instead of answering 404 or 422.
Id = Annotated[int, Field(ge=1, le=2**63 - 1)]


class ProjectIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: Name
    description: Description = ""
    color: Key | None = None
    owner_id: Id


class ProjectPatch(BaseModel):
    """Only the fields sent change. `archived` archives or restores (company
    owners); the name is a company owner's or a project owner's; the rest are
    a project owner's."""

    model_config = ConfigDict(extra="forbid")

    name: Name | None = None
    description: Description | None = None
    color: Key | None = None
    default_background: Background | None = None
    members_can_create_boards: bool | None = None
    members_can_invite: bool | None = None
    aging_enabled: bool | None = None
    aging_days: Literal[3, 7, 14, 30] | None = None
    archived: bool | None = None

    @model_validator(mode="after")
    def _only_colours_clear(self) -> ProjectPatch:
        """Null clears the colour or the background; it is not a value for the rest."""
        nulls = {n for n in self.model_fields_set if getattr(self, n) is None}
        if nulls - {"color", "default_background"}:
            raise ValueError(f"cannot be null: {', '.join(sorted(nulls))}")
        return self

    def changes(self) -> dict[str, object]:
        """The settings sent, without `archived`."""
        return {name: getattr(self, name) for name in self.model_fields_set if name != "archived"}


class ProjectOut(BaseModel):
    """`role` is the signed-in person's role in the project, None when they
    are a company owner who is not in it."""

    id: int
    name: str
    description: str
    color: str | None
    default_background: str | None
    members_can_create_boards: bool
    members_can_invite: bool
    aging_enabled: bool
    aging_days: int
    created_at: str
    archived_at: str | None
    role: ProjectRole | None

    @classmethod
    def of(cls, seen: service.Seen) -> ProjectOut:
        p = seen.project
        return cls(
            id=p.id,
            name=p.name,
            description=p.description,
            color=p.color,
            default_background=p.default_background,
            members_can_create_boards=p.members_can_create_boards,
            members_can_invite=p.members_can_invite,
            aging_enabled=p.aging_enabled,
            aging_days=p.aging_days,
            created_at=p.created_at,
            archived_at=p.archived_at,
            role=seen.role,
        )


class OwnerOut(BaseModel):
    user_id: int
    name: str


class ProjectSummaryOut(BaseModel):
    """A row of Manage projects (company owners): no boards are opened."""

    id: int
    name: str
    color: str | None
    archived_at: str | None
    owners: list[OwnerOut]
    members: int
    boards: int

    @classmethod
    def of(cls, summary: service.Summary) -> ProjectSummaryOut:
        p = summary.project
        return cls(
            id=p.id,
            name=p.name,
            color=p.color,
            archived_at=p.archived_at,
            owners=[OwnerOut(user_id=i, name=n) for i, n in summary.owners],
            members=summary.members,
            boards=summary.boards,
        )


class MemberIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    user_id: Id
    role: ProjectRole


class RoleIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    role: ProjectRole


class ProjectMemberOut(BaseModel):
    user_id: int
    name: str
    email: str
    avatar_url: str | None
    role: ProjectRole

    @classmethod
    def of(cls, member: service.Member) -> ProjectMemberOut:
        return cls(
            user_id=member.user_id,
            name=member.name,
            email=member.email,
            avatar_url=member.avatar_url,
            role=cast(ProjectRole, member.role),  # project_members.role CHECK
        )


# --- boards ------------------------------------------------------------------------------


class BoardIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: Name
    background: Background | None = None


class BoardPatch(BaseModel):
    """Only the fields sent change. `archived` closes or reopens the board;
    null clears the background and is not a name."""

    model_config = ConfigDict(extra="forbid")

    name: Name | None = None
    background: Background | None = None
    archived: bool | None = None

    @model_validator(mode="after")
    def _only_background_clears(self) -> BoardPatch:
        nulls = {n for n in self.model_fields_set if getattr(self, n) is None}
        if nulls - {"background"}:
            raise ValueError(f"cannot be null: {', '.join(sorted(nulls))}")
        return self

    def changes(self) -> dict[str, object]:
        return {name: getattr(self, name) for name in self.model_fields_set if name != "archived"}


class AccessIn(BaseModel):
    """`restricted` true: only project owners and `people` (project members)
    see the board. False: the whole project sees it and the list is cleared."""

    model_config = ConfigDict(extra="forbid")

    restricted: bool
    people: list[Id] = Field(default_factory=list, max_length=500)


class BoardOut(BaseModel):
    """`access` is the restricted list, shown to project owners only."""

    id: int
    project_id: int
    name: str
    background: str | None
    restricted: bool
    starred: bool
    access: list[int] | None
    created_at: str
    archived_at: str | None

    @classmethod
    def of(cls, seen: service.SeenBoard) -> BoardOut:
        b = seen.board
        return cls(
            id=b.id,
            project_id=b.project_id,
            name=b.name,
            background=b.background,
            restricted=b.restricted,
            starred=seen.starred,
            access=seen.access,
            created_at=b.created_at,
            archived_at=b.archived_at,
        )
