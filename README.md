# Tazko

Self-hosted board app for several companies. One Rust binary (Axum, rusqlite, tokio) embeds the React web app and the super admin console; each company's data is its own SQLite file. Google sign-in by invite. Runs on loopback behind a Cloudflare Tunnel.

Status: **skeleton** — no features yet. Work starts at [docs/milestones/P0.md](docs/milestones/P0.md), then M1.

## Where things are

| Path | What |
|---|---|
| `CLAUDE.md` | Rules for every agent session (short on purpose) |
| `.claude/` | Agent settings, format hook, `planner` / `reviewer` / `security` subagents, `prototype-compare` skill |
| `design/` | **Read-only** UI spec: clickable prototype, tokens, screen index, known deviations |
| `docs/build-plan.md` | Data, permissions, limits, deployment (original HTML in `docs/sources/`) |
| `docs/decisions.md` | Every judgment call (D1–D11 proposed) |
| `docs/milestones/` | P0, M1–M6 task lists: the memory between sessions |
| `src/` | Rust crate; one module per area (map in `src/lib.rs`) |
| `migrations/` | `control/` and `tenant/` SQL, versioned by `PRAGMA user_version` |
| `web/` | React + TypeScript + Vite + Tailwind (shadcn/ui ready) |
| `tests/` | Rust integration tests; `tests/e2e/` Playwright |
| `deploy/` | systemd units and host scripts — written by the agent, **run by the owner** |
| `scripts/ci.sh` | The single green check |
| `tools/` | Chrome screenshot harness used by `prototype-compare` |

## Develop

Needs Rust stable (see `rust-toolchain.toml`), Node 22+, and `cargo install cargo-deny`.

```bash
npm --prefix web install
```

```bash
cargo run -- serve
```

```bash
npm --prefix web run dev
```

The Vite dev server (http://localhost:5173) proxies `/health`, `/auth`, `/api`, `/admin/api` and `/cli` to the binary on 127.0.0.1:8791. Settings come from `TAZKO_*` variables; see `.env.example`.

```bash
bash scripts/ci.sh
```

End-to-end tests (`npm install` at the repo root once, then `npx playwright install chromium`):

```bash
npx playwright test
```

## Deploy

Written in M1-08. Summary from the build plan: build the bundle off the server (D8), copy it to `/var/lib/tazko-incoming`, run `tazko-release` as `tazko-deploy`; it switches `/opt/tazko/current`, restarts the service and rolls back by itself if `/health` does not answer within 20 s. Nightly backup at 02:30 via `tazko-backup.timer`.
