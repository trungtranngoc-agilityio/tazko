# Status

Where the project stands and what comes next. Read it at the start of a session; update it at the end of every task.
Task details live in docs/milestones/Mx.md, judgment calls in docs/decisions.md, milestone reports in docs/progress.md.

Updated 2026-11-19 · `dev` at 94d0862 (#12)

## Now

M1 · Platform (release 0.1.0) · task **M1-06** Admin console and company settings, part 4 of 5.

| Part | What | State |
|---|---|---|
| 1 | Members and invites API for company owners (D27) | merged, #9 |
| 2a, 2b | Console API: companies, invites, people, audit log, server, Workspace domains (D28, D29) | merged |
| 3 | Company screens: sidebar, switcher, Projects empty state, Company settings (D30) | merged, #12 |
| 4 | Console screens (6 pages) on the console API | **next** |
| 5 | Fake Google sign-in for e2e; `admin.spec.ts`; side-by-side check with the prototype | after part 4 |

## Next

1. M1-06 part 4: console screens. Open the matching screens in design/ first. Names, emails and audit targets come from Google profiles: render them as text only and test with a name like `<img src=x onerror=alert(1)>` (M1.md, security review).
2. M1-06 part 5: fake OIDC server, `admin.spec.ts`, prototype comparison of Company home, Company settings and the console (prototype-compare skill). Then tick M1-06.
3. M1-07 company lifecycle: create, suspend, resume, delete to `trash/`.
4. M1-08 deploy (parallel ok with M1-07): scripts in deploy/, the owner runs them. This also proves M1-01's last line (web on Pages reaches the API), so tick M1-01 then.
5. Cut `release/0.1.0`.

## Waiting on the owner

- Q2 (M1.md): list a suspended company in the switcher, greyed. Built that way (D30); still proposed.
- D23, D25, D27 to D30 are proposed, not decided.
- Real design tokens: design/tokens.css is still the placeholder, so colours and font differ from the prototype (M1.md, Visual check).

## Housekeeping

- The worktree `../tazko-wt/company-screens` belongs to a merged branch and can be removed: `git worktree remove ../tazko-wt/company-screens`.
