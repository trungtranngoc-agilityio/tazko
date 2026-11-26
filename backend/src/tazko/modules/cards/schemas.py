"""API contract for lists and cards."""

from __future__ import annotations

from typing import Annotated

from pydantic import BaseModel, ConfigDict, StringConstraints, model_validator

from tazko.core.fields import Id, Name
from tazko.modules.cards import service

Title = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=512)]


def _says_what_changes(model: BaseModel, *fields: str) -> None:
    sent = model.model_fields_set
    if not sent:
        raise ValueError(f"send at least one of: {', '.join(fields)}")
    nulls = sorted(n for n in sent if getattr(model, n) is None)
    if nulls:
        raise ValueError(f"cannot be null: {', '.join(nulls)}")


class ListIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: Name


class ListPatch(BaseModel):
    """Only the fields sent change. `archived` archives or restores the list."""

    model_config = ConfigDict(extra="forbid")

    name: Name | None = None
    archived: bool | None = None

    @model_validator(mode="after")
    def _check(self) -> ListPatch:
        _says_what_changes(self, "name", "archived")
        return self


class ListPosition(BaseModel):
    """Right after the list `after_id` of the same board; null puts it first."""

    model_config = ConfigDict(extra="forbid")

    after_id: Id | None


class CardIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: Title


class CardPatch(BaseModel):
    """Only the fields sent change. `archived` archives or restores the card."""

    model_config = ConfigDict(extra="forbid")

    title: Title | None = None
    archived: bool | None = None

    @model_validator(mode="after")
    def _check(self) -> CardPatch:
        _says_what_changes(self, "title", "archived")
        return self


class CardPosition(BaseModel):
    """Into the list `list_id` of the same board, right after the card
    `after_id` of that list; null puts it on top."""

    model_config = ConfigDict(extra="forbid")

    list_id: Id
    after_id: Id | None


class CardOut(BaseModel):
    """What a card tile shows. `rank` sorts the cards of a list as plain text."""

    id: int
    list_id: int
    title: str
    rank: str
    due_at: str | None
    done_at: str | None
    cover_color: str | None
    created_at: str
    updated_at: str
    archived_at: str | None

    @classmethod
    def of(cls, card: service.Card) -> CardOut:
        return cls(
            id=card.id,
            list_id=card.list_id,
            title=card.title,
            rank=card.rank,
            due_at=card.due_at,
            done_at=card.done_at,
            cover_color=card.cover_color,
            created_at=card.created_at,
            updated_at=card.updated_at,
            archived_at=card.archived_at,
        )


class ListOut(BaseModel):
    """A list with its open cards in order."""

    id: int
    board_id: int
    name: str
    rank: str
    created_at: str
    archived_at: str | None
    cards: list[CardOut]

    @classmethod
    def of(cls, found: service.ListWithCards) -> ListOut:
        lst = found.row
        return cls(
            id=lst.id,
            board_id=lst.board_id,
            name=lst.name,
            rank=lst.rank,
            created_at=lst.created_at,
            archived_at=lst.archived_at,
            cards=[CardOut.of(card) for card in found.cards],
        )
