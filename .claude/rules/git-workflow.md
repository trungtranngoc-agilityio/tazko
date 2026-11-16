# Git workflow (D18)

## Branches
- `main`: production history. PRs only, CI green. Only the owner merges.
- `milestone/<id>-<name>` (e.g. `milestone/m1-skeleton`): the integration branch for one milestone. A PR into `main` when the milestone is done; the owner merges it with a merge commit so each task stays one commit in history.
- One branch per piece of work, cut from the milestone branch:
  - `feat/<task-id>-<slug>` new task (`feat/m1-04-google-signin`)
  - `fix/<slug>` bug or review finding, `refactor/<slug>`, `chore/<slug>` (tooling, setup), `docs/<slug>`
  - `hotfix/<slug>` from `main` for a production bug; after it merges, merge `main` back into the open milestone branch.
- Never commit straight to a milestone branch or to `main`.

## Parallel work
- Tasks marked "parallel ok" in docs/milestones/Mx.md each run in their own git worktree: `git worktree add ../tazko-wt/<branch> -b <branch> <milestone-branch>`.
- Two agents never share a working folder. Reserve migration numbers in the milestone file before parallel tasks start.
- Remove the worktree after its branch merges: `git worktree remove ../tazko-wt/<branch>`.

## Commits
- Conventional Commits: `<type>(<scope>): <summary>`, imperative, under 72 characters.
  Types: feat, fix, refactor, perf, test, docs, chore, ci. Scope: the module or area (auth, db, orgs, admin, web, deploy, claude).
- Body: what and why, wrapped at 72. Footer `Task: M1-04` when the work belongs to a task.
- No AI attribution lines (D11).
- `scripts/ci.sh` is green before every commit.

## Pull requests
- Into the milestone branch, squash-merged by the owner, branch deleted after merge. The squash commit message is the PR title (Conventional Commit format) plus the description's What.
- Fill .github/pull_request_template.md: what, why, how to test, the "Done when" tests it proves, the reviewer agents that ran and their outcome.
- Size: about 400 changed lines, not counting lock files and generated files. A PR touching more than three concerns is split.
- Before asking for the merge: CI green, the reviewer agents for the touched areas ran (see code-review.md), every finding answered.

## Releases
- When a milestone merges into `main`, bump `backend/pyproject.toml` and `frontend/package.json` (0.MINOR.PATCH while pre-1.0: a milestone bumps MINOR, a hotfix bumps PATCH) and tag `vX.Y.Z` on `main`.
- CHANGELOG.md (Keep a Changelog): every PR that changes what a person sees or what the API returns adds a line under `[Unreleased]`; the release moves them under the version.
- A release that has to be rolled back: open the issue, add a regression test, then release again.
