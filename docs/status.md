# Status

Where the project stands and what comes next. Read it at the start of a session; update it at the end of every task.
Task details live in docs/milestones/Mx.md, judgment calls in docs/decisions.md, milestone reports in docs/progress.md.

Updated 2026-11-20 · `dev` at 823f26d (#20) · M1-07 on `feature/company-lifecycle`, not pushed

## Now

M1 · Platform (release 0.1.0) · task **M1-07** Company lifecycle: built and ticked on `feature/company-lifecycle` (D35). M1-06 is done (#9 to #20).

- Super admins suspend, resume and delete a company on Company detail; delete moves the folder to `data/trash/`.
- A member whose companies are all suspended is refused at sign-in and told why.

## Next

1. Merge `feature/company-lifecycle` (M1-07).
2. M1-08 deploy: scripts in deploy/, the owner runs them; includes the nightly job that removes trash older than 30 days (D35). This also proves M1-01's last line (web on Pages reaches the API), so tick M1-01 then.
3. Cut `release/0.1.0`.

## Waiting on the owner

- Q2 (M1.md): list a suspended company in the switcher, greyed. Built that way (D30); still proposed.
- D23, D25, D27 to D33 and D35 are proposed, not decided.
- Real design tokens: design/tokens.css is still the placeholder, so colours and font differ from the prototype (M1.md, Visual check).

## Housekeeping

- The worktree `../tazko-wt/company-screens` belongs to a merged branch and can be removed: `git worktree remove ../tazko-wt/company-screens`.
- Stacked PRs: merge the lower PR without deleting its branch, retarget the next PR to `dev`, then delete the branch. Deleting a base branch first makes GitHub close the PRs on it (it happened to #15; reopened).
