# Decisions

Every judgment call, with date and reason. Status `proposed` means the owner has not confirmed it yet.
Format for new entries: `## Dn — question`, then date, choice, why, affects.

| # | Question | Choice | Affects | Status |
|---|---|---|---|---|
| D1 | Due reminders per card (prototype) or per person (plan)? | Per person, as in the plan. Remove “Remind me” from the Dates popup. | M2, M6 | proposed |
| D2 | Show M3/M4 items (custom fields, save as template, palette) in the M2 board menu? | Hide them until their milestone ships. No dead buttons. | M2–M4 | proposed |
| D3 | Do invites expire? | Yes, after 14 days by default. Show the expiry date; allow re-invite. | M1 | proposed |
| D4 | Confirm “Delete forever” and “Remove member”? | Yes. Block removing the last owner. Removing yourself asks first. | M1, M2 | proposed |
| D5 | Can observers comment? | No. Observers are fully read-only. | M2 | proposed |
| D6 | Cards assigned to someone removed from the project? | Unassign automatically, log an event, keep the card. | M2 | proposed |
| D7 | Can a company “manage” token open restricted boards? | No. Tokens follow the same rules as people. | M6 | proposed |
| D8 | Where do builds run? | In CI or a build machine. Only the built bundle goes to the server. | M1 | proposed |
| D9 | Off-machine backup required? | Yes, one copy off the machine, with a monthly restore test. | M1 | proposed |
| D10 | May the agent run sudo or systemd commands? | No. It writes scripts in `deploy/`; you read and run them. | M1 | proposed |
| D11 | AI attribution in commits | None: no Co-Authored-By or "generated with" lines in commits or PRs. `attribution` is empty in `.claude/settings.json`. | All | decided 2026-11-11 |
| D12 | Allow the permissive licenses Unicode-3.0 and Zlib in `deny.toml`? | Yes, both. Unicode-3.0 for unicode-ident; Zlib for foldhash, which rusqlite 0.33+ pulls in. rusqlite moves to 0.42. Any other license outside MIT, Apache-2.0, BSD, ISC still needs the owner. | M1 | decided 2026-11-11 |
| D13 | One binary that embeds the web app, or separate backend and frontend? | Separate folders and separate deploys. `server/` is an API-only binary behind the tunnel at `tazko-api-dev.hugepigstudio.com`; `web/` is a static site on Cloudflare Pages at `tazko-dev.hugepigstudio.com`. Same-site hosts, so the host-only `SameSite=Lax` session cookie works with `credentials: "include"`; CORS allows exactly `TAZKO_WEB_ORIGIN`; Origin is still checked on writes and WebSockets. Replaces the build plan's "web app compiled into the binary". | M1, M3, M6 | decided 2026-11-11 |
| D14 | Backend language: Rust (build plan) or Python? | Python 3.12+. FastAPI + uvicorn for HTTP and WebSocket, stdlib `sqlite3` (no ORM), `argparse` CLI, uv for packages with a committed `uv.lock`, ruff (lint + format), mypy strict, pytest. Release bundle is a wheel plus hashed, pinned requirements installed into a per-release virtualenv; systemd runs `.venv/bin/tazko`. PSF-2.0 is accepted as a license exception (typing_extensions, required by FastAPI/Pydantic). Replaces the build plan's "one static Rust binary". | M1–M6 | decided 2026-11-11 |
| D15 | Folder names and internal structure | `server/` -> `backend/`, `web/` -> `frontend/` (and `deploy/backend`, `deploy/frontend`). Backend in layers: `core/` (pydantic-settings config, errors, logging, `Depends` helpers), `db/`, `modules/<feature>/` with router, schemas, service, repository, `main.py` app factory; tests split into unit and integration. Frontend by feature: `app/`, `pages/`, `features/`, `shared/`, with ESLint import rules for the layers. The Cloudflare Pages project keeps the name `tazko-web`. | M1–M6 | decided 2026-11-11 |

## Log

- 2026-11-11 · D13 · Owner chose separate deploys with Cloudflare Pages + an API subdomain over one binary and over path routing on one host. API host is `tazko-api-dev`, not `api.tazko-dev`, because the free certificate covers one subdomain level. Effects: Google redirect URI moves to the API host (P0-2), the tunnel rule is for the API host (P0-3), new P0 job for the Pages project, M1-01 no longer embeds the web build, M1-08 covers both release paths, and the e2e harness starts both parts.
- 2026-11-11 · D14 · Owner chose Python over Rust for the backend, and accepted PSF-2.0. Effects: `server/` is a uv-managed package (`server/src/tazko`), Cargo workspace and `deny.toml` removed, `scripts/ci.sh` and CI run ruff, mypy, pytest and `tools/check-backend-licenses.py`; the host needs uv and Python 3.12 (P0-4, M1-08); "one writer thread per company" stays, implemented with a dedicated thread per tenant and `sqlite3` connections (M1-03); idle memory and cold start budgets in the build plan were measured for Rust and are re-baselined at M1-01.
- 2026-11-11 · D15 · Owner asked for a best-practice structure and chose the `backend/` + `frontend/` names, backend layering and a feature-based frontend; repo tooling (task runner, separate e2e package) stays as is. The REST v1 module is `public_api` so it is not confused with the internal API. `tenant` moved from a feature into `db/`. Added pydantic-settings (MIT) and python-dotenv (BSD-3) for settings.
