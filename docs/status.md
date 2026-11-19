# Status

Where the project stands and what comes next. Read it at the start of a session; update it at the end of every task.
Task details live in docs/milestones/Mx.md, judgment calls in docs/decisions.md, milestone reports in docs/progress.md.

Updated 2026-11-19 · `dev` at 1ec6b8a (#18) · part 5 on `feature/e2e-fake-google`, not pushed

## Now

M1 · Platform (release 0.1.0) · task **M1-06** Admin console and company settings: all five parts built; ticked once the owner accepts the visual gaps (D34).

| Part | What | State |
|---|---|---|
| 1 | Members and invites API for company owners (D27) | merged, #9 |
| 2a, 2b | Console API: companies, invites, people, audit log, server, Workspace domains (D28, D29) | merged |
| 3 | Company screens: sidebar, switcher, Projects empty state, Company settings (D30) | merged, #12 |
| 4 | Console screens (6 pages) on the console API (D31) | merged, #14 to #17 |
| 5 | Stand-in Google for e2e (D32); `admin.spec.ts`; prototype comparison (M1.md, Visual check; D33) | committed on `feature/e2e-fake-google`, PR waits for the owner |

## Next

1. M1-06 part 5: open the PR for `feature/e2e-fake-google` and merge it.
2. Owner: decide D34. Then icons in the sidebars and buttons, avatar tones and the header badge (a small UI task), and tick M1-06.
3. M1-07 company lifecycle: create, suspend, resume, delete to `trash/`.
4. M1-08 deploy (parallel ok with M1-07): scripts in deploy/, the owner runs them. This also proves M1-01's last line (web on Pages reaches the API), so tick M1-01 then.
5. Cut `release/0.1.0`.

## Waiting on the owner

- Q2 (M1.md): list a suspended company in the switcher, greyed. Built that way (D30); still proposed.
- D23, D25, D27 to D34 are proposed, not decided. D34 decides whether M1-06 can be ticked.
- Real design tokens: design/tokens.css is still the placeholder, so colours and font differ from the prototype (M1.md, Visual check).

## Housekeeping

- The worktree `../tazko-wt/company-screens` belongs to a merged branch and can be removed: `git worktree remove ../tazko-wt/company-screens`.
- Stacked PRs: merge the lower PR without deleting its branch, retarget the next PR to `dev`, then delete the branch. Deleting a base branch first makes GitHub close the PRs on it (it happened to #15; reopened).
