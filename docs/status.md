# Status

Where the project stands and what comes next. Read it at the start of a session; update it at the end of every task.
Task details live in docs/milestones/Mx.md, judgment calls in docs/decisions.md, milestone reports in docs/progress.md.

Updated 2026-11-23 · `dev` at 36ea062 (#59) · M2-01 on `feature/board-schema`, not pushed

## Now

M1 · Platform (release 0.1.0): every agent task is merged (M1-08 part 2 is #59). M1-01 and M1-08 stay unticked until the owner runs deploy/README.md "First time" on the host.

M2 · Core boards (release 0.2.0) · task **M2-01** Tenant schema and ranks, on `feature/board-schema`: tenant migration `0002_boards` (projects, members, boards, access, stars, lists, cards, labels, card members and watchers) and `tazko/db/rank.py` (fractional ranks with rebalance, D38). Local commit only.

## Next

1. M2-01: PR into `dev` and merge.
2. Owner: run deploy/README.md "First time" on the host; that proves M1-08's last lines and M1-01's (web on Pages reaches the API); tick both, then cut `release/0.1.0`.
3. M2-02: projects and server-side permissions, with the full permission matrix and the security agent after.

## Waiting on the owner

- Q2 (M1.md): list a suspended company in the switcher, greyed. Built that way (D30); still proposed.
- D23, D25, D27 to D33 and D36 to D38 are proposed, not decided.
- Real design tokens: design/tokens.css is still the placeholder, so colours and font differ from the prototype (M1.md, Visual check).

## Housekeeping

- The worktree `../tazko-wt/company-screens` belongs to a merged branch and can be removed: `git worktree remove ../tazko-wt/company-screens`.
- Stacked PRs: merge the lower PR without deleting its branch, retarget the next PR to `dev`, then delete the branch. Deleting a base branch first makes GitHub close the PRs on it (it happened to #15; reopened).
