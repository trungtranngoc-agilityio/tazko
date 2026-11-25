# Status

Where the project stands and what comes next. Read it at the start of a session; update it at the end of every task.
Task details live in docs/milestones/Mx.md, judgment calls in docs/decisions.md, milestone reports in docs/progress.md.

Updated 2026-11-25 · `dev` at 58ff179 (#61) · open PRs #62 to #66 (stacked) and the Claude setup branch

## Now

M1 · Platform (release 0.1.0): every agent task is merged (M1-08 part 2 is #59). M1-01 and M1-08 stay unticked until the owner runs deploy/README.md "First time" on the host.

M2 · Core boards (release 0.2.0):
- M2-01 tenant schema and ranks: merged (#60).
- M2-02 projects and permissions (M2.md, "M2-02 parts"): parts 1 and 2 merged (#61). Part 3, project invites (D41), is PR #62 into `dev`: a new email joins the company as a plain member and sees only that project; a company member gets the project at their next request.
- Cleanup stacked on #62 (D42): #63 deprecated APIs, #64 backend modules by feature, #65 plain comments, #66 deploy comments. Each targets the PR below it.

## Next

1. Owner: merge #62 to #66 in order (see Housekeeping on stacked PRs); open Claude Code in this folder from now on (CLAUDE.md, How we work).
2. M2-02 part 4: screens (Your projects, Manage projects, Project members with the invite form and pending invites, Project settings), then the security agent; tick M2-02.
3. Owner: run deploy/README.md "First time" on the host; that proves M1-08's last lines and M1-01's (web on Pages reaches the API); tick both, then cut `release/0.1.0`. To ship 0.1.0 without the board tables, cut it from 36ea062 (the `dev` commit before M2-01); either way the release before tenant 0002 runs on a migrated file (D21).

## Waiting on the owner

- Q2 (M1.md): list a suspended company in the switcher, greyed. Built that way (D30); still proposed.
- D23, D25, D27 to D33 and D36 to D42 are proposed, not decided.
- Claude setup: turn off the plugins and connectors this project does not use (list in the Claude setup PR).
- Real design tokens: design/tokens.css is still the placeholder, so colours and font differ from the prototype (M1.md, Visual check).

## Housekeeping

- The worktree `../tazko-wt/company-screens` belongs to a merged branch and can be removed: `git worktree remove ../tazko-wt/company-screens`.
- Stacked PRs: merge the lower PR without deleting its branch, retarget the next PR to `dev`, then delete the branch. Deleting a base branch first makes GitHub close the PRs on it (it happened to #15; reopened).
