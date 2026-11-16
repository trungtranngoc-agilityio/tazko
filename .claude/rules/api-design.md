---
paths:
  - "backend/src/tazko/modules/**"
  - "backend/src/tazko/core/errors.py"
  - "backend/src/tazko/main.py"
  - "frontend/src/shared/api/**"
  - "frontend/src/features/*/api.ts"
---

# API design (D19)

The internal API serves only the web app and stays backward compatible for one release (CLAUDE.md). The public REST API is `/api/v1` (M6).

## Paths and methods
- Plural nouns, kebab-case, under `/api` (D19): `/api/orgs/{slug}/projects/{id}/boards`. Sign-in stays at `/auth`, the console API at `/admin/api`. A company is always named by its slug in the path.
- GET never changes data. POST creates, PATCH changes part, PUT replaces, DELETE removes. Search uses GET with query parameters.

## Status codes
- 200 read or update with a body; 201 created, with a `Location` header; 204 delete or action with no body.
- 400 malformed request; 401 not signed in; 403 signed in but not allowed (also a write with a wrong Origin); 404 missing or not visible to you (restricted boards and other companies answer 404, never 403); 409 conflict or duplicate (slug taken, invite already used); 422 validation failed; 429 rate limited; 500 unexpected.

## Errors
Every error body is:

```json
{"error": {"code": "SLUG_TAKEN", "message": "slug: already taken", "details": [{"field": "slug", "message": "already taken"}]}}
```

- `code` is UPPER_SNAKE and stable: the web app shows `errorText(error.code)` from frontend/src/shared/i18n, which reads the key `error.<CODE>` and falls back to `error.UNKNOWN`. Add the key when the UI must explain a new code. Never change a shipped code. `message` is English for logs and fallbacks only.
- `details` lists one entry per problem for 422 (`field` names the field; a field can appear twice) and is empty otherwise.
- A body that is not JSON, or a missing body, is 400 `BAD_REQUEST`, not 422.
- A 204 has no body; `api()` in frontend/src/shared/api returns `undefined` for it.
- Raise a tazko.core.errors class (NotFound, Unauthorized, Forbidden, BadRequest, Conflict, Invalid); pass a specific `code` when the UI must react to it.
- Never return stack traces, paths, SQL or secrets.

## Bodies
- Responses are Pydantic models from the module's schemas.py. Never return token hashes, session ids, `google_sub` or another company's data.
- Times are UTC ISO 8601 with `Z`. Ids are integers inside one company file.
- Every list is bounded: `limit` (default 50, max 200) with a keyset cursor (`after`), or a fixed small cap documented on the route.
- Filters and sort fields come from an allow list, never raw column names.
