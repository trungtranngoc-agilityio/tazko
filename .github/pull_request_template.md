## What

<!-- One or two sentences. Title in Conventional Commit format: feat(auth): ... -->

## Why

<!-- Task id (M1-04), finding or decision it answers. -->

## How to test

<!-- Commands and the screen or request to try. -->

## Done when

| Line from docs/milestones/Mx.md | Test (file::name) |
|---|---|
|  |  |

## Review

| Agent | Outcome |
|---|---|
| reviewer |  |

Findings: <!-- each one: fixed (commit) / won't fix (why) / deferred (where) -->

## Checklist

- [ ] `scripts/ci.sh` green; e2e run if the change crosses web and API
- [ ] Under about 400 changed lines (lock files excluded), three concerns or fewer
- [ ] docs/decisions.md has every new judgment call
- [ ] CHANGELOG.md `[Unreleased]` updated if people or the API see a change
- [ ] Screens compared with the prototype (UI changes only)
