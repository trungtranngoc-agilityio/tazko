# Status

Where the project stands and what comes next. Read it at the start of a session; update it at the end of every task.
Task details live in docs/milestones/Mx.md, judgment calls in docs/decisions.md, milestone reports in docs/progress.md.

Updated 2026-11-26 · `dev` at a593f70 (#71) · M2-03 part 1 on `feature/board-lists-and-cards`, not pushed

## Now

M1 · Platform (release 0.1.0): every agent task is merged (M1-08 part 2 is #59). M1-01 and M1-08 stay unticked until the owner runs deploy/README.md "First time" on the host.

M2 · Core boards (release 0.2.0):
- M2-01 tenant schema and ranks: merged (#60).
- M2-02 projects and permissions: every part merged (#61, #62, cleanup #63 to #67, screens #68 to #71).
- M2-03 board UI, in three parts (M2.md, "M2-03 parts", D44). Part 1, the lists and cards API (new module `cards`, action `edit_cards`), is on `feature/board-lists-and-cards`, committed, not pushed; reviewer findings answered (about 1,250 lines, over the 400 guideline; the owner kept it as one PR on 2026-11-26).

## Next

1. Owner: push `feature/board-lists-and-cards` and open its PR into `dev` (Task M2-03 part 1; does not close the M2-03 issue yet).
2. M2-03 part 2: the board screen (Boards tab, Starred boards, lists and card tiles, composers, rename, archive), on the part 1 API.
3. M2-03 part 3: drag and drop of cards and lists, with the e2e (observers cannot drag); closes the M2-03 issue.
4. Owner: run deploy/README.md "First time" on the host; that proves M1-08's last lines and M1-01's (web on Pages reaches the API); tick both, then cut `release/0.1.0`. To ship 0.1.0 without the board tables, cut it from 36ea062 (the `dev` commit before M2-01); either way the release before tenant 0002 runs on a migrated file (D21).

## Waiting on the owner

- Q2 (M1.md): list a suspended company in the switcher, greyed. Built that way (D30); still proposed.
- D23, D25, D27 to D33 and D36 to D44 are proposed, not decided.
- Claude setup: turn off the plugins and connectors this project does not use (list in the Claude setup PR).
- Real design tokens: design/tokens.css is still the placeholder, so colours and font differ from the prototype (M1.md, Visual check).

## Housekeeping

- The worktree `../tazko-wt/company-screens` belongs to a merged branch and can be removed: `git worktree remove ../tazko-wt/company-screens`.
- Stacked PRs: merge the lower PR without deleting its branch, retarget the next PR to `dev`, then delete the branch. Deleting a base branch first makes GitHub close the PRs on it (it happened to #15; reopened).
