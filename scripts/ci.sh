#!/usr/bin/env bash
# The one check that must be green before every commit and in CI.
# fmt, clippy -D warnings, cargo test, web lint + typecheck + vitest + build,
# license checks for Rust crates and shipped web packages.
set -euo pipefail
cd "$(dirname "$0")/.."

step() { printf '\n== %s\n' "$*"; }

step "web: install"
if [ ! -d web/node_modules ] || [ web/package-lock.json -nt web/node_modules ]; then
  npm --prefix web ci --no-audit --no-fund
fi

step "web: lint"
npm --prefix web run lint

step "web: test"
npm --prefix web test

step "web: build (typecheck + bundle into web/dist)"
npm --prefix web run build

step "web: licenses"
node tools/check-web-licenses.mjs

step "rust: fmt"
cargo fmt --all -- --check

step "rust: clippy"
cargo clippy --all-targets --locked -- -D warnings

step "rust: test"
cargo test --locked

step "rust: licenses"
if ! command -v cargo-deny >/dev/null 2>&1; then
  echo "cargo-deny is missing: cargo install --locked cargo-deny" >&2
  exit 1
fi
cargo deny check licenses bans sources

printf '\nci: all green\n'
