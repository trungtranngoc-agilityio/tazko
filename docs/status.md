# Status

Where the project stands and what comes next. Read it at the start of a session; update it at the end of every task.
Task details live in docs/milestones/Mx.md, judgment calls in docs/decisions.md, milestone reports in docs/progress.md.

Updated 2026-11-19 · `dev` at 5efe872 (#19) · icons on `feature/prototype-icons`

## Now

M1 · Platform (release 0.1.0) · task **M1-06** Admin console and company settings: done and ticked (D34). Next task: **M1-07**.

| Part | What | State |
|---|---|---|
| 1 | Members and invites API for company owners (D27) | merged, #9 |
| 2a, 2b | Console API: companies, invites, people, audit log, server, Workspace domains (D28, D29) | merged |
| 3 | Company screens: sidebar, switcher, Projects empty state, Company settings (D30) | merged, #12 |
| 4 | Console screens (6 pages) on the console API (D31) | merged, #14 to #17 |
| 5 | Stand-in Google for e2e (D32); `admin.spec.ts`; prototype comparison (M1.md, Visual check; D33) | merged, #19 |
| + | Prototype icons, avatar tones, 44 px header badge (D34) | `feature/prototype-icons` |

## Next

1. Merge `feature/prototype-icons` (closes M1-06).
2. M1-07 company lifecycle: create, suspend, resume, delete to `trash/`.
3. M1-08 deploy (parallel ok with M1-07): scripts in deploy/, the owner runs them. This also proves M1-01's last line (web on Pages reaches the API), so tick M1-01 then.
4. Cut `release/0.1.0`.

## Waiting on the owner

- Q2 (M1.md): list a suspended company in the switcher, greyed. Built that way (D30); still proposed.
- D23, D25, D27 to D33 are proposed, not decided.
- Real design tokens: design/tokens.css is still the placeholder, so colours and font differ from the prototype (M1.md, Visual check).

## Housekeeping

- The worktree `../tazko-wt/company-screens` belongs to a merged branch and can be removed: `git worktree remove ../tazko-wt/company-screens`.
- Stacked PRs: merge the lower PR without deleting its branch, retarget the next PR to `dev`, then delete the branch. Deleting a base branch first makes GitHub close the PRs on it (it happened to #15; reopened).
