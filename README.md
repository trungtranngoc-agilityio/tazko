# Tazko

Self-hosted board app for several companies. Each company's data is its own SQLite file. Google sign-in by invite.

Two parts, built and deployed separately (docs/decisions.md D13, D14, D15):

| Part | Folder | Stack | Runs on |
|---|---|---|---|
| **Backend** (API) | `backend/` | Python 3.12+: FastAPI, uvicorn, sqlite3 (packages by uv) | One service on loopback, behind a Cloudflare Tunnel at `tazko-api-dev.hugepigstudio.com` |
| **Frontend** (web) | `frontend/` | React, TypeScript, Vite, Tailwind (shadcn/ui ready) | Static site on Cloudflare Pages at `tazko-dev.hugepigstudio.com` |

Status: **skeleton** — no features yet. Work starts at [docs/milestones/P0.md](docs/milestones/P0.md), then M1.

## Where things are

| Path | What |
|---|---|
| `CLAUDE.md` | Rules for every agent session (short on purpose) |
| `.claude/` | Agent settings, format hook, `planner` / `reviewer` / `security` subagents, `prototype-compare` skill |
| `design/` | **Read-only** UI spec: clickable prototype, tokens, screen index, known deviations |
| `docs/build-plan.md` | Data, permissions, limits, deployment (original HTML in `docs/sources/`) |
| `docs/decisions.md` | Every judgment call; overrides the build plan where they differ |
| `docs/milestones/` | P0, M1–M6 task lists: the memory between sessions |
| `backend/pyproject.toml`, `backend/uv.lock` | Backend package, dependencies and tool settings (ruff, mypy, pytest) |
| `backend/src/tazko/` | Backend package: `core/`, `db/`, `modules/<feature>/` (router, schemas, service, repository), `main.py`, `cli.py` |
| `backend/src/tazko/migrations/` | `control/` and `tenant/` SQL, versioned by `PRAGMA user_version` |
| `backend/tests/` | `unit/` and `integration/` (pytest), shared fixtures in `conftest.py` |
| `frontend/src/` | `app/` (shell, router), `pages/`, `features/<name>/`, `shared/` (api client, i18n, ui); layer rules in [frontend/src/shared/README.md](frontend/src/shared/README.md) |
| `tests/e2e/` | Playwright tests across both parts |
| `deploy/backend/`, `deploy/frontend/` | Release scripts per part — written by the agent, **run by the owner** ([deploy/README.md](deploy/README.md)) |
| `scripts/ci.sh` | The single green check |
| `tools/` | Chrome screenshot harness and the frontend and backend license checks |

## Develop

Needs Python 3.12+, [uv](https://docs.astral.sh/uv/) and Node 22+.

```bash
uv sync --project backend
npm --prefix frontend install
```

Backend on 127.0.0.1:8791 (settings from `TAZKO_*`, see `.env.example`):

```bash
uv run --project backend tazko serve
```

Frontend on http://localhost:5173 (proxies `/health`, `/auth`, `/api`, `/admin/api`, `/ws`, `/cli` to the backend, so dev is same-origin):

```bash
npm --prefix frontend run dev
```

All checks:

```bash
bash scripts/ci.sh
```

End-to-end tests (`npm install` at the repo root once, then `npx playwright install chromium`):

```bash
npx playwright test
```

## Deploy

See [deploy/README.md](deploy/README.md). In short: the backend bundle (a wheel plus pinned, hashed requirements) is built off the server and installed with `deploy/backend/release.sh`, which health-checks and rolls back by itself; the frontend is built with `VITE_API_URL` and uploaded with `deploy/frontend/deploy.sh`, and rolled back from the Pages deployment list. Either side can be released or rolled back alone.
