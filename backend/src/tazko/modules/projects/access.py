"""Who may do what in a project: one pure function, so the whole matrix is
tested in one place (tests/unit/test_project_access.py) and every service asks it.

Outside the project and not a company owner: "hide" (404), so the project's
existence never leaks. Company owners manage every project (and its owners)
but open its boards and change its settings only once in it. Members create
boards and add people only when the project's switches allow it; observers
only read. An archived project is read-only until a company owner restores it.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

CompanyRole = Literal["owner", "member"]
ProjectRole = Literal["owner", "member", "observer"]
Decision = Literal["allow", "forbid", "hide", "archived"]
Action = Literal[
    "view",  # the project, its settings as read-only
    "list_members",
    "open_boards",
    "manage",  # rename, archive, restore, delete (company owners)
    "edit_settings",
    "manage_owners",  # add, promote, demote or remove a project owner
    "manage_members",  # change or remove members and observers
    "add_member",  # add a member or observer
    "create_board",
    "edit_board",  # rename, background, close and reopen a board
    "edit_cards",  # add, rename, move, archive and restore lists and cards
    "restrict_board",  # restrict a board and choose who may open it
]
ACTIONS: tuple[Action, ...] = (
    "view",
    "list_members",
    "open_boards",
    "manage",
    "edit_settings",
    "manage_owners",
    "manage_members",
    "add_member",
    "create_board",
    "edit_board",
    "edit_cards",
    "restrict_board",
)
# Still allowed on an archived project.
READS: frozenset[Action] = frozenset({"view", "list_members", "open_boards", "manage"})


@dataclass(frozen=True)
class Standing:
    company_role: CompanyRole
    project_role: ProjectRole | None


def decide(
    standing: Standing,
    action: Action,
    *,
    archived: bool = False,
    members_can_invite: bool = False,
    members_can_create_boards: bool = True,
) -> Decision:
    company_owner = standing.company_role == "owner"
    role = standing.project_role
    if role is None and not company_owner:
        return "hide"
    allowed = _allowed(
        company_owner,
        role,
        action,
        members_can_invite=members_can_invite,
        members_can_create_boards=members_can_create_boards,
    )
    if not allowed:
        return "forbid"
    if archived and action not in READS:
        return "archived"
    return "allow"


def _allowed(
    company_owner: bool,
    role: ProjectRole | None,
    action: Action,
    *,
    members_can_invite: bool,
    members_can_create_boards: bool,
) -> bool:
    if action in ("view", "list_members"):
        return True
    if action in ("manage", "manage_owners") and company_owner:
        return True
    if action == "manage":
        return False
    if role == "owner":
        return True
    if role == "member":
        return action in ("open_boards", "edit_board", "edit_cards") or (
            (action == "add_member" and members_can_invite)
            or (action == "create_board" and members_can_create_boards)
        )
    return action == "open_boards" and role == "observer"


def sees_board(role: ProjectRole | None, *, restricted: bool, listed: bool) -> bool:
    """Whether someone with project role `role` may see a board at all. A
    restricted board shows only to the project's owners (who manage it) and
    the people on its list; to anyone else it does not exist (404,
    the prototype leaked it). Company owners outside the project see no board."""
    if role is None:
        return False
    return role == "owner" or not restricted or listed
