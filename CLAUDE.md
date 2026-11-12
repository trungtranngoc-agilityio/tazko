# Tazko

Multi-tenant board app. Two deployables (D13), folder layout D15:
- backend/: one Python service (FastAPI, uvicorn, stdlib sqlite3; uv manages packages), JSON + WebSocket API only, behind a Cloudflare Tunnel (D14).
- frontend/: React web app, a static site on Cloudflare Pages that calls the API cross-origin with cookies.
Specs: docs/build-plan.md (data, permissions, deploy) and design/tazko-prototype.html (UI).
If they disagree: plan wins on data and permissions, prototype wins on UI. If neither says, stop and ask.
docs/decisions.md overrides the build plan where they differ (D13 replaces "the binary embeds the web app"; D14 replaces Rust with Python).

## Commands
- scripts/ci.sh          frontend lint + vitest + build, backend ruff format/check, mypy --strict, pytest, license checks
- uv run --project backend tazko serve   API on 127.0.0.1:8791 (or `cd backend && uv run tazko serve`)
- cd backend && uv run pytest           backend tests only; `uv add <pkg>` to add a dependency (lock file is committed)
- npm --prefix frontend run dev   web on http://localhost:5173, proxies /api /auth /ws ... to :8791
- npx playwright test    e2e (tests/e2e), starts both; not in scripts/ci.sh, runs as its own CI job. Run it before a commit that touches a flow across web and API.

## Layout
- backend/src/tazko: core/ (settings, errors, logging, deps) -> db/ -> modules/<name>/ -> main.py (app factory) and cli.py.
- A module is router.py (HTTP only, no SQL) + schemas.py (Pydantic contract) + service.py (rules, permission checks) + repository.py (its SQL). Shape and list: backend/src/tazko/modules/__init__.py; modules/health is the example.
- Modules import core, db and other modules' services only. Routes reach settings and databases through core/deps.py (Depends), not app.state.
- Errors are raised as tazko.core.errors.AppError subclasses. mypy strict covers src and tests.
- backend/src/tazko/migrations/control and .../tenant (shipped in the wheel). backend/tests/unit and tests/integration; fixtures in tests/conftest.py.
- frontend/src: app/ (providers, router, layouts, styles) -> pages/<screen>/ -> features/<name>/ (components, api.ts, hooks; public index.ts) -> shared/ (api, i18n, ui, lib). ESLint blocks upward and deep imports; see frontend/src/shared/README.md.
- Every UI string in frontend/src/shared/i18n. Every API call through frontend/src/shared/api.
- deploy/backend and deploy/frontend are written by the agent and run by the owner. Run the deploy-reviewer agent on every change there before asking the owner to run it. design/ is never edited.

## How we work
- One milestone per branch: milestone/m2-core. One task per commit. Task list lives in docs/milestones/Mx.md.
- Test first, red then green: write the test for a "Done when" line, run it and see it fail for the expected reason (not an import or syntax error), then write the least code that makes it pass, then refactor with the tests green. Never weaken or delete a test to make it pass.
- Name tests after behaviour (test_expired_invite_is_refused), one behaviour per test, arranged as given / when / then. Use the lowest layer that proves the line: unit, then integration (TestClient), then e2e (tests/e2e) only for flows across web and API.
- Run scripts/ci.sh before every commit. Commit messages: short, plain description of the change. No AI attribution (D11).
- Record every judgment call in docs/decisions.md (date, question, choice, why).
- Before a UI task, open the matching screen in design/ and note layout, states (empty, loading, error, read-only), text, keys.
- design/KNOWN-DEVIATIONS.md lists prototype behaviour that is wrong. Do not copy it; each entry has a regression test.
- The API stays backward compatible for one release so web and server can roll back independently.

## Data
- data/control.db: users, companies, memberships, invites, sessions, audit log.
- data/orgs/<slug>/tazko.db and data/orgs/<slug>/files/: one company each. No org_id columns.
- One writer thread per company, small read pool. WAL, synchronous=NORMAL, foreign_keys=ON.
- Migrations tracked with PRAGMA user_version.
- Every change writes an events row in the same transaction.

## Auth and permissions
- Google OIDC with PKCE, started and called back on the API host, then redirect to TAZKO_WEB_ORIGIN.
- Sign-in only for existing users or valid invites. Invites expire after 14 days.
- Match account by sub; match by email only when the user has no sub yet.
- Session cookie: host-only on the API host, HttpOnly, Secure, SameSite=Lax (web and API are same-site).
- CORS allows exactly TAZKO_WEB_ORIGIN with credentials. Also check Origin on every state-changing request and on the WebSocket handshake.
- Permissions are checked on the server for every request. The UI hiding a button is not a check.
- Observer is read-only, including comments and custom fields. Restricted boards are hidden from unlisted members.
- Tokens are stored as hashes only. Webhooks never call private addresses (check after DNS resolve).

## Never
- Run sudo, systemctl, cloudflared, wrangler or anything on the production host or Cloudflare. Write a script in deploy/ and ask.
- Read or print secrets (.env, data/secret). Ask the owner to set them.
- Merge PRs, push --force, or push to main.
- Add Postgres, Docker, or a library that is not MIT, Apache-2.0, BSD or ISC (Unicode-3.0, Zlib (D12) and PSF-2.0 (D14) are accepted exceptions; tools/check-backend-licenses.py and tools/check-frontend-licenses.mjs hold the lists).
- Name other products in code, text, tests or docs. Copy code, text or icons from other products.

## UI
- Tailwind theme from design/tokens.css. Light and dark must both match the prototype.
- Initial JS under 200 KB gzip. No key shortcut fires while typing in a field.
