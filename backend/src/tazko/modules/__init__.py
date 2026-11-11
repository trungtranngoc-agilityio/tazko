"""Feature modules. Each one owns one area end to end and has the same shape
(files appear when the module needs them; `health` is the worked example):

    modules/<name>/
        __init__.py     exports `router` (and nothing else other modules need)
        router.py       FastAPI routes: parse input, call the service, shape output. No SQL.
        schemas.py      Pydantic request/response models (the API contract)
        service.py      Business rules and permission checks; raises tazko.core.errors
        repository.py   SQL for this area only (stdlib sqlite3, parameters always bound)

Rules:
- A module may import `tazko.core`, `tazko.db` and another module's service, never
  another module's router or repository.
- Every permission check lives in a service, so routes, WebSockets and the CLI share it.

| Module          | Responsibility                                       | First milestone |
|-----------------|------------------------------------------------------|-----------------|
| `health`        | `/health` for the tunnel and release health checks  | M1              |
| `orgs`          | Companies, memberships, tenant handle cache          | M1              |
| `auth`          | Google OIDC + PKCE, sessions, Origin check, invites  | M1              |
| `admin`         | Super admin console API (`/admin/api`)               | M1              |
| `boards`        | Projects, boards, lists, permissions                 | M2              |
| `cards`         | Cards, checklists, comments, search                  | M2              |
| `realtime`      | WebSocket per board, in-memory hub                   | M3              |
| `files`         | Content-hash storage, quotas, thumbnails             | M3              |
| `notifications` | Mentions, bell, due-soon, email queue                | M3, M6          |
| `public_api`    | REST `/api/v1`, OpenAPI, tokens, webhooks            | M6              |
"""
