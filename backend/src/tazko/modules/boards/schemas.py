"""API contract for boards."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, model_validator

from tazko.core.fields import Background, Id, Name
from tazko.modules.boards import service


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
