<!--
Title: the Conventional Commit line, e.g. `feat(auth): sign in with Google`.
Every section is filled with real content. Nothing to say? Write "none" and why. Delete these comments.
-->

## Purpose

<!-- One or two sentences a non-developer understands: what problem this solves, for whom.
     Then the task or finding: "Task: M1-04" / "Security review finding 3" / "Decision D19". -->

## Changes

<!-- What is different after this PR, grouped by area. Behaviour first, files second.
     Mark anything the API or a person sees, and anything that needs a config or deploy step. -->

**Backend**
-

**Frontend**
-

**Docs and rules**
-

**Breaking or needs action:** none

## How to test

<!-- Steps a reviewer can follow, each with the result they should see. -->

| # | Do this | Expect |
|---|---|---|
| 1 | `bash scripts/ci.sh` | `ci: all green` |
| 2 |  |  |

## Test results

<!-- What was actually run on this branch, and what came out. -->

| Check | Result |
|---|---|
| `scripts/ci.sh` (lint, types, unit + integration, licenses) | ✅ / ❌ — N passed, N skipped (why) |
| Backend branch coverage (floor 92%) |  % |
| e2e `npx playwright test` | ✅ / ❌ / not needed (why) |
| GitHub CI | link or status |
| Manual check | what you tried and what you saw, or "none" |

New or changed tests:

| Proves | Test |
|---|---|
|  | `file::test_name` |

## Review

| Agent | Result |
|---|---|
| reviewer |  |

| Finding | Outcome |
|---|---|
|  | fixed in `<commit>` / won't fix (why) / deferred to (where) |

## Checklist

- [ ] Branch named by kind and purpose (`feature/`, `fix/`, `refactor/`, `hotfix/`, `docs/`, `release/`)
- [ ] About 400 changed lines or fewer (lock files excluded), three concerns or fewer
- [ ] docs/decisions.md has every new judgment call
- [ ] CHANGELOG.md `[Unreleased]` updated if a person or the API sees a change
- [ ] Screens compared with the prototype, light and dark (UI changes only)
