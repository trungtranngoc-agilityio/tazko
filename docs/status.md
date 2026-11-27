# Status

Where the project stands and what comes next. Read it at the start of a session; update it at the end of every task.
Task details live in docs/milestones/Mx.md, judgment calls in docs/decisions.md, milestone reports in docs/progress.md.

Updated 2026-11-27 · `dev` at fed5260 · M2-03 part 3c split in three stacked local branches (3c, 3d, 3e), not pushed

## Now

M1 · Platform (release 0.1.0): every agent task is merged (M1-08 part 2 is #59). M1-01 and M1-08 stay unticked until the owner runs deploy/README.md "First time" on the host.

M2 · Core boards (release 0.2.0):
- M2-01 tenant schema and ranks: merged (#60).
- M2-02 projects and permissions: every part merged (#61, #62, cleanup #63 to #67, screens #68 to #71).
- M2-03 board UI, in parts (M2.md, "M2-03 parts", D44 to D46, D48). Parts 1 to 3b merged (#72 to #76, #79).
  - The board actions, split in three at the owner's request after review, each stacked on the one before (M2.md, "M2-03 parts"):
    - 3c `feature/list-archive` (from `dev`, about 330 lines): the shared panel and note, archive a list from its menu with Undo.
    - 3d `feature/board-star-close` (on 3c, about 170 lines): star the board; the board menu with Close board.
    - 3e `feature/board-access` (on 3d, about 410 lines, most of it tests): the access chip and Board access panel, also from the board menu.
  - Each branch: scripts/ci.sh green, e2e `board.spec.ts` passes in both themes (installed Chrome; 3e also `projects.spec.ts`). Visual check done in both themes (M2.md table). The reviewer agent ran on the combined change before the split; fixed: a closed board offered owners the access switch, a late star overwrote an access change, a refused Undo lost its note, an unused string, Escape in a field closed a panel; the one-note Undo is in D48. Not fixed (nits): focus does not return to the button that opened a panel; the board menu ignores a press outside. The reviewer did not see the split branches on their own.
  - `feature/board-actions` is the combined branch before the split; 3e has the same code. It was never pushed and can be deleted.

## Next

1. Owner: push the three branches and open stacked PRs: 3c into `dev`, 3d into 3c, 3e into 3d; merge in that order, retargeting the next PR to `dev` before deleting each branch (see Housekeeping). Delete the merged branches `feature/board-screen`, `feature/board-editing` and `feature/board-editing-on-dev`.
2. M2-03 part 4: drag and drop of cards and lists, with the e2e (observers cannot drag); closes the M2-03 issue.
3. Owner: run deploy/README.md "First time" on the host; that proves M1-08's last lines and M1-01's (web on Pages reaches the API); tick both, then cut `release/0.1.0`. To ship 0.1.0 without the board tables, cut it from 36ea062 (the `dev` commit before M2-01); either way the release before tenant 0002 runs on a migrated file (D21).

## Waiting on the owner

- Q2 (M1.md): list a suspended company in the switcher, greyed. Built that way (D30); still proposed.
- D23, D25, D27 to D33, D36 to D46 and D48 are proposed, not decided.
- Claude setup: turn off the plugins and connectors this project does not use (list in the Claude setup PR).
- Real design tokens: design/tokens.css is still the placeholder, so colours and font differ from the prototype (M1.md, Visual check).

## Housekeeping

- A Google stand-in (`node tests/e2e/fake-google.mjs`) from an earlier e2e run still holds port 8792 in a VS Code terminal; `npx playwright test` refuses to start until it is stopped.

- The worktree `../tazko-wt/company-screens` belongs to a merged branch and can be removed: `git worktree remove ../tazko-wt/company-screens`.
- Local `dev` in the main checkout is behind `origin/dev` (a593f70 against 0b29803); pull it before using it as a review base.
- Screenshots for the visual check were taken with tools/h.mjs, which starts headless Chrome on ports 9361 and 9362 and may leave those processes running; they could not be listed from this session.
- Stacked PRs: merge the lower PR without deleting its branch, retarget the next PR to `dev`, then delete the branch. Deleting a base branch first makes GitHub close the PRs on it (it happened to #15; reopened).
