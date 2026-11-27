# Status

Where the project stands and what comes next. Read it at the start of a session; update it at the end of every task.
Task details live in docs/milestones/Mx.md, judgment calls in docs/decisions.md, milestone reports in docs/progress.md.

Updated 2026-11-27 · `dev` at 0b29803 (#75) · M2-03 part 3a in PR #76 (`feature/board-screen` into `dev`), part 3b in stacked PR #77 (`feature/board-editing` into `feature/board-screen`)

## Now

M1 · Platform (release 0.1.0): every agent task is merged (M1-08 part 2 is #59). M1-01 and M1-08 stay unticked until the owner runs deploy/README.md "First time" on the host.

M2 · Core boards (release 0.2.0):
- M2-01 tenant schema and ranks: merged (#60).
- M2-02 projects and permissions: every part merged (#61, #62, cleanup #63 to #67, screens #68 to #71).
- M2-03 board UI, in parts (M2.md, "M2-03 parts", D44 to D46). Parts 1 and 2 merged (#72 to #75). Part 3 is the board screen, frontend only, split in three at the owner's request after review (D46):
  - 3a PR #76, `feature/board-screen` (from `dev`, about 740 lines with tests): board tiles open the board; lists and card tiles; collapse; read-only notes for observers, a closed board (Reopen for owners and members) and an archived project; a refused or missing board shows a way back.
  - 3b PR #77, `feature/board-editing` (on 3a, about 760 lines with tests and the e2e): add a list and a card, rename the board and a list in place; the visual check shots and table row.
  - Both: scripts/ci.sh green on each branch; e2e `board.spec.ts` and `projects.spec.ts` pass in both themes on 3b (run with installed Chrome); not run on 3a alone. The reviewer agent ran on the combined change before the split. Fixed: 403 shows a way back without Try again; Enter while an input method composes does nothing; an observer on a closed board is not told to reopen; tests for the collapsed count, card order, refused card add and rename; D46 wording; Reopen is disabled while busy. The size finding was answered by the split. The reviewer did not see the split branches on their own.
  - 3c (archive a list with Undo, star, Close board, Board access dialog) is not started.

## Next

1. Owner: review and merge #76, then retarget #77 to `dev` before deleting `feature/board-screen` (Housekeeping, stacked PRs), then merge #77. GitHub CI was still running on both when they were opened.
2. M2-03 part 3c on a branch cut from `feature/board-editing`: archive a list with Undo, star, Close board in the board menu, and the Board access dialog (project owners restrict a board to chosen members; it needs `GET .../members`).
3. M2-03 part 4: drag and drop of cards and lists, with the e2e (observers cannot drag); closes the M2-03 issue.
4. Owner: run deploy/README.md "First time" on the host; that proves M1-08's last lines and M1-01's (web on Pages reaches the API); tick both, then cut `release/0.1.0`. To ship 0.1.0 without the board tables, cut it from 36ea062 (the `dev` commit before M2-01); either way the release before tenant 0002 runs on a migrated file (D21).

## Waiting on the owner

- Q2 (M1.md): list a suspended company in the switcher, greyed. Built that way (D30); still proposed.
- D23, D25, D27 to D33 and D36 to D46 are proposed, not decided.
- Claude setup: turn off the plugins and connectors this project does not use (list in the Claude setup PR).
- Real design tokens: design/tokens.css is still the placeholder, so colours and font differ from the prototype (M1.md, Visual check).

## Housekeeping

- A Google stand-in (`node tests/e2e/fake-google.mjs`) from an earlier e2e run still holds port 8792 in a VS Code terminal; `npx playwright test` refuses to start until it is stopped.

- The worktree `../tazko-wt/company-screens` belongs to a merged branch and can be removed: `git worktree remove ../tazko-wt/company-screens`.
- Local `dev` in the main checkout is behind `origin/dev` (a593f70 against 0b29803); pull it before using it as a review base.
- Screenshots for the visual check were taken with tools/h.mjs, which starts headless Chrome on ports 9361 and 9362 and may leave those processes running; they could not be listed from this session.
- Stacked PRs: merge the lower PR without deleting its branch, retarget the next PR to `dev`, then delete the branch. Deleting a base branch first makes GitHub close the PRs on it (it happened to #15; reopened).
