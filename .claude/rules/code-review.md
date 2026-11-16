# Code review

## Which reviewer, when
Run these before asking the owner to merge. Pass only the base branch or milestone id, never a summary.

| The diff touches | Run |
|---|---|
| Any code | `reviewer` agent |
| `modules/auth`, `modules/admin`, `core/` (sessions, CORS, Origin), tokens, uploads, WebSocket, `frontend/src/shared/api` | `security` agent |
| `backend/src/tazko/migrations/**` or a new table or index | `backend-design:schema-reviewer` agent and the `backend-design:review-migration` skill |
| `deploy/**` | `deploy-reviewer` agent |
| An API route, schema or error code the frontend uses | check the frontend callers in the same PR (API compatibility, CLAUDE.md) |

## Severity
- `block`: security hole, data loss, broken logic, a "Done when" line without a real test. Must be fixed before merge.
- `should`: bug, race, missing error path test, rule broken. Fixed before merge unless the owner agrees to defer it.
- `nit`: naming, style, small readability. Optional.
- `question`: needs an answer from the author or owner, not necessarily wrong.

## What to check beyond correctness
- Concurrency: two requests at once, close during use, the same company opened twice, writes racing each other.
- Edge cases: empty, None, max length, unicode, expired, another company's id.
- Blocking work: database calls block, so routes that use them are `def`, never `async def`.
- Queries: no N+1, an index for every new WHERE or JOIN column, every list bounded.
- Suppressions: every `noqa`, `type: ignore` or skipped test says why on the same line.
- Tests prove behaviour (status, body, rows written), not that a function was called. No time- or order-dependent tests.
- Functions over about 30 lines or with more than one reason to change get split.

## Answering findings
Every finding gets an outcome in the PR description: `fixed` (with the commit), `won't fix` (why), or `deferred` (where it is tracked: milestone file or decisions.md). At most three review rounds; anything left goes to the owner.
