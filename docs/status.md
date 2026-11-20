# Status

Where the project stands and what comes next. Read it at the start of a session; update it at the end of every task.
Task details live in docs/milestones/Mx.md, judgment calls in docs/decisions.md, milestone reports in docs/progress.md.

Updated 2026-11-20 · `dev` at 60b9bb1 (#57) · M1-08 part 1 on `feature/backup-and-check`, not pushed

## Now

M1 · Platform (release 0.1.0) · task **M1-08** Deploy, part 1 of 2 in progress. M1-07 is done (#57).

| Part | What | State |
|---|---|---|
| 1 | `tazko backup`, `check`, `purge-trash`; rollback-safe migrations (D36) | committed on `feature/backup-and-check` |
| 2 | deploy/: host setup, tunnel rule, bundle, release.sh with pre-release backup and auto rollback, units, Pages deploy, README; deploy-reviewer | **next** |

## Next

1. M1-08 part 1: PR and merge.
2. M1-08 part 2: the deploy scripts; the owner runs them. This also proves M1-01's last line (web on Pages reaches the API), so tick M1-01 then.
3. Cut `release/0.1.0`.

## Waiting on the owner

- Q2 (M1.md): list a suspended company in the switcher, greyed. Built that way (D30); still proposed.
- D23, D25, D27 to D33 and D36 are proposed, not decided.
- Real design tokens: design/tokens.css is still the placeholder, so colours and font differ from the prototype (M1.md, Visual check).

## Housekeeping

- The worktree `../tazko-wt/company-screens` belongs to a merged branch and can be removed: `git worktree remove ../tazko-wt/company-screens`.
- Stacked PRs: merge the lower PR without deleting its branch, retarget the next PR to `dev`, then delete the branch. Deleting a base branch first makes GitHub close the PRs on it (it happened to #15; reopened).
