# Progress

One short report per milestone: what was built, checks passed, differences from the prototype, anything unverified, and the performance numbers (cold start, initial JS gzip, idle memory).

## Skeleton · 2026-11-11

- Repository skeleton: Rust crate with the planned module layout, `/health`, CLI command stubs; web app (Vite, React, TypeScript, Tailwind) with app and admin entry routes; deploy unit files and script stubs; `scripts/ci.sh`; CI workflow; docs, decisions and milestone files.
- Verified on Windows (Rust 1.99.1, MSVC): cargo fmt, clippy -D warnings, cargo test (3 tests), web lint/test/build, web license check. `tazko serve` answers `/health` and serves the embedded web app.
- Initial JS: 101.5 KB gzip (budget 200 KB).
- `design/tokens.css` is a placeholder; real values are extracted in M1-01.
