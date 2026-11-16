# Git workflow (D18)

## Branches
A branch name says what kind of change it is and what it does, in a few lowercase words joined by
hyphens. No milestone or task ids in the name (`m1`, `m1-04`): those go in the commit footer and the PR.

| Branch | For | Cut from | Merges into | Example |
|---|---|---|---|---|
| `main` | production history; PRs only, CI green, only the owner merges | | | |
| `release/<version>` | the integration branch of one milestone, until it ships | `main` | `main` (merge commit, then tag `v<version>`) | `release/0.1.0` (M1) |
| `feature/<what>` | a new capability or task | the open release branch | the release branch (squash) | `feature/google-signin` |
| `fix/<what>` | a bug or a review finding not yet released | the open release branch | the release branch (squash) | `fix/security-hardening` |
| `refactor/<what>` | a change in structure with no change in behaviour | the open release branch | the release branch (squash) | `refactor/error-contract` |
| `hotfix/<what>` | a bug in production | `main` | `main`, then `main` is merged into the open release branch | `hotfix/session-expiry` |
| `docs/<what>` | docs, rules, templates or agent setup only, no code | the open release branch | the release branch (squash) | `docs/pr-template` |

- The version of each milestone is set in docs/milestones/Mx.md (M1 is 0.1.0, M2 is 0.2.0, ...).
- Tooling, CI and dependency changes are a `feature/` (new check or tool) or a `fix/` (broken one).
  There is no `chore/` branch.
- Never commit straight to a release branch or to `main`.

## Parallel work
- Tasks marked "parallel ok" in docs/milestones/Mx.md each run in their own git worktree: `git worktree add ../tazko-wt/<branch> -b <branch> <release-branch>`.
- Two agents never share a working folder. Reserve migration numbers in the milestone file before parallel tasks start.
- Remove the worktree after its branch merges: `git worktree remove ../tazko-wt/<branch>`.

## Commits
- Conventional Commits: `<type>(<scope>): <summary>`, imperative, under 72 characters.
  Types: feat, fix, refactor, perf, test, docs, ci, build (dependencies, packaging), release (version bump
  and changelog on a release branch). Scope: the module or area, for example auth, db, orgs, admin, api, backend, web, deploy, ci, claude.
- Body: what and why, wrapped at 72. Footer `Task: M1-04` when the work belongs to a task.
- No AI attribution lines (D11).
- `scripts/ci.sh` is green before every commit.

## Pull requests
- Title: the Conventional Commit line, e.g. `feat(auth): sign in with Google`.
- Task PRs go into the open release branch and are squash-merged by the owner, branch deleted after
  merge. The squash commit message is the PR title plus the description's Purpose.
- Fill every section of .github/pull_request_template.md with real content. A reader must see in a
  minute what the PR is for, what changed, what to test and what the tests showed. No placeholders,
  no empty tables: write "none" and why.
- Size: about 400 changed lines, not counting lock files and generated files. A PR touching more than
  three concerns is split.
- Before asking for the merge: CI green, the reviewer agents for the touched areas ran (see
  code-review.md), every finding answered.

## Releases
- Before `release/<version>` merges into `main`, a `release(<version>)` commit on it bumps `backend/pyproject.toml` and `frontend/package.json` (0.MINOR.PATCH while pre-1.0: a milestone bumps MINOR, a hotfix bumps PATCH) and moves the CHANGELOG lines under the version; the owner tags `v<version>` on `main` after the merge.
- CHANGELOG.md (Keep a Changelog): every PR that changes what a person sees or what the API returns adds a line under `[Unreleased]`; the release moves them under the version.
- A release that has to be rolled back: open the issue, add a regression test, then release again.
