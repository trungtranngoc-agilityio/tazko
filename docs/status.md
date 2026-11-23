# Status

Where the project stands and what comes next. Read it at the start of a session; update it at the end of every task.
Task details live in docs/milestones/Mx.md, judgment calls in docs/decisions.md, milestone reports in docs/progress.md.

Updated 2026-11-23 · `dev` at 36ea062 (#59) · M2-01 in PR #60 · M2-02 parts 1 and 2 on `feature/project-permissions` (stacked on `feature/board-schema`), not pushed

## Now

M1 · Platform (release 0.1.0): every agent task is merged (M1-08 part 2 is #59). M1-01 and M1-08 stay unticked until the owner runs deploy/README.md "First time" on the host.

M2 · Core boards (release 0.2.0):
- M2-01 tenant schema and ranks: PR #60, CI green, waiting for merge.
- M2-02 projects and permissions, parts 1 and 2 of 4 (M2.md, "M2-02 parts"): projects and project members with the permission matrix (D39); boards, restricted boards and stars (D40). Local commits, stacked on M2-01.

## Next

1. Merge #60, then open the M2-02 PR for parts 1 and 2 (retarget it to `dev` once #60 is in; see Housekeeping on stacked PRs).
2. M2-02 part 3: project invites (a new email joins the company and sees only that project).
3. Owner: run deploy/README.md "First time" on the host; that proves M1-08's last lines and M1-01's (web on Pages reaches the API); tick both, then cut `release/0.1.0`. To ship 0.1.0 without the board tables, cut it from 36ea062 (the `dev` commit before M2-01); either way the release before tenant 0002 runs on a migrated file (D21).

## Waiting on the owner

- Q2 (M1.md): list a suspended company in the switcher, greyed. Built that way (D30); still proposed.
- D23, D25, D27 to D33 and D36 to D40 are proposed, not decided.
- Real design tokens: design/tokens.css is still the placeholder, so colours and font differ from the prototype (M1.md, Visual check).

## Housekeeping

- The worktree `../tazko-wt/company-screens` belongs to a merged branch and can be removed: `git worktree remove ../tazko-wt/company-screens`.
- Stacked PRs: merge the lower PR without deleting its branch, retarget the next PR to `dev`, then delete the branch. Deleting a base branch first makes GitHub close the PRs on it (it happened to #15; reopened).
