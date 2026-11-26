"""Feature modules. Each one owns one area end to end; `health` is the smallest example.

    modules/<name>/
        __init__.py     one line saying what the module owns
        router.py       FastAPI routes: parse input, call the service, shape output. No SQL.
        schemas.py      Pydantic request and response models (the API contract)
        service.py      Rules and permission checks; raises tazko.core.errors
        repository.py   SQL for this area only (stdlib sqlite3, values always bound)

A large service is split by sub-feature next to service.py (orgs/console.py,
invites/projects.py, projects/access.py); each such file is used like a service.

Rules:
- A module imports `tazko.core`, `tazko.db` and other modules' services, never
  another module's router or repository. A schemas.py may reuse another
  module's response model when an API answers with the same shape (admin
  lists company invites as invites/schemas.py does).
- Every permission check lives in a service, so routes and the CLI share it.

| Module     | Owns                                                         |
|------------|--------------------------------------------------------------|
| `health`   | `/health` for the tunnel and release checks                  |
| `users`    | People in control.db, the super admin flag, Workspace domains |
| `audit`    | Audit log rows, written in the caller's transaction          |
| `auth`     | Google sign-in, sessions, sign-out                           |
| `orgs`     | Companies, members, `open_company`; the console (console.py) |
| `invites`  | Company invites and invites to one project (projects.py)     |
| `admin`    | Console pages that read across modules (`/admin/api`)        |
| `projects` | Projects, members, roles and the permission matrix           |
| `boards`   | Boards in a project, restricted boards, stars                |
| `cards`    | Lists and cards on a board: add, rename, move, archive       |
"""
