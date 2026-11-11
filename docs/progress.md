# Progress

One short report per milestone: what was built, checks passed, differences from the prototype, anything unverified, and the performance numbers (cold start, initial JS gzip, idle memory).

## Skeleton · 2026-11-11

- Repository skeleton: Rust crate with the planned module layout, `/health`, CLI command stubs; web app (Vite, React, TypeScript, Tailwind) with app and admin entry routes; deploy unit files and script stubs; `scripts/ci.sh`; CI workflow; docs, decisions and milestone files.
- Verified on Windows (Rust 1.99.1, MSVC): cargo fmt, clippy -D warnings, cargo test (3 tests), web lint/test/build, web license check. `tazko serve` answers `/health` and serves the embedded web app.
- Initial JS: 101.5 KB gzip (budget 200 KB).
- Split into `server/` (API-only binary, CORS for `TAZKO_WEB_ORIGIN`) and `web/` (static site for Cloudflare Pages), with separate deploy folders (D13). The embedding step (`build.rs`, `web.rs`, rust-embed) was removed.
- Backend rewritten in Python (D14): FastAPI app factory with the same `/health`, JSON errors and single-origin CORS; argparse CLI with the same command stubs; 9 pytest tests; ruff, mypy strict and a Python license check in `scripts/ci.sh`. Cargo workspace and `deny.toml` removed. Smoke test: `/health`, JSON 404, CORS for the web origin only, Vite proxy. Idle API memory about 55 MB (Windows, Python 3.14); the build plan budget was set for Rust and is re-baselined in M1-01.
- Restructured (D15): `backend/` (core, db, modules with `health` as the example module; 15 tests) and `frontend/` (app, pages, features with `auth` as the example feature, shared; 4 tests; ESLint layer rules checked against a deliberate violation).
- `design/tokens.css` is a placeholder; real values are extracted in M1-01.
