#!/usr/bin/env bash
# The one check that must be green before every commit and in CI.
# frontend lint + typecheck + vitest + build; backend ruff (lint + format),
# mypy, pytest; license checks for shipped frontend and backend packages.
set -euo pipefail
cd "$(dirname "$0")/.."

step() { printf '\n== %s\n' "$*"; }

if ! command -v uv >/dev/null 2>&1; then
  echo "uv is missing: see https://docs.astral.sh/uv/ to install it" >&2
  exit 1
fi
ROOT="$(pwd)"
py() { uv run --project "$ROOT/backend" --locked "$@"; }

step "frontend: install"
if [ ! -d frontend/node_modules ] || [ frontend/package-lock.json -nt frontend/node_modules ]; then
  npm --prefix frontend ci --no-audit --no-fund
fi

step "frontend: lint"
npm --prefix frontend run lint

step "frontend: test"
npm --prefix frontend test

step "frontend: build (typecheck + static bundle in frontend/dist)"
npm --prefix frontend run build

step "frontend: licenses"
node tools/check-frontend-licenses.mjs

step "backend: install"
uv sync --project backend --locked

step "backend: format"
(cd backend && py ruff format --check .)

step "backend: lint"
(cd backend && py ruff check .)

step "backend: types"
(cd backend && py mypy)

step "backend: test"
(cd backend && py pytest)

step "backend: licenses"
py python tools/check-backend-licenses.py

printf '\nci: all green\n'
