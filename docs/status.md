# Status

Where the project stands and what comes next. Read it at the start of a session; update it at the end of every task.
Task details live in docs/milestones/Mx.md, judgment calls in docs/decisions.md, milestone reports in docs/progress.md.

Updated 2026-11-26 · `dev` at a593f70 (#71) · M2-03 part 1 in PR #72; part 2 split into three stacked branches, not pushed

## Now

M1 · Platform (release 0.1.0): every agent task is merged (M1-08 part 2 is #59). M1-01 and M1-08 stay unticked until the owner runs deploy/README.md "First time" on the host.

M2 · Core boards (release 0.2.0):
- M2-01 tenant schema and ranks: merged (#60).
- M2-02 projects and permissions: every part merged (#61, #62, cleanup #63 to #67, screens #68 to #71).
- M2-03 board UI, in parts (M2.md, "M2-03 parts", D44, D45). Part 1, the lists and cards API, is PR #72 into `dev` (about 1,250 lines; the owner kept it as one PR). Part 2 was split at the owner's request into three stacked branches, each committed, not pushed: 2a `feature/board-tile-counts` (tile counts and `GET /starred-boards`, on part 1), 2b `feature/boards-tab` (the Boards tab, on 2a), 2c `feature/starred-boards` (Starred boards on Your projects, on 2b).

## Next

1. Owner: merge PR #72, then push and open PRs for 2a, 2b and 2c in that order (each into `dev` once the one below has merged; see Housekeeping on stacked PRs).
2. M2-03 part 3: the board screen (lists and card tiles, add list and card, rename, archive a list, star, close, the access dialog), and board tiles open it.
3. M2-03 part 4: drag and drop of cards and lists, with the e2e (observers cannot drag); closes the M2-03 issue.
4. Owner: run deploy/README.md "First time" on the host; that proves M1-08's last lines and M1-01's (web on Pages reaches the API); tick both, then cut `release/0.1.0`. To ship 0.1.0 without the board tables, cut it from 36ea062 (the `dev` commit before M2-01); either way the release before tenant 0002 runs on a migrated file (D21).

## Waiting on the owner

- Q2 (M1.md): list a suspended company in the switcher, greyed. Built that way (D30); still proposed.
- D23, D25, D27 to D33 and D36 to D45 are proposed, not decided.
- Claude setup: turn off the plugins and connectors this project does not use (list in the Claude setup PR).
- Real design tokens: design/tokens.css is still the placeholder, so colours and font differ from the prototype (M1.md, Visual check).

## Housekeeping

- A Google stand-in (`node tests/e2e/fake-google.mjs`) from an earlier e2e run still holds port 8792 in a VS Code terminal; `npx playwright test` refuses to start until it is stopped.

- The worktree `../tazko-wt/company-screens` belongs to a merged branch and can be removed: `git worktree remove ../tazko-wt/company-screens`.
- Stacked PRs: merge the lower PR without deleting its branch, retarget the next PR to `dev`, then delete the branch. Deleting a base branch first makes GitHub close the PRs on it (it happened to #15; reopened).
