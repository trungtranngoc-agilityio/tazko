"""The project permission matrix: who may do what in a project.

Every cell is written out, not computed, so a change to the rules has to
change this table on purpose. "hide" answers 404 (the project does not exist
for them), "forbid" 403, "archived" 409 PROJECT_ARCHIVED.
"""

from __future__ import annotations

from typing import cast

import pytest

from tazko.modules.projects.access import ACTIONS, Action, ProjectRole, Standing, decide, sees_board

# (company role, project role) -> the standings the matrix covers.
OWNER_OUTSIDE = Standing("owner", None)
MEMBER_OUTSIDE = Standing("member", None)
PROJECT_OWNER = Standing("member", "owner")
PROJECT_MEMBER = Standing("member", "member")
OBSERVER = Standing("member", "observer")
COMPANY_OWNER_AS_MEMBER = Standing("owner", "member")
COMPANY_OWNER_AS_OBSERVER = Standing("owner", "observer")

WHO = {
    "company owner, not in project": OWNER_OUTSIDE,
    "company member, not in project": MEMBER_OUTSIDE,
    "project owner": PROJECT_OWNER,
    "project member": PROJECT_MEMBER,
    "observer": OBSERVER,
    "company owner, project member": COMPANY_OWNER_AS_MEMBER,
    "company owner, observer": COMPANY_OWNER_AS_OBSERVER,
}

# Switches at their defaults: members create boards, members do not invite.
MATRIX: dict[Action, dict[str, str]] = {
    "view": {
        "company owner, not in project": "allow",
        "company member, not in project": "hide",
        "project owner": "allow",
        "project member": "allow",
        "observer": "allow",
        "company owner, project member": "allow",
        "company owner, observer": "allow",
    },
    "list_members": {
        "company owner, not in project": "allow",
        "company member, not in project": "hide",
        "project owner": "allow",
        "project member": "allow",
        "observer": "allow",
        "company owner, project member": "allow",
        "company owner, observer": "allow",
    },
    "open_boards": {
        "company owner, not in project": "forbid",  # until they add themselves
        "company member, not in project": "hide",
        "project owner": "allow",
        "project member": "allow",
        "observer": "allow",
        "company owner, project member": "allow",
        "company owner, observer": "allow",
    },
    "manage": {  # rename, archive, restore, delete
        "company owner, not in project": "allow",
        "company member, not in project": "hide",
        "project owner": "forbid",
        "project member": "forbid",
        "observer": "forbid",
        "company owner, project member": "allow",
        "company owner, observer": "allow",
    },
    "edit_settings": {
        "company owner, not in project": "forbid",
        "company member, not in project": "hide",
        "project owner": "allow",
        "project member": "forbid",
        "observer": "forbid",
        "company owner, project member": "forbid",
        "company owner, observer": "forbid",
    },
    "manage_owners": {  # add, promote, demote or remove a project owner
        "company owner, not in project": "allow",
        "company member, not in project": "hide",
        "project owner": "allow",
        "project member": "forbid",
        "observer": "forbid",
        "company owner, project member": "allow",
        "company owner, observer": "allow",
    },
    "manage_members": {  # change or remove members and observers
        "company owner, not in project": "forbid",
        "company member, not in project": "hide",
        "project owner": "allow",
        "project member": "forbid",
        "observer": "forbid",
        "company owner, project member": "forbid",
        "company owner, observer": "forbid",
    },
    "add_member": {  # add a member or observer
        "company owner, not in project": "forbid",
        "company member, not in project": "hide",
        "project owner": "allow",
        "project member": "forbid",  # members_can_invite is off by default
        "observer": "forbid",
        "company owner, project member": "forbid",
        "company owner, observer": "forbid",
    },
    "create_board": {
        "company owner, not in project": "forbid",
        "company member, not in project": "hide",
        "project owner": "allow",
        "project member": "allow",  # members_can_create_boards is on by default
        "observer": "forbid",
        "company owner, project member": "allow",
        "company owner, observer": "forbid",
    },
    "edit_board": {  # rename, background, close and reopen a board
        "company owner, not in project": "forbid",
        "company member, not in project": "hide",
        "project owner": "allow",
        "project member": "allow",
        "observer": "forbid",
        "company owner, project member": "allow",
        "company owner, observer": "forbid",
    },
    "restrict_board": {  # restrict a board and choose who may open it
        "company owner, not in project": "forbid",
        "company member, not in project": "hide",
        "project owner": "allow",
        "project member": "forbid",
        "observer": "forbid",
        "company owner, project member": "forbid",
        "company owner, observer": "forbid",
    },
}

CELLS = [(action, who) for action, row in MATRIX.items() for who in row]


def test_the_matrix_covers_every_action_and_standing() -> None:
    assert set(MATRIX) == set(ACTIONS)
    assert all(set(row) == set(WHO) for row in MATRIX.values())


@pytest.mark.parametrize(("action", "who"), CELLS)
def test_permission_matrix(action: Action, who: str) -> None:
    assert decide(WHO[who], action) == MATRIX[action][who]


@pytest.mark.parametrize("who", ["project member", "company owner, project member"])
def test_members_invite_when_the_project_allows_it(who: str) -> None:
    assert decide(WHO[who], "add_member", members_can_invite=True) == "allow"
    assert decide(OBSERVER, "add_member", members_can_invite=True) == "forbid"


def test_members_cannot_create_boards_when_the_project_says_so() -> None:
    assert decide(PROJECT_MEMBER, "create_board", members_can_create_boards=False) == "forbid"
    assert decide(PROJECT_OWNER, "create_board", members_can_create_boards=False) == "allow"


READS = {"view", "list_members", "open_boards"}


@pytest.mark.parametrize(("action", "who"), CELLS)
def test_an_archived_project_allows_only_reads_and_its_management(action: Action, who: str) -> None:
    expected = MATRIX[action][who]
    if expected == "allow" and action not in READS | {"manage"}:
        expected = "archived"
    assert decide(WHO[who], action, archived=True) == expected


@pytest.mark.parametrize(
    ("role", "restricted", "listed", "sees"),
    [
        ("owner", False, False, True),
        ("owner", True, False, True),  # project owners manage restricted boards
        ("member", False, False, True),
        ("member", True, False, False),  # restricted boards hide from unlisted members
        ("member", True, True, True),
        ("observer", True, False, False),
        ("observer", True, True, True),
        (None, False, False, False),  # not in the project: no board at all
    ],
)
def test_who_sees_a_board(role: str | None, restricted: bool, listed: bool, sees: bool) -> None:
    assert sees_board(cast(ProjectRole | None, role), restricted=restricted, listed=listed) is sees
